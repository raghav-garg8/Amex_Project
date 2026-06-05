-- database/queries/rolling_window.sql
-- Calculates 90-day rolling spend aggregates per customer and category.
-- WINDOW partition: Groups by customer_id and merchant_category to isolate spend streams.
-- ORDER BY: Arranges chronologically by txn_date to construct temporal sequences.
-- RANGE: Includes transactions from the last 90 days (relative to current txn_date) to handle unevenly spaced transaction dates.

SELECT
    customer_id,
    merchant_category,
    txn_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY customer_id, merchant_category
        ORDER BY txn_date
        RANGE BETWEEN INTERVAL 90 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_90d_spend
FROM transactions
WHERE status = 'completed';
