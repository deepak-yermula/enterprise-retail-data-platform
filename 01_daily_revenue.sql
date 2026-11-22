-- Gold revenue from completed sales only, in integer cents.
SELECT order_date, completed_line_items, units_sold,
       revenue_cents, ROUND(revenue_cents / 100.0, 2) AS revenue_cad
FROM gold_daily_revenue
ORDER BY order_date;
