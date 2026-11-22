-- Customer value and ranking within their country.
SELECT customer_name, country, completed_orders, revenue_cents,
       DENSE_RANK() OVER (PARTITION BY country ORDER BY revenue_cents DESC) AS country_rank
FROM gold_customer_value
ORDER BY country, country_rank;
