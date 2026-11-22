# Databricks notebook source
# Databricks-only integration example; requires a configured workspace, cluster,
# access to ADLS/Unity Catalog, and valid input CSV paths. Not exercised in CI.

# COMMAND ----------
from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.conf.set("spark.sql.session.timeZone", "UTC")

dbutils.widgets.text("batch_id", "retail-batch-01")
dbutils.widgets.text("orders_csv_path", "")
dbutils.widgets.text("customers_csv_path", "")
dbutils.widgets.text("products_csv_path", "")
dbutils.widgets.text("lake_root", "")

batch_id = dbutils.widgets.get("batch_id").strip()
orders_csv_path = dbutils.widgets.get("orders_csv_path").strip()
customers_csv_path = dbutils.widgets.get("customers_csv_path").strip()
products_csv_path = dbutils.widgets.get("products_csv_path").strip()
lake_root = dbutils.widgets.get("lake_root").rstrip("/")
if not all([batch_id, orders_csv_path, customers_csv_path, products_csv_path, lake_root]):
    raise ValueError("Set batch_id, input CSV paths, and accessible lake_root widget values")

bronze_path = f"{lake_root}/bronze/orders"
silver_path = f"{lake_root}/silver/order_items"
customers_path = f"{lake_root}/silver/customers"
products_path = f"{lake_root}/silver/products"
manifest_path = f"{lake_root}/control/processed_batches"

# COMMAND ----------
# Re-run protection: do not reprocess a successfully completed batch ID.
if DeltaTable.isDeltaTable(spark, manifest_path):
    if spark.read.format("delta").load(manifest_path).where(F.col("batch_id") == batch_id).limit(1).count():
        dbutils.notebook.exit(f"Batch {batch_id} was already processed")

customers = spark.read.option("header", True).csv(customers_csv_path)
products = spark.read.option("header", True).csv(products_csv_path)
customers.select("customer_id", "customer_name", "country").write.format("delta").mode("overwrite").save(customers_path)
products.select("product_id", "product_name", "category").write.format("delta").mode("overwrite").save(products_path)

source = spark.read.option("header", True).csv(orders_csv_path)
expected = ["line_item_id", "order_id", "order_date", "customer_id", "product_id",
            "quantity", "unit_price_cents", "status", "updated_at"]
missing = set(expected) - set(source.columns)
if missing:
    raise ValueError(f"Required source columns missing: {sorted(missing)}")

# Bronze: preserve source payload for audit. This is at-least-once append if an
# execution crashes before the control manifest is written; see cloud runbook.
(source.select(*expected)
 .withColumn("batch_id", F.lit(batch_id))
 .withColumn("ingested_at", F.current_timestamp())
 .write.format("delta").mode("append").save(bronze_path))

# COMMAND ----------
# Silver: typed validation; reject invalid rows before version-aware MERGE.
normalized = (source.select(*expected)
    .withColumn("quantity", F.col("quantity").cast("int"))
    .withColumn("unit_price_cents", F.col("unit_price_cents").cast("long"))
    .withColumn("order_date", F.to_date("order_date"))
    .withColumn("updated_at", F.to_timestamp("updated_at")))

valid_customers = customers.select("customer_id").distinct().withColumn("_customer_ok", F.lit(True))
valid_products = products.select("product_id").distinct().withColumn("_product_ok", F.lit(True))
checked = (normalized.join(valid_customers, "customer_id", "left")
    .join(valid_products, "product_id", "left")
    .withColumn("reject_reason", F.when(F.col("line_item_id").isNull() | (F.trim("line_item_id") == ""), "missing line_item_id")
        .when(F.col("order_id").isNull() | (F.trim("order_id") == ""), "missing order_id")
        .when(F.col("order_date").isNull() | F.col("updated_at").isNull(), "bad date or timestamp")
        .when(F.col("quantity").isNull() | (F.col("quantity") <= 0), "invalid quantity")
        .when(F.col("unit_price_cents").isNull() | (F.col("unit_price_cents") < 0), "invalid price")
        .when(F.col("status").isNull() | (~F.col("status").isin("completed", "cancelled", "pending")), "invalid status")
        .when(F.col("_customer_ok").isNull(), "unknown customer")
        .when(F.col("_product_ok").isNull(), "unknown product")))

(checked.where(F.col("reject_reason").isNotNull())
    .drop("_customer_ok", "_product_ok")
    .withColumn("batch_id", F.lit(batch_id))
    .write.format("delta").mode("append").save(f"{lake_root}/quality/rejected_orders"))
valid = checked.where(F.col("reject_reason").isNull()).select(*expected)

# Exact duplicate events collapse. Inconsistent same-timestamp updates are
# rejected explicitly rather than picked arbitrarily.
row_fingerprint = F.sha2(F.to_json(F.struct(*[F.col(c) for c in expected])), 256)
fingerprinted = valid.withColumn("_fingerprint", row_fingerprint)
conflicts = (fingerprinted.groupBy("line_item_id", "updated_at")
    .agg(F.countDistinct("_fingerprint").alias("versions"))
    .where("versions > 1"))
if conflicts.limit(1).count() > 0:
    raise ValueError("Conflicting updates share line_item_id and updated_at; investigate source")

window = Window.partitionBy("line_item_id").orderBy(F.col("updated_at").desc())
dedup = (fingerprinted.withColumn("_rank", F.row_number().over(window))
    .where("_rank = 1").drop("_rank", "_fingerprint"))

if DeltaTable.isDeltaTable(spark, silver_path):
    target = DeltaTable.forPath(spark, silver_path)
    # Updated values replace the previous version; exact replays are harmless.
    (target.alias("t").merge(dedup.alias("s"), "t.line_item_id = s.line_item_id")
        .whenMatchedUpdateAll(condition="s.updated_at > t.updated_at")
        .whenNotMatchedInsertAll()
        .execute())
else:
    dedup.write.format("delta").mode("overwrite").save(silver_path)

# COMMAND ----------
# Gold: replace reproducible aggregates from all current Silver records.
# Large-volume production version would prefer partition-aware incremental gold.
silver = spark.read.format("delta").load(silver_path)
completed = silver.where(F.col("status") == "completed")
(daily := completed.groupBy("order_date").agg(
    F.count("line_item_id").alias("completed_line_items"),
    F.sum("quantity").alias("units_sold"),
    F.sum(F.col("quantity") * F.col("unit_price_cents")).alias("revenue_cents")))
(daily.write.format("delta").mode("overwrite").save(f"{lake_root}/gold/daily_revenue"))

(product_sales := completed.groupBy("product_id").agg(
    F.sum("quantity").alias("units_sold"),
    F.sum(F.col("quantity") * F.col("unit_price_cents")).alias("revenue_cents")))
(product_sales.join(products, "product_id", "right")
    .fillna({"units_sold": 0, "revenue_cents": 0})
    .write.format("delta").mode("overwrite").save(f"{lake_root}/gold/product_performance"))

(customer_sales := completed.groupBy("customer_id").agg(
    F.countDistinct("order_id").alias("completed_orders"),
    F.sum(F.col("quantity") * F.col("unit_price_cents")).alias("revenue_cents")))
(customer_sales.join(customers, "customer_id", "right")
    .fillna({"completed_orders": 0, "revenue_cents": 0})
    .write.format("delta").mode("overwrite").save(f"{lake_root}/gold/customer_value"))

# Successful-batch log: a lightweight demo manifest, not atomic across tables.
(spark.createDataFrame([(batch_id,)], ["batch_id"])
 .withColumn("completed_at", F.current_timestamp())
 .write.format("delta").mode("append").save(manifest_path))
dbutils.notebook.exit(f"Completed batch {batch_id}")
