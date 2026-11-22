# Power BI dashboard — reproduction guide

**Status:** documented dashboard design, not an exported PBIX or published report.

## Data inputs

After `python -m retail_pipeline.cli demo`, import the CSVs in `output/gold/`:

- `gold_daily_revenue.csv`: `order_date`, `completed_line_items`, `units_sold`, `revenue_cents`
- `gold_product_performance.csv`: `product_id`, `product_name`, `category`, `units_sold`, `revenue_cents`
- `gold_customer_value.csv`: `customer_id`, `customer_name`, `country`, `completed_orders`, `revenue_cents`

## Recommended pages

1. **Executive Overview**: total completed revenue (CAD), daily revenue line chart, units sold KPI.
2. **Products**: top products by revenue, product category breakdown.
3. **Customers**: customer value by country, top 5 customers by completed sales revenue.

## DAX measures (on `gold_daily_revenue`)

```dax
Completed Revenue CAD = DIVIDE(SUM(gold_daily_revenue[revenue_cents]), 100)
Units Sold = SUM(gold_daily_revenue[units_sold])
Completed Line Items = SUM(gold_daily_revenue[completed_line_items])
```

Do not create one connected data model by joining all three gold tables directly: all are already aggregated at different grains, which can double-count revenue. Use separate pages or shared dimensional tables with carefully managed relationships.

## Verified baseline

Synthetic input after both batches should report **CAD $1,970.00 completed revenue**, matching local CI assertions. Never present this demonstration revenue as business production performance.
