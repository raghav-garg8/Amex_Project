-- database/queries/cohort_analysis.sql
-- Segments customers into equal-population spend cohorts (LOW, MEDIUM, HIGH) based on total completed transaction spend.
-- CTE customer_spend: Computes total lifetime completed spend per customer.
-- NTILE(3): Partitions the sorted spend list into three groups of equal size.

WITH customer_spend AS (
    SELECT
        customer_id,
        SUM(amount) AS total_spend
    FROM transactions
    WHERE status = 'completed'
    GROUP BY customer_id
),
ranked_customers AS (
    SELECT
        customer_id,
        total_spend,
        NTILE(3) OVER (ORDER BY total_spend ASC) AS cohort_rank
    FROM customer_spend
)
SELECT
    customer_id,
    total_spend,
    CASE cohort_rank
        WHEN 1 THEN 'LOW'
        WHEN 2 THEN 'MEDIUM'
        WHEN 3 THEN 'HIGH'
    END AS spend_cohort
FROM ranked_customers;
