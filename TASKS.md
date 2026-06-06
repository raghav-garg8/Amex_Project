# TASKS.md — Project Roadmap and Task Backlog

This file serves as the master task tracking board for the **FinSight** project. It outlines development milestones, task priorities, and completion statuses.

---

## Milestone Summary

| Milestone | Phase | Description | Status |
|---|---|---|---|
| **Milestone 0** | Initialization | Project memory, architecture, decisions, rules | **COMPLETED** |
| **Milestone 1** | Ingestion | Synthetic data generation, Pandas anomaly cleaning, DB loader | **COMPLETED** |
| **Milestone 2** | DB & SQL | MySQL schema, indices, rolling window & cohort queries | **COMPLETED** |
| **Milestone 3** | Scoring | Python life-event scorers, arbitration conflict resolver | **COMPLETED** |
| **Milestone 4** | Engagement | EWMA engagement engine, channel diversity, fused opportunity score | **COMPLETED** |
| **Milestone 5** | Feedback | A/B simulator, back-test precision validator, SQL feedback loops | **COMPLETED** |
| **Milestone 6** | Dashboard | Power BI DAX measures, table specifications, and guides | **COMPLETED** |
| **Milestone 7** | Upgrade | FinSight project upgrade, RFM, spend velocity, fusion index | **COMPLETED** |

---

## Detailed Milestone Backlog

### Milestone 0: Project Setup & Memory Initialization (Completed)
- [x] Extract project requirements from discussions and target outcomes.
- [x] Create project memory files (`PROJECT.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TASKS.md`, `AGENTS.md`) in root.
- [x] Map database structure, scoring weights, and design constraints.

---

### Milestone 1: Data Generation & Ingestion Pipeline (Completed)
*Goal: Generate realistic transaction and click engagement logs, identify anomalies, and sanitize data.*

* [x] **Task 1.1:** Build `pipeline/generate_data.py`
  - Use `Faker` and `NumPy` to simulate 1,000 customers, 200 merchants, 80 categories, and 12 months of raw transaction history (~50,000 rows).
  - Inject specific anomalies (duplicates, negative spend, future dates, invalid merchant categories) to test cleaning layers.
  - Generate ~15,000 raw engagement events across channels (email, app, web, SMS).
* [x] **Task 1.2:** Implement `pipeline/clean_transform.py`
  - Load generated CSVs into Pandas.
  - Scan for and handle anomalies: deduplicate, clamp out-of-bounds probability scores, correct boolean type mismatches, and standardize date strings to `YYYY-MM-DD`.
  - Save an anomaly log report containing error rates and resolution counts in `logs/`.
* [x] **Task 1.3:** Setup Local Database Environment
  - Configure native local MySQL instance.
  - Set up port binding and local connection parameters.
* [x] **Task 1.4:** Create Database Loader `pipeline/load_to_db.py`
  - Establish a connection pool to MySQL.
  - Write ingestion logic to insert cleaned transactions, engagement logs, and reference tables into the database.

---

### Milestone 2: MySQL Schema & Analytics Aggregations (Completed)
*Goal: Define database tables and create high-performance SQL queries for rolling aggregations and cohorts.*

* [x] **Task 2.1:** Write Database Schema `database/schema.sql`
  - Create the DDL for all 12 tables defined in `DATA_DICTIONARY.md`.
  - Set up primary/foreign keys, enum fields, and performance-critical composite indexes.
* [x] **Task 2.2:** Build SQL Queries (`database/queries/`)
  - `rolling_window.sql`: Write queries calculating rolling 90-day category spend aggregates.
  - `cohort_analysis.sql`: Implement `NTILE(3)` logic to dynamically segment customers into spend groups.
  - `signal_detection.sql`: Query transaction frequencies and utility setups to output the final `customer_features` table.
  - `engagement_analytics.sql`: Retrieve raw click/open frequencies.
* [x] **Task 2.3:** Automate Feature Aggregation
  - Build a shell or Python script to execute SQL schema and query pipelines to populate `customer_features`.

---

### Milestone 3: Python Scoring Engine & Arbitration (Completed)
*Goal: Write the rules-based scoring calculations and the resolution logic for multi-event ties.*

* [x] **Task 3.1:** Create Scorer Config `scoring/scoring_config.py`
  - Store configurable weights, scoring thresholds, and event boundaries.
* [x] **Task 3.2:** Implement Scorer `scoring/life_event_scorer.py`
  - Write distinct scoring functions for all 5 life events using the scaling formulas in `SCORING_METHODOLOGY.md`.
  - Handle null aggregates or edge-case missing values safely.
* [x] **Task 3.3:** Build Arbitration Engine `scoring/arbitration_engine.py`
  - Implement priority logic: score gap wins first, recency tiebreaks second, and business priority hierarchy third.
  - Ensure it outputs the selected event, recommended card, conflict flag, and a text rationale.
* [x] **Task 3.4:** Write Scoring Unit Tests
  - Build `tests/test_scoring.py` and `tests/test_arbitration.py` using `pytest` to test scorer boundaries and arbitration tie-breakers.

---

### Milestone 4: EWMA Engagement & Score Fusion (Completed)
*Goal: Build the digital interaction engine and combine transaction intent with engagement bias.*

* [x] **Task 4.1:** Build EWMA Engine `engagement/ewma_engine.py`
  - Write sequential calculations for smoothing email opens, clicks, and redemptions with $\alpha = 0.5$.
* [x] **Task 4.2:** Implement Combined Scorer `engagement/combined_scorer.py`
  - Calculate the channel diversity multiplier (rewards multi-channel clicks up to +45%).
  - Fuse transaction scores with engagement and channel multipliers; cap results at 100.
  - Write output rows back to MySQL `customer_scores` table.
* [x] **Task 4.3:** Build Engagement Unit Tests
  - Create `tests/test_ewma.py` to validate temporal decay calculations.

---

### Milestone 5: Outcome Feedback & A/B Simulation (Completed)
*Goal: Simulate customer campaign conversions, test precision/recall, and run A/B analyses.*

* [x] **Task 5.1:** Build Feedback Loop Simulator `pipeline/feedback_loop.py`
  - Simulate purchase events occurring in the 60-day window following scoring recommendation.
  - Write outcomes (converted, conversion date) to `offer_conversions`.
* [x] **Task 5.2:** Create Back-Testing Evaluator
  - Calculate and report system precision and recall across all five life events.
  - Confirm precision is meeting targets (e.g., Relocation $\ge$ 0.72, New Child $\ge$ 0.75).
* [x] **Task 5.3:** Build A/B Simulation Validator
  - Group customers into treatment (scored recommendations) and control (generic offers).
  - Calculate conversion rate uplifts, statistical significance, and estimated revenue impact.

---

### Milestone 6: Power BI Specification & Templates (Completed)
*Goal: Document visualization measures and finalize dashboard specifications.*

* [x] **Task 6.1:** Document DAX Measures `docs/POWERBI_GUIDE.md`
  - Write out all DAX queries for calculated columns (e.g., Conversion Rate, Spend Cohorts) and measures (e.g., Total Revenue Uplift, Active Flag Counts).
* [x] **Task 6.2:** Finalize Dashboard Layout and Mockups
  - Specify page layouts, charts, and filter interactions for Executive, Customer Intelligence, and Product Recommendation dashboards.

---

### Milestone 7: FinSight Platform Upgrade (Completed)
*Goal: Rebrand the entire repository, extend DDL schema, implement RFM/Spend Velocity/Priority Fusion scoring engines, and write SQL query packages.*

* [x] **Task 7.1:** Overwrite `README.md` with new FinSight template.
* [x] **Task 7.2:** Append new tables (`customer_rfm`, `customer_velocity`, `customer_priority`) to `database/schema.sql`.
* [x] **Task 7.3:** Update `scoring/scoring_config.py` with DB settings and RFM/Velocity thresholds.
* [x] **Task 7.4:** Globally rebrand brand name references (LifeEventRadar/Amex to FinSight) in all 20+ scripts and markdown documentations.
* [x] **Task 7.5:** Implement `scoring/rfm_engine.py` using Pandas quintiles.
* [x] **Task 7.6:** Implement customer-relative Z-score `scoring/velocity_detector.py`.
* [x] **Task 7.7:** Implement the fusion formula logic in `fusion/priority_index.py`.
* [x] **Task 7.8:** Create SQL queries `rfm_scoring.sql` and `velocity_anomaly.sql` in `database/queries/`.
* [x] **Task 7.9:** Create test suites `tests/test_rfm.py` and `tests/test_velocity.py`.
* [x] **Task 7.10:** Run all automated tests and confirm successful integration runs.
