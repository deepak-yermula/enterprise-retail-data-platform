# Data contract and quality policy

## Source event grain

One row is one *version of an order line* identified by `line_item_id`. Multiple versions of a line item can arrive in separate batches. `order_id` can appear on multiple line items. Every example row is synthetic.

| Column | Logical type | Constraint |
|---|---|---|
| `line_item_id` | string | Nonblank, business key |
| `order_id` | string | Nonblank |
| `order_date` | ISO date | Valid `YYYY-MM-DD` |
| `customer_id` | string | Present in customers reference data |
| `product_id` | string | Present in products reference data |
| `quantity` | integer | Greater than 0 |
| `unit_price_cents` | integer | Greater than or equal to 0 |
| `status` | enum | `completed`, `cancelled`, `pending` |
| `updated_at` | ISO timestamp with timezone | Parsed and normalized to UTC |

## Semantics

- Silver chooses the **latest `updated_at`** for each `line_item_id`.
- Older versions are ignored; exact replay of a batch is skipped by file fingerprint.
- Same-version conflicts in storage are quarantined; conflicting different payloads at identical timestamps *within a single batch* are rejected. Such events must be manually reconciled.
- Gold only recognizes `completed` line items, excluding `cancelled` and `pending`.
- Revenue is gross line-item sales before taxes, discounts, refunds, shipping or recognized-revenue adjustments. It is **not** an accounting-grade revenue report.
- Gold customer `completed_orders` counts distinct `order_id` values with at least one completed line item.
- Individual item statuses are independent; this small demo does not enforce a whole-order status invariant.

## Known gaps

- Does not implement full CDC transaction ordering, source deletions, refunds, foreign currency conversion, late-arriving dimension history, schema registry or historical SCD Type 2.
- SHA-based file replay skipping assumes one unchanged file is a complete unit of work; file modifications change SHA and are treated as a new batch.
- No time-zone-specific business-day conversion; `order_date` is considered already in the desired business calendar.
- This implementation uses limited synthetic inputs rather than scale-tested data.
