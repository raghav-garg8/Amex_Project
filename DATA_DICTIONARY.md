# DATA_DICTIONARY.md
## Complete Table and Column Reference

> Every table, every column, every constraint — documented.
> This is what professional data teams produce before writing a single query.

---

## Database: `finsight_db`

### Table Index

| Table | Rows (approx.) | Purpose |
|---|---|---|
| customers | 1,000 | Customer master profile |
| transactions | ~50,000 | 12-month transaction history |
| merchant_categories | ~80 | Category → signal weight mapping |
| merchants | ~200 | Merchant master data |
| offer_views | ~8,000 | Offer impression events |
| email_opens | ~4,000 | Email marketing open events |
| reward_redemptions | ~2,000 | Reward point redemption events |
| campaign_clicks | ~3,000 | CTA click events across channels |
| customer_features | 1,000 | Pre-aggregated SQL features for scoring |
| customer_scores | 1,000 | Final scores + recommendations |
| offer_conversions | ~500 | Simulated outcome data for back-testing |
| opt_out_registry | variable | Customers who opted out of behavioral scoring |

---

## Table: `customers`

**Purpose:** Master customer profile table. One row per customer.

| Column | Type | Nullable | Description |
|---|---|---|---|
| customer_id | INT UNSIGNED | NOT NULL PK | Unique customer identifier. Auto-increment. |
| age | TINYINT UNSIGNED | NOT NULL | Customer age in years. Range: 18–75. |
| city | VARCHAR(50) | NOT NULL | Current city of residence. |
| income_band | ENUM | NOT NULL | Income bracket: 'LOW', 'MEDIUM', 'HIGH', 'PREMIUM' |
| card_type | VARCHAR(30) | NOT NULL | Current card tier: 'Standard', 'Premium', 'Elite' |
| join_date | DATE | NOT NULL | Date customer joined the platform. |
| life_stage | VARCHAR(30) | NULL | Self-reported life stage: 'Student', 'Young Professional', 'Family', 'Senior'. Used for segmentation only — NOT used in scoring. |
| opted_out | TINYINT(1) | NOT NULL DEFAULT 0 | 1 = opted out of behavioral scoring. Customers with opted_out=1 are excluded from all scoring pipelines. |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT | Record creation timestamp. |

**Indexes:**
```sql
PRIMARY KEY (customer_id)
INDEX idx_city (city)
INDEX idx_card_type (card_type)
INDEX idx_income_band (income_band)
```

---

## Table: `transactions`

**Purpose:** Core transaction history. One row per transaction event.

| Column | Type | Nullable | Description |
|---|---|---|---|
| txn_id | BIGINT UNSIGNED | NOT NULL PK | Unique transaction ID. |
| customer_id | INT UNSIGNED | NOT NULL FK | References customers.customer_id |
| merchant_id | INT UNSIGNED | NOT NULL FK | References merchants.merchant_id |
| merchant_category | VARCHAR(50) | NOT NULL | Category of merchant. Denormalised for query performance. |
| amount | DECIMAL(12,2) | NOT NULL | Transaction amount in INR. Must be > 0 after cleaning. |
| txn_date | DATE | NOT NULL | Transaction date. |
| txn_city | VARCHAR(50) | NULL | City where transaction occurred. Used for relocation detection. |
| channel | ENUM | NOT NULL | Transaction channel: 'online', 'in_store', 'contactless', 'international' |
| status | ENUM | NOT NULL | 'completed', 'pending', 'reversed'. Only 'completed' used in scoring. |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT | Record insertion timestamp. |

**Indexes:**
```sql
PRIMARY KEY (txn_id)
INDEX idx_customer_date (customer_id, txn_date)
INDEX idx_customer_category (customer_id, merchant_category)
INDEX idx_txn_date (txn_date)
```

**Business rules:**
- `amount` must be > 0. Negative values excluded during cleaning.
- `txn_date` must be ≤ CURDATE(). Future dates excluded during cleaning.
- Only `status = 'completed'` rows included in all scoring calculations.

---

## Table: `merchant_categories`

**Purpose:** Maps merchant categories to life event signals and their weights.
This is the configuration layer of the scoring engine.

| Column | Type | Nullable | Description |
|---|---|---|---|
| category_id | SMALLINT UNSIGNED | NOT NULL PK | Unique category ID. |
| category_name | VARCHAR(50) | NOT NULL UNIQUE | Human-readable category name. |
| life_event_tag | ENUM | NOT NULL | Which event this category signals: 'home_purchase', 'relocation', 'marriage', 'new_child', 'higher_education', 'neutral' |
| signal_weight | TINYINT UNSIGNED | NOT NULL | Base weight contribution (1–40). See SCORING_METHODOLOGY.md. |
| signal_type | ENUM | NOT NULL | 'spend_scaled', 'binary', 'frequency' — determines scoring formula applied. |
| spend_threshold | DECIMAL(10,2) | NULL | For spend_scaled signals: the amount at which full weight is awarded. NULL for binary/frequency signals. |
| description | VARCHAR(200) | NULL | Human-readable explanation of why this category is a signal. |

**Sample rows:**
```
category_name          life_event_tag    signal_weight  signal_type   spend_threshold
FURNITURE_STORES       home_purchase     30             spend_scaled  50000.00
MOVING_COMPANIES       relocation        35             spend_scaled  20000.00
JEWELRY_STORES         marriage          30             spend_scaled  40000.00
MATERNITY_HOSPITAL     new_child         35             binary        NULL
UNIVERSITY_FEES        higher_education  35             binary        NULL
REAL_ESTATE_PORTALS    home_purchase     20             frequency     NULL
```

---

## Table: `merchants`

**Purpose:** Master merchant reference.

| Column | Type | Nullable | Description |
|---|---|---|---|
| merchant_id | INT UNSIGNED | NOT NULL PK | Unique merchant ID. |
| merchant_name | VARCHAR(100) | NOT NULL | Merchant display name (synthetic). |
| category_id | SMALLINT UNSIGNED | NOT NULL FK | References merchant_categories.category_id |
| city | VARCHAR(50) | NULL | Primary operating city. |
| is_partner | TINYINT(1) | NOT NULL DEFAULT 0 | 1 = merchant partnership. Used for offer targeting. |

---

## Table: `offer_views`

**Purpose:** Records when a customer was shown an offer (impression event).
Mirrors the offer_action variable in the FinSight dataset.

| Column | Type | Nullable | Description |
|---|---|---|---|
| view_id | BIGINT UNSIGNED | NOT NULL PK | Unique view event ID. |
| customer_id | INT UNSIGNED | NOT NULL FK | Customer who saw the offer. |
| offer_id | VARCHAR(30) | NOT NULL | Offer identifier. |
| offer_category | VARCHAR(50) | NOT NULL | Category of offer: 'travel', 'home', 'lifestyle', 'rewards', 'education' |
| channel | ENUM | NOT NULL | Delivery channel: 'email', 'app', 'web', 'sms' |
| viewed_at | TIMESTAMP | NOT NULL | When the offer was shown. |
| was_clicked | TINYINT(1) | NOT NULL DEFAULT 0 | 1 = customer clicked the offer CTA. |
| placement_id | VARCHAR(30) | NULL | Where on the page/email the offer was shown. |

**Note:** `was_clicked = 1` means this offer view resulted in a click.
This is equivalent to the binary outcome variable (offer_action) in the
FinSight 2025 problem statement.

---

## Table: `email_opens`

**Purpose:** Email marketing engagement events.

| Column | Type | Nullable | Description |
|---|---|---|---|
| open_id | BIGINT UNSIGNED | NOT NULL PK | Unique open event ID. |
| customer_id | INT UNSIGNED | NOT NULL FK | Customer who opened the email. |
| campaign_id | VARCHAR(30) | NOT NULL | Email campaign identifier. |
| offer_category | VARCHAR(50) | NOT NULL | Category of offers in the email. |
| opened_at | TIMESTAMP | NOT NULL | When the email was opened. |
| device_type | ENUM | NULL | 'mobile', 'desktop', 'tablet' |

---

## Table: `reward_redemptions`

**Purpose:** Tracks when customers redeem Membership Rewards points.

| Column | Type | Nullable | Description |
|---|---|---|---|
| redemption_id | INT UNSIGNED | NOT NULL PK | Unique redemption ID. |
| customer_id | INT UNSIGNED | NOT NULL FK | Redeeming customer. |
| points_redeemed | INT UNSIGNED | NOT NULL | Number of points redeemed in this event. |
| redemption_category | VARCHAR(50) | NOT NULL | What the points were redeemed for: 'travel', 'cashback', 'shopping', 'dining' |
| redeemed_at | TIMESTAMP | NOT NULL | Redemption timestamp. |
| dollar_value | DECIMAL(8,2) | NOT NULL | Monetary equivalent of points redeemed. |

---

## Table: `campaign_clicks`

**Purpose:** CTA click events across all channels (email, app, web, SMS).

| Column | Type | Nullable | Description |
|---|---|---|---|
| click_id | BIGINT UNSIGNED | NOT NULL PK | Unique click event ID. |
| customer_id | INT UNSIGNED | NOT NULL FK | Customer who clicked. |
| campaign_id | VARCHAR(30) | NOT NULL | Campaign that generated the click. |
| offer_category | VARCHAR(50) | NOT NULL | Category of the clicked offer. |
| channel | ENUM | NOT NULL | Which channel: 'email', 'app', 'web', 'sms' |
| clicked_at | TIMESTAMP | NOT NULL | Click timestamp. |

---

## Table: `customer_features`

**Purpose:** Pre-aggregated feature table. Populated by SQL queries in
`database/queries/signal_detection.sql`. This table is what the Python
scoring engine reads directly — avoiding complex JOINs at score time.

| Column | Type | Description |
|---|---|---|
| customer_id | INT UNSIGNED PK | Customer reference. |
| feature_date | DATE | Date features were computed. |
| furniture_spend_90d | DECIMAL(12,2) | Rolling 90-day spend in FURNITURE_STORES category. |
| appliance_spend_90d | DECIMAL(12,2) | Rolling 90-day spend in APPLIANCES category. |
| real_estate_visits_90d | TINYINT | Count of real estate portal transactions in 90 days. |
| insurance_payment_flag | TINYINT(1) | 1 if home insurance payment detected in 90 days. |
| moving_spend_90d | DECIMAL(12,2) | Rolling 90-day spend on moving/cargo services. |
| new_city_utility_flag | TINYINT(1) | 1 if utility setup in a new city detected. |
| jewelry_spend_90d | DECIMAL(12,2) | Rolling 90-day spend in JEWELRY_STORES category. |
| wedding_spend_90d | DECIMAL(12,2) | Rolling 90-day spend on wedding categories. |
| hospital_payment_flag | TINYINT(1) | 1 if maternity/hospital payment detected. |
| baby_product_spend_30d | DECIMAL(12,2) | Rolling 30-day spend on baby products. |
| pharmacy_spend_spike | TINYINT(1) | 1 if pharmacy spend > 2× prior 90-day average. |
| university_fee_flag | TINYINT(1) | 1 if university fee payment detected. |
| test_prep_spend_90d | DECIMAL(12,2) | Rolling 90-day spend on test prep/coaching. |
| spend_growth_3m | DECIMAL(5,4) | 3-month spend growth rate. Positive = increasing. |
| spend_cohort | ENUM | 'LOW', 'MEDIUM', 'HIGH' — equal-population cohort assignment. |
| distinct_cities_90d | TINYINT | Number of distinct cities with transactions in 90 days. |

---

## Table: `customer_scores`

**Purpose:** Final scored output. One row per customer per scoring run.

| Column | Type | Description |
|---|---|---|
| score_id | BIGINT UNSIGNED PK | Unique score record ID. |
| customer_id | INT UNSIGNED FK | Scored customer. |
| score_date | DATE | Date scoring engine was run. |
| home_score | DECIMAL(5,1) | Home purchase event score (0–100). |
| relocation_score | DECIMAL(5,1) | Relocation event score (0–100). |
| marriage_score | DECIMAL(5,1) | Marriage event score (0–100). |
| child_score | DECIMAL(5,1) | New child event score (0–100). |
| edu_score | DECIMAL(5,1) | Higher education event score (0–100). |
| top_event | VARCHAR(30) | Event with highest score above threshold. NULL if none exceed threshold. |
| engagement_multiplier | DECIMAL(4,3) | EWMA engagement score for top event category. |
| channel_multiplier | DECIMAL(4,3) | Channel diversity multiplier (1.15–1.45). |
| opportunity_score | DECIMAL(5,1) | Combined score: life_event × engagement × channel (capped at 100). |
| recommended_product | VARCHAR(100) | product recommendation for top event. |
| conflict_flag | TINYINT(1) | 1 if multiple events scored above threshold (arbitration applied). |
| arbitration_reason | VARCHAR(200) | Why arbitration chose top_event over alternatives. NULL if no conflict. |

---

## Table: `offer_conversions`

**Purpose:** Simulated outcome table for back-testing and feedback loop.

| Column | Type | Description |
|---|---|---|
| conversion_id | INT UNSIGNED PK | Unique conversion record ID. |
| customer_id | INT UNSIGNED FK | Customer who received the offer. |
| score_date | DATE | Date when scoring recommendation was made. |
| top_event | VARCHAR(30) | Event that triggered the recommendation. |
| recommended_product | VARCHAR(100) | Product offered to customer. |
| offer_sent_at | TIMESTAMP | When offer was delivered. |
| converted | TINYINT(1) | 1 = customer took up the offer within 60 days. |
| converted_at | TIMESTAMP | NULL | When conversion occurred. NULL if not converted. |
| conversion_window_days | TINYINT | Days between offer delivery and conversion. |
| group_type | ENUM | 'treatment' (flagged customer) or 'control' (random sample). |

---

## Table: `opt_out_registry`

**Purpose:** Records customers who have opted out of behavioral scoring.
Customers in this table are excluded from ALL scoring, feature computation,
and dashboard display. See `docs/ETHICS_AND_GOVERNANCE.md`.

| Column | Type | Description |
|---|---|---|
| opt_out_id | INT UNSIGNED PK | Unique opt-out record ID. |
| customer_id | INT UNSIGNED FK | Customer who opted out. |
| opted_out_at | TIMESTAMP | When opt-out was recorded. |
| opt_out_channel | VARCHAR(30) | How opt-out was requested: 'app', 'web', 'customer_service', 'email' |
| reinstated_at | TIMESTAMP NULL | If customer later reinstated consent. NULL = still opted out. |

---

## Table: `customer_rfm`

**Purpose:** Recency, Frequency, Monetary (RFM) customer value scores and segments. Populated by `scoring/rfm_engine.py`.

| Column | Type | Description |
|---|---|---|
| rfm_id | BIGINT UNSIGNED PK | Unique RFM record ID. |
| customer_id | INT UNSIGNED FK | References customers.customer_id |
| score_date | DATE | Date the RFM scores were calculated. |
| recency_days | INT UNSIGNED | Days since the customer's last completed transaction. |
| frequency | INT UNSIGNED | Number of completed transactions in the history. |
| monetary | DECIMAL(14,2) | Total spend amount of completed transactions. |
| R_score | TINYINT UNSIGNED | Recency quintile score (1-5, where 5 is most recent). |
| F_score | TINYINT UNSIGNED | Frequency quintile score (1-5, where 5 is highest count). |
| M_score | TINYINT UNSIGNED | Monetary quintile score (1-5, where 5 is highest spend). |
| rfm_score | CHAR(3) | Concatenated RFM code (e.g. '555' for Champions). |
| rfm_combined | TINYINT UNSIGNED | Sum of R_score, F_score, and M_score (ranges from 3 to 15). |
| segment | VARCHAR(30) | Assigned customer segment (e.g. 'Champions', 'Lost'). |

---

## Table: `customer_velocity`

**Purpose:** Spend velocity anomaly scores comparing 30-day current spend with a 6-month baseline. Populated by `scoring/velocity_detector.py`.

| Column | Type | Description |
|---|---|---|
| velocity_id | BIGINT UNSIGNED PK | Unique spend velocity record ID. |
| customer_id | INT UNSIGNED FK | References customers.customer_id |
| score_date | DATE | Date the velocity scores were calculated. |
| current_spend | DECIMAL(14,2) | Spend amount in the current 30-day period. |
| baseline_mean | DECIMAL(14,2) | Mean monthly spend over the 6-month baseline. |
| baseline_std | DECIMAL(14,2) | Standard deviation of monthly spend over the baseline. |
| velocity_score | DECIMAL(8,4) | Spend velocity Z-score: `(current - baseline_mean) / baseline_std`. |
| velocity_label | VARCHAR(40) | Visual label (e.g. 'Strong Positive Anomaly', 'Declining'). |
| velocity_weight | DECIMAL(5,3) | Priority index multiplier weight (clamped between 0.500 and 1.500). |
| months_of_data | TINYINT UNSIGNED | Number of months of historical transaction data available. |

---

## Table: `customer_priority`

**Purpose:** Fused Customer Priority Index, combining all three analytic engines. Populated by `fusion/priority_index.py`.

| Column | Type | Description |
|---|---|---|
| priority_id | BIGINT UNSIGNED PK | Unique priority record ID. |
| customer_id | INT UNSIGNED FK | References customers.customer_id |
| score_date | DATE | Date the priority index was calculated. |
| life_event_score | DECIMAL(5,1) | Combined life event opportunity score (0.0-100.0). |
| rfm_segment | VARCHAR(30) | RFM segment assigned to the customer. |
| rfm_weight | DECIMAL(5,3) | Multiplier weight based on RFM segment (0.700-1.500). |
| velocity_weight | DECIMAL(5,3) | Multiplier weight based on spend velocity Z-score (0.500-1.500). |
| engagement_multiplier | DECIMAL(5,3) | EWMA email/click recency engagement multiplier (0.500-2.000). |
| channel_multiplier | DECIMAL(5,3) | Channel diversity multiplier (1.000-1.450). |
| priority_index | DECIMAL(5,2) | Fused priority score (capped at 100.00). |
| top_event | VARCHAR(30) | Win-arbitrated primary life event tag. |
| recommended_product | VARCHAR(100) | Recommended card product referral target. |
| action_tier | ENUM | Triage tier: 'IMMEDIATE', 'HIGH', 'MEDIUM', 'LOW'. |

