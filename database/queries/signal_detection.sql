-- database/queries/signal_detection.sql
-- Aggregates completed transaction history for each customer to detect event signals and populate the customer_features table.
-- Anchored on the execution date '2026-06-05' to support the current scoring batch window.

WITH customer_spend_totals AS (
    SELECT
        customer_id,
        SUM(amount) AS total_spend
    FROM transactions
    WHERE status = 'completed'
    GROUP BY customer_id
),
cohort_ranks AS (
    SELECT
        customer_id,
        NTILE(3) OVER (ORDER BY total_spend ASC) AS cohort_rank
    FROM customer_spend_totals
),
cohort_mapping AS (
    SELECT
        customer_id,
        CASE cohort_rank
            WHEN 1 THEN 'LOW'
            WHEN 2 THEN 'MEDIUM'
            WHEN 3 THEN 'HIGH'
        END AS spend_cohort
    FROM cohort_ranks
),
transaction_aggregates AS (
    SELECT
        t.customer_id,
        -- Home Purchase Signals
        COALESCE(SUM(CASE WHEN t.merchant_category = 'FURNITURE_STORES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS furniture_spend_90d,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'APPLIANCES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS appliance_spend_90d,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'REAL_ESTATE_PORTALS' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN 1 ELSE 0 END), 0) AS real_estate_visits_90d,
        MAX(CASE WHEN t.merchant_category = 'HOME_INSURANCE' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN 1 ELSE 0 END) AS insurance_payment_flag,
        
        -- Relocation Signals
        COALESCE(SUM(CASE WHEN t.merchant_category = 'MOVING_COMPANIES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS moving_spend_90d,
        MAX(CASE WHEN t.merchant_category = 'NEW_CITY_UTILITIES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) AND t.txn_city != c.city THEN 1 ELSE 0 END) AS new_city_utility_flag,
        
        -- Marriage Signals
        COALESCE(SUM(CASE WHEN t.merchant_category = 'JEWELRY_STORES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS jewelry_spend_90d,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'WEDDING_VENUES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS wedding_spend_90d,
        
        -- New Child Signals
        MAX(CASE WHEN t.merchant_category = 'MATERNITY_HOSPITAL' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN 1 ELSE 0 END) AS hospital_payment_flag,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'BABY_PRODUCTS' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 30 DAY) THEN t.amount ELSE 0 END), 0.00) AS baby_product_spend_30d,
        
        -- Pharmacy Spike Baseline Spends
        COALESCE(SUM(CASE WHEN t.merchant_category = 'PHARMACY' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 30 DAY) THEN t.amount ELSE 0 END), 0.00) AS pharm_30d,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'PHARMACY' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 120 DAY) AND t.txn_date < DATE_SUB('2026-06-05', INTERVAL 30 DAY) THEN t.amount ELSE 0 END), 0.00) AS pharm_30_120d,
        
        -- Higher Education Signals
        MAX(CASE WHEN t.merchant_category = 'UNIVERSITY_FEES' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN 1 ELSE 0 END) AS university_fee_flag,
        COALESCE(SUM(CASE WHEN t.merchant_category = 'TEST_PREP' AND t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.amount ELSE 0 END), 0.00) AS test_prep_spend_90d,
        
        -- Total spend components for 3-month spend growth calculations
        COALESCE(SUM(CASE WHEN t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 30 DAY) THEN t.amount ELSE 0 END), 0.00) AS spend_30d,
        COALESCE(SUM(CASE WHEN t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) AND t.txn_date < DATE_SUB('2026-06-05', INTERVAL 30 DAY) THEN t.amount ELSE 0 END), 0.00) AS spend_30_90d,
        
        -- Location Diversity
        COUNT(DISTINCT CASE WHEN t.txn_date >= DATE_SUB('2026-06-05', INTERVAL 90 DAY) THEN t.txn_city END) AS distinct_cities_90d
    FROM transactions t
    INNER JOIN customers c ON t.customer_id = c.customer_id
    WHERE t.status = 'completed' AND c.opted_out = 0
    GROUP BY t.customer_id
)
SELECT
    a.customer_id,
    '2026-06-05' AS feature_date,
    a.furniture_spend_90d,
    a.appliance_spend_90d,
    a.real_estate_visits_90d,
    a.insurance_payment_flag,
    a.moving_spend_90d,
    a.new_city_utility_flag,
    a.jewelry_spend_90d,
    a.wedding_spend_90d,
    a.hospital_payment_flag,
    a.baby_product_spend_30d,
    -- Spike: Current 30d spend > 2x the 30d average of preceding 90d (or purchase made after zero baseline)
    CASE 
        WHEN a.pharm_30d > 2.0 * (a.pharm_30_120d / 3.0) THEN 1
        WHEN a.pharm_30d > 0.0 AND a.pharm_30_120d = 0.0 THEN 1
        ELSE 0
    END AS pharmacy_spend_spike,
    a.university_fee_flag,
    a.test_prep_spend_90d,
    -- Growth rate: (spend_last_30d - baseline_avg_30d) / baseline_avg_30d
    CASE
        WHEN a.spend_30_90d > 0.0 THEN ROUND((a.spend_30d - (a.spend_30_90d / 2.0)) / (a.spend_30_90d / 2.0), 4)
        ELSE 0.0000
    END AS spend_growth_3m,
    m.spend_cohort,
    -- If no transactions in 90 days, defaults to 1 distinct city (home city)
    CASE WHEN a.distinct_cities_90d > 0 THEN a.distinct_cities_90d ELSE 1 END AS distinct_cities_90d
FROM transaction_aggregates a
LEFT JOIN cohort_mapping m ON a.customer_id = m.customer_id;
