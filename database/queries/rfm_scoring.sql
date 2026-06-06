-- rfm_scoring.sql
-- FinSight — Customer Behavioral Intelligence Platform
-- RFM scoring queries used to validate Python engine output
-- and power Power BI dashboard visuals directly.

-- ============================================================
-- Query 1: Raw RFM values per customer
-- ============================================================
SELECT
    customer_id,
    DATEDIFF(CURDATE(), MAX(txn_date))      AS recency_days,
    COUNT(*)                                 AS frequency,
    ROUND(SUM(amount), 2)                   AS monetary,
    MAX(txn_date)                            AS last_txn_date
FROM transactions
WHERE status = 'completed'
AND amount > 0
GROUP BY customer_id
ORDER BY monetary DESC;


-- ============================================================
-- Query 2: RFM quintile scores using NTILE
-- (SQL equivalent of Python pd.qcut)
-- ============================================================
WITH rfm_raw AS (
    SELECT
        customer_id,
        DATEDIFF(CURDATE(), MAX(txn_date)) AS recency_days,
        COUNT(*)                            AS frequency,
        SUM(amount)                         AS monetary
    FROM transactions
    WHERE status = 'completed' AND amount > 0
    GROUP BY customer_id
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- Recency: LOWER days = HIGHER score (reversed NTILE)
        6 - NTILE(5) OVER (ORDER BY recency_days ASC)  AS R_score,
        NTILE(5) OVER (ORDER BY frequency ASC)          AS F_score,
        NTILE(5) OVER (ORDER BY monetary ASC)           AS M_score
    FROM rfm_raw
)
SELECT
    customer_id,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    R_score,
    F_score,
    M_score,
    CONCAT(R_score, F_score, M_score) AS rfm_code,
    R_score + F_score + M_score       AS rfm_combined
FROM rfm_scored
ORDER BY rfm_combined DESC;


-- ============================================================
-- Query 3: Segment distribution (for Power BI donut chart)
-- ============================================================
SELECT
    segment,
    COUNT(*)                                  AS customer_count,
    ROUND(AVG(monetary), 0)                   AS avg_monetary,
    ROUND(AVG(recency_days), 0)               AS avg_recency_days,
    ROUND(AVG(frequency), 1)                  AS avg_frequency,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*))
          OVER (), 1)                          AS pct_of_total
FROM customer_rfm
GROUP BY segment
ORDER BY avg_monetary DESC;


-- ============================================================
-- Query 4: RFM × Life Event matrix
-- (Core visual for Dashboard 3 — Segment Strategy)
-- ============================================================
SELECT
    r.segment          AS rfm_segment,
    s.top_event        AS life_event,
    COUNT(*)           AS customer_count,
    ROUND(AVG(p.priority_index), 1) AS avg_priority_index,
    ROUND(AVG(s.opportunity_score), 1) AS avg_life_event_score
FROM customer_rfm r
JOIN customer_scores s
    ON r.customer_id = s.customer_id
JOIN customer_priority p
    ON r.customer_id = p.customer_id
WHERE s.top_event IS NOT NULL
GROUP BY r.segment, s.top_event
ORDER BY avg_priority_index DESC;


-- ============================================================
-- Query 5: Champions at risk of life event (highest priority)
-- ============================================================
SELECT
    c.customer_id,
    c.city,
    c.card_type,
    r.segment,
    r.rfm_combined,
    s.top_event,
    s.opportunity_score,
    v.velocity_label,
    p.priority_index,
    p.action_tier,
    p.recommended_product
FROM customers c
JOIN customer_rfm r       ON c.customer_id = r.customer_id
JOIN customer_scores s    ON c.customer_id = s.customer_id
JOIN customer_velocity v  ON c.customer_id = v.customer_id
JOIN customer_priority p  ON c.customer_id = p.customer_id
WHERE r.segment IN ('Champions', 'Loyal', 'Cannot Lose')
AND s.top_event IS NOT NULL
AND p.action_tier IN ('IMMEDIATE', 'HIGH')
ORDER BY p.priority_index DESC
LIMIT 50;
