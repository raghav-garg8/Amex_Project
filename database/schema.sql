-- database/schema.sql
-- Database DDL schema for FinSight.
-- Consists of all 12 tables with proper relationships and indexes.

-- -------------------------------------------------------------------------
-- Clean existing tables in reverse dependency order
-- -------------------------------------------------------------------------
DROP TABLE IF EXISTS customer_priority;
DROP TABLE IF EXISTS customer_velocity;
DROP TABLE IF EXISTS customer_rfm;
DROP TABLE IF EXISTS opt_out_registry;
DROP TABLE IF EXISTS offer_conversions;
DROP TABLE IF EXISTS customer_scores;
DROP TABLE IF EXISTS customer_features;
DROP TABLE IF EXISTS campaign_clicks;
DROP TABLE IF EXISTS reward_redemptions;
DROP TABLE IF EXISTS email_opens;
DROP TABLE IF EXISTS offer_views;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS merchants;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS merchant_categories;

-- -------------------------------------------------------------------------
-- Reference Table: merchant_categories
-- -------------------------------------------------------------------------
CREATE TABLE merchant_categories (
    category_id SMALLINT UNSIGNED NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    life_event_tag ENUM('home_purchase', 'relocation', 'marriage', 'new_child', 'higher_education', 'neutral') NOT NULL,
    signal_weight TINYINT UNSIGNED NOT NULL,
    signal_type ENUM('spend_scaled', 'binary', 'frequency', 'neutral') NOT NULL,
    spend_threshold DECIMAL(10,2) NULL,
    description VARCHAR(200) NULL,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Master Profile Table: customers
-- -------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id INT UNSIGNED NOT NULL,
    age TINYINT UNSIGNED NOT NULL,
    city VARCHAR(50) NOT NULL,
    income_band ENUM('LOW', 'MEDIUM', 'HIGH', 'PREMIUM') NOT NULL,
    card_type VARCHAR(30) NOT NULL,
    join_date DATE NOT NULL,
    life_stage VARCHAR(30) NULL,
    opted_out TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id),
    INDEX idx_city (city),
    INDEX idx_card_type (card_type),
    INDEX idx_income_band (income_band)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Reference Table: merchants
-- -------------------------------------------------------------------------
CREATE TABLE merchants (
    merchant_id INT UNSIGNED NOT NULL,
    merchant_name VARCHAR(100) NOT NULL,
    category_id SMALLINT UNSIGNED NOT NULL,
    city VARCHAR(50) NULL,
    is_partner TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (merchant_id),
    CONSTRAINT fk_merchants_category FOREIGN KEY (category_id) REFERENCES merchant_categories (category_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Core Ledger Table: transactions
-- -------------------------------------------------------------------------
CREATE TABLE transactions (
    txn_id BIGINT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    merchant_id INT UNSIGNED NOT NULL,
    merchant_category VARCHAR(50) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    txn_date DATE NOT NULL,
    txn_city VARCHAR(100) NULL,
    channel ENUM('online', 'in_store', 'contactless', 'international') NOT NULL,
    status ENUM('completed', 'pending', 'reversed') NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (txn_id),
    CONSTRAINT fk_transactions_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    CONSTRAINT fk_transactions_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id) ON DELETE RESTRICT,
    -- Core analytical index keys for rolling 90-day aggregations
    INDEX idx_customer_date (customer_id, txn_date),
    INDEX idx_customer_category (customer_id, merchant_category),
    INDEX idx_txn_date (txn_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Engagement Table: offer_views
-- -------------------------------------------------------------------------
CREATE TABLE offer_views (
    view_id BIGINT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    offer_id VARCHAR(30) NOT NULL,
    offer_category VARCHAR(50) NOT NULL,
    channel ENUM('email', 'app', 'web', 'sms') NOT NULL,
    viewed_at TIMESTAMP NOT NULL,
    was_clicked TINYINT(1) NOT NULL DEFAULT 0,
    placement_id VARCHAR(30) NULL,
    PRIMARY KEY (view_id),
    CONSTRAINT fk_offer_views_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_customer_view (customer_id, viewed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Engagement Table: email_opens
-- -------------------------------------------------------------------------
CREATE TABLE email_opens (
    open_id BIGINT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    campaign_id VARCHAR(30) NOT NULL,
    offer_category VARCHAR(50) NOT NULL,
    opened_at TIMESTAMP NOT NULL,
    device_type ENUM('mobile', 'desktop', 'tablet') NULL,
    PRIMARY KEY (open_id),
    CONSTRAINT fk_email_opens_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_customer_open (customer_id, opened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Engagement Table: reward_redemptions
-- -------------------------------------------------------------------------
CREATE TABLE reward_redemptions (
    redemption_id INT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    points_redeemed INT UNSIGNED NOT NULL,
    redemption_category VARCHAR(50) NOT NULL,
    redeemed_at TIMESTAMP NOT NULL,
    dollar_value DECIMAL(8,2) NOT NULL,
    PRIMARY KEY (redemption_id),
    CONSTRAINT fk_reward_red_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_customer_redemption (customer_id, redeemed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Engagement Table: campaign_clicks
-- -------------------------------------------------------------------------
CREATE TABLE campaign_clicks (
    click_id BIGINT UNSIGNED NOT NULL,
    customer_id INT UNSIGNED NOT NULL,
    campaign_id VARCHAR(30) NOT NULL,
    offer_category VARCHAR(50) NOT NULL,
    channel ENUM('email', 'app', 'web', 'sms') NOT NULL,
    clicked_at TIMESTAMP NOT NULL,
    PRIMARY KEY (click_id),
    CONSTRAINT fk_campaign_clicks_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_customer_click (customer_id, clicked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Pre-aggregated SQL Features: customer_features
-- -------------------------------------------------------------------------
CREATE TABLE customer_features (
    customer_id INT UNSIGNED NOT NULL,
    feature_date DATE NOT NULL,
    furniture_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    appliance_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    real_estate_visits_90d TINYINT NOT NULL DEFAULT 0,
    insurance_payment_flag TINYINT(1) NOT NULL DEFAULT 0,
    moving_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    new_city_utility_flag TINYINT(1) NOT NULL DEFAULT 0,
    jewelry_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    wedding_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    hospital_payment_flag TINYINT(1) NOT NULL DEFAULT 0,
    baby_product_spend_30d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    pharmacy_spend_spike TINYINT(1) NOT NULL DEFAULT 0,
    university_fee_flag TINYINT(1) NOT NULL DEFAULT 0,
    test_prep_spend_90d DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    spend_growth_3m DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
    spend_cohort ENUM('LOW', 'MEDIUM', 'HIGH') NULL,
    distinct_cities_90d TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (customer_id),
    CONSTRAINT fk_customer_features_cust FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Output Table: customer_scores
-- -------------------------------------------------------------------------
CREATE TABLE customer_scores (
    score_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id INT UNSIGNED NOT NULL,
    score_date DATE NOT NULL,
    home_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    relocation_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    marriage_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    child_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    edu_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    top_event VARCHAR(30) NULL,
    engagement_multiplier DECIMAL(4,3) NOT NULL DEFAULT 1.000,
    channel_multiplier DECIMAL(4,3) NOT NULL DEFAULT 1.000,
    opportunity_score DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    recommended_product VARCHAR(100) NULL,
    conflict_flag TINYINT(1) NOT NULL DEFAULT 0,
    arbitration_reason VARCHAR(200) NULL,
    PRIMARY KEY (score_id),
    CONSTRAINT fk_customer_scores_cust FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_customer_score_date (customer_id, score_date),
    INDEX idx_score_date (score_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Outcome Table: offer_conversions
-- -------------------------------------------------------------------------
CREATE TABLE offer_conversions (
    conversion_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id INT UNSIGNED NOT NULL,
    score_date DATE NOT NULL,
    top_event VARCHAR(30) NULL,
    recommended_product VARCHAR(100) NULL,
    offer_sent_at TIMESTAMP NULL,
    converted TINYINT(1) NOT NULL DEFAULT 0,
    converted_at TIMESTAMP NULL,
    conversion_window_days TINYINT NULL,
    group_type ENUM('treatment', 'control') NOT NULL DEFAULT 'treatment',
    PRIMARY KEY (conversion_id),
    CONSTRAINT fk_offer_conversions_cust FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    INDEX idx_conversion_customer (customer_id),
    INDEX idx_conversion_date (score_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Compliance Registry Table: opt_out_registry
-- -------------------------------------------------------------------------
CREATE TABLE opt_out_registry (
    opt_out_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id INT UNSIGNED NOT NULL,
    opted_out_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    opt_out_channel VARCHAR(30) NOT NULL,
    reinstated_at TIMESTAMP NULL,
    PRIMARY KEY (opt_out_id),
    CONSTRAINT fk_opt_out_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    UNIQUE KEY uq_customer_opt_out (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- Table: customer_rfm
-- Stores RFM scores computed by rfm_engine.py
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_rfm (
    rfm_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id     INT UNSIGNED NOT NULL,
    score_date      DATE NOT NULL,
    recency_days    INT UNSIGNED NOT NULL,
    frequency       INT UNSIGNED NOT NULL,
    monetary        DECIMAL(14,2) NOT NULL,
    R_score         TINYINT UNSIGNED NOT NULL COMMENT '1-5, higher=better',
    F_score         TINYINT UNSIGNED NOT NULL COMMENT '1-5, higher=better',
    M_score         TINYINT UNSIGNED NOT NULL COMMENT '1-5, higher=better',
    rfm_score       CHAR(3) NOT NULL COMMENT 'e.g. 543',
    rfm_combined    TINYINT UNSIGNED NOT NULL COMMENT 'Sum of R+F+M, 3-15',
    segment         VARCHAR(30) NOT NULL,
    PRIMARY KEY (rfm_id),
    UNIQUE KEY uq_customer_date (customer_id, score_date),
    INDEX idx_segment (segment),
    INDEX idx_rfm_combined (rfm_combined),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT 'RFM customer value scores — computed by rfm_engine.py';


-- ============================================================
-- Table: customer_velocity
-- Stores spend velocity Z-scores from velocity_detector.py
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_velocity (
    velocity_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id     INT UNSIGNED NOT NULL,
    score_date      DATE NOT NULL,
    current_spend   DECIMAL(14,2),
    baseline_mean   DECIMAL(14,2),
    baseline_std    DECIMAL(14,2),
    velocity_score  DECIMAL(8,4) NOT NULL DEFAULT 0.0000,
    velocity_label  VARCHAR(40) NOT NULL DEFAULT 'Normal',
    velocity_weight DECIMAL(5,3) NOT NULL DEFAULT 1.000,
    months_of_data  TINYINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (velocity_id),
    UNIQUE KEY uq_customer_date (customer_id, score_date),
    INDEX idx_velocity_score (velocity_score),
    INDEX idx_velocity_label (velocity_label),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT 'Spend velocity anomaly scores — computed by velocity_detector.py';


-- ============================================================
-- Table: customer_priority
-- Stores the fused Customer Priority Index from priority_index.py
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_priority (
    priority_id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id             INT UNSIGNED NOT NULL,
    score_date              DATE NOT NULL,
    life_event_score        DECIMAL(5,1),
    rfm_segment             VARCHAR(30),
    rfm_weight              DECIMAL(5,3),
    velocity_weight         DECIMAL(5,3),
    engagement_multiplier   DECIMAL(5,3),
    channel_multiplier      DECIMAL(5,3),
    priority_index          DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    top_event               VARCHAR(30),
    recommended_product     VARCHAR(100),
    action_tier             ENUM('IMMEDIATE','HIGH','MEDIUM','LOW')
                            NOT NULL DEFAULT 'LOW',
    PRIMARY KEY (priority_id),
    UNIQUE KEY uq_customer_date (customer_id, score_date),
    INDEX idx_priority_index (priority_index),
    INDEX idx_action_tier (action_tier),
    INDEX idx_rfm_event (rfm_segment, top_event),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT 'Customer Priority Index — fused output of all 3 engines';
