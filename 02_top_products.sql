-- Rank revenue contribution of each product.
SELECT product_name, category, units_sold, revenue_cents,
       DENSE_RANK() OVER (ORDER BY revenue_cents DESC) AS revenue_rank
FROM gold_product_performance
ORDER BY revenue_rank, product_name;
