-- velocity_anomaly.sql
-- FinSight — Customer Behavioral Intelligence Platform
-- Spend velocity anomaly detection queries.

-- ============================================================
-- Query 1: Monthly spend per customer (rolling 7 months)
-- ============================================================
SELECT
    customer_id,
    DATE_FORMAT(txn_date, '%Y-%m') AS month,
    COUNT(*)                        AS txn_count,
    ROUND(SUM(amount), 2)           AS monthly_spend,
    ROUND(AVG(amount), 2)           AS avg_txn_value
FROM transactions
WHERE status = 'completed'
AND amount > 0
AND txn_date >= DATE_SUB(CURDATE(), INTERVAL 7 MONTH)
GROUP BY customer_id, DATE_FORMAT(txn_date, '%Y-%m')
ORDER BY customer_id, month;


-- ============================================================
-- Query 2: Customer 6-month spend baseline statistics
-- ============================================================
WITH monthly_spend AS (
    SELECT
        customer_id,
        DATE_FORMAT(txn_date, '%Y-%m') AS month,
        SUM(amount)                     AS monthly_total
    FROM transactions
    WHERE status = 'completed'
    AND amount > 0
    AND txn_date >= DATE_SUB(CURDATE(), INTERVAL 7 MONTH)
    AND txn_date < DATE_FORMAT(CURDATE(), '%Y-%m-01')
    GROUP BY customer_id, DATE_FORMAT(txn_date, '%Y-%m')
)
SELECT
    customer_id,
    ROUND(AVG(monthly_total), 2)  AS baseline_mean,
    ROUND(STD(monthly_total), 2)  AS baseline_std,
    ROUND(MIN(monthly_total), 2)  AS baseline_min,
    ROUND(MAX(monthly_total), 2)  AS baseline_max,
    COUNT(*)                       AS months_in_baseline
FROM monthly_spend
GROUP BY customer_id
HAVING months_in_baseline >= 3;


-- ============================================================
-- Query 3: Current month spend vs baseline (for Power BI)
-- ============================================================
WITH baseline AS (
    SELECT
        customer_id,
        AVG(monthly_total)  AS baseline_mean,
        STD(monthly_total)  AS baseline_std
    FROM (
        SELECT
            customer_id,
            DATE_FORMAT(txn_date, '%Y-%m') AS month,
            SUM(amount)                     AS monthly_total
        FROM transactions
        WHERE status = 'completed'
        AND amount > 0
        AND txn_date >= DATE_SUB(CURDATE(), INTERVAL 7 MONTH)
        AND txn_date < DATE_FORMAT(CURDATE(), '%Y-%m-01')
        GROUP BY customer_id, DATE_FORMAT(txn_date, '%Y-%m')
    ) m
    GROUP BY customer_id
),
current_month AS (
    SELECT
        customer_id,
        SUM(amount) AS current_spend
    FROM transactions
    WHERE status = 'completed'
    AND amount > 0
    AND txn_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    ROUND(c.current_spend, 2)   AS current_spend,
    ROUND(b.baseline_mean, 2)   AS baseline_mean,
    ROUND(b.baseline_std, 2)    AS baseline_std,
    ROUND(
        (c.current_spend - b.baseline_mean)
        / NULLIF(b.baseline_std, 0),
    4)                           AS velocity_z_score,
    CASE
        WHEN b.baseline_std = 0 OR b.baseline_std IS NULL
            THEN 'Stable Spender'
        WHEN (c.current_spend - b.baseline_mean)
             / b.baseline_std > 2
            THEN 'Strong Positive Anomaly'
        WHEN (c.current_spend - b.baseline_mean)
             / b.baseline_std > 1
            THEN 'Moderate Increase'
        WHEN (c.current_spend - b.baseline_mean)
             / b.baseline_std >= -1
            THEN 'Normal'
        WHEN (c.current_spend - b.baseline_mean)
             / b.baseline_std >= -2
            THEN 'Declining'
        ELSE 'Strong Negative Anomaly'
    END                          AS velocity_label
FROM current_month c
JOIN baseline b ON c.customer_id = b.customer_id
ORDER BY velocity_z_score DESC;
