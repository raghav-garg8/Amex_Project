# DECISIONS.md — Architectural Decisions & Tradeoffs

This document details the core architectural decisions made for **FinSight**, the options considered, the tradeoffs evaluated, and the business or technical rationales for each choice.

---

## 1. Rule-Based Scoring Engine vs. Machine Learning Models

* **Decision:** Implement a weighted rule-based scoring engine instead of a machine learning classifier (e.g., XGBoost, Logistic Regression).
* **Options Considered:**
  1. *Supervised Machine Learning:* Training a gradient-boosted tree model on historical conversion logs.
  2. *Weighted Rule Engine:* A deterministic, score-summing engine based on predefined thresholds.
* **Tradeoffs & Evaluation:**
  - *Machine Learning:* Offers higher potential recall by detecting non-linear feature relationships. However, it requires a large volume of high-quality labeled historical data, is prone to model drift, and acts as a "black box" where specific predictions cannot be easily explained.
  - *Rule Engine:* Simpler to implement, but requires manual weight tuning. Crucially, it provides **100% transparency and explainability** for every decision.
* **Rationale for Decision:** 
  Financial services regulators require auditability for customer-affecting decisions. A rule-based engine allows customer service or risk agents to trace a score exactly: *"Customer #4012 scored 85 on Relocation due to a moving company spend of ₹25,000 (35 points) and a new city utility payment (25 points)."* It also provides stable, explainable predictions that do not suffer from sudden covariate shift.

---

## 2. EWMA (Exponentially Weighted Moving Average) vs. Simple Aggregations for Engagement

* **Decision:** Use an Exponentially Weighted Moving Average (EWMA) to smooth and score digital engagement events, rather than a simple average or count.
* **Options Considered:**
  1. *Simple Count:* Total number of email opens or app clicks in the last 90 days.
  2. *Rolling Mean:* Average daily click rate.
  3. *EWMA:* Recency-biased smoothing using $\alpha = 0.5$.
* **Tradeoffs & Evaluation:**
  - *Simple Count/Mean:* Easy to implement in SQL. However, they treat an event from 89 days ago identically to an event that happened yesterday.
  - *EWMA:* Requires sequential calculations, which are more complex, but biases the score towards the most recent interactions.
* **Rationale for Decision:**
  Customer digital interest decays exponentially. A customer who clicked a travel card offer yesterday is far more likely to convert than one who clicked 3 months ago. EWMA natively reflects this temporal decay, prioritizing recent customer interest while smoothing out daily noise.

---

## 3. Multiplicative Fusion vs. Additive Fusion for Combined Scoring

* **Decision:** Fuses transaction scores and engagement multipliers using multiplication: `opportunity_score = life_event_score * engagement_multiplier * channel_multiplier`, capped at 100.
* **Options Considered:**
  1. *Additive Scoring:* Fusing them via a weighted sum (e.g., `0.7 * transaction + 0.3 * engagement`).
  2. *Multiplicative Scoring:* Using engagement as a scaling multiplier on top of the transaction base.
* **Tradeoffs & Evaluation:**
  - *Additive:* Easy to scale and guarantees scores stay within range. However, a customer with zero engagement but maximum spend signals could still achieve a high score, leading to wasted marketing spend.
  - *Multiplicative:* Can result in high scores if multipliers are large (necessitating a cap), but ensures that if engagement is low or zero, the final opportunity score is significantly penalized.
* **Rationale for Decision:**
  Marketing conversion requires both **intent** (demonstrated by transaction spend) and **interest** (demonstrated by click engagement). A multiplicative approach behaves like an AND gate: a customer who is buying baby supplies *and* opening baby-care emails represents a high-conviction target. If they are buying supplies but deleting emails, the score is scaled down, preventing irrelevant targeting.

---

## 4. Equal-Population Cohorts vs. Fixed Brackets for Spend Segmentation

* **Decision:** Use SQL `NTILE(3)` to partition customers into equal-population Low, Medium, and High spend cohorts.
* **Options Considered:**
  1. *Fixed Spend Brackets:* Predefining thresholds (e.g., Low < ₹10k, Medium ₹10k–₹50k, High > ₹50k).
  2. *Equal-Population Cohorts:* Segmenting dynamically based on current portfolio spend distributions.
* **Tradeoffs & Evaluation:**
  - *Fixed Brackets:* Easy to document and explain. However, inflation, general spend growth, or shifts in customer demographic mix can cause populations to skew heavily into one bracket, leaving others empty.
  - *Equal-Population:* Ensures a balanced split across cohorts, but cohort boundaries shift dynamically as portfolio spend changes.
* **Rationale for Decision:**
  Equal-population segmentation is a standard risk-modelling best practice. It ensures that downstream analytical models and Power BI dashboard visual segments always have sufficient and balanced data points, regardless of seasonal shifts in portfolio-wide spending.

---

## 5. Separate Arbitration Module vs. Inline Scoring Decisions

* **Decision:** Implement conflict resolution logic in a standalone `arbitration_engine.py` rather than within individual scoring scripts.
* **Options Considered:**
  1. *Inline Logic:* Letting the life event scorer resolve ties using simple `if/else` checks during calculation.
  2. *Standalone Engine:* Outputting all raw scores first, then passing them to an independent arbitration component.
* **Tradeoffs & Evaluation:**
  - *Inline:* Fewer files and slightly faster execution. However, it tightly couples signal weights with business policy rules.
  - *Standalone:* Decouples calculations from policy. If the business priority changes, only the arbitration engine is modified.
* **Rationale for Decision:**
  Separation of concerns. Raw scoring represents the *probability of customer intent*. Arbitration represents *business targeting policy* (which product  prefers to push due to profitability, CLV, or portfolio balance). Treating these as separate software boundaries makes the codebase easier to test, maintain, and audit.

---

## 6. 90-Day Rolling Window for Signal Aggregation

* **Decision:** Standardize on a 90-day rolling window for transactional aggregations.
* **Options Considered:**
  1. *Short Window (30 Days):* Captures highly immediate spend spikes, but misses longer-tail preparation cycles.
  2. *Long Window (180 Days):* Captures early signals, but carries stale data that may no longer indicate an active transition.
  3. *Medium Window (90 Days):* The primary rolling duration for transactional features.
* **Tradeoffs & Evaluation:**
  - *30 Days:* Misses customers who buy furniture over a 2-month period before moving.
  - *180 Days:* Risk of capturing a one-off purchase from 5 months ago and misidentifying it as a near-term life change.
* **Rationale for Decision:**
  90 days is the optimal balance for consumer credit behavior. Major life events (moving, weddings, higher education) typically exhibit a 60-to-90 day preparation window. A 90-day window captures the acceleration of spend during this preparation phase while remaining fresh enough to trigger marketing campaigns before the event concludes.

---

## 7. Native Local MySQL Database vs. Docker Containerization

* **Decision:** Run database operations on a native local MySQL installation (e.g., via Homebrew or direct OS install) rather than Docker containers.
* **Options Considered:**
  1. *Containerized database:* Run MySQL via a Docker Compose recipe.
  2. *Native local database:* Run MySQL as a local background daemon service on the host OS.
* **Tradeoffs & Evaluation:**
  - *Containerized:* Offers portability across environments, but requires a running Docker daemon, which might have local execution blocks, port clashes, or CPU overhead.
  - *Native local:* Reduces runtime overhead and dependencies (no Docker required), making local CLI administration simpler, but requires manual environment configuration.
* **Rationale for Decision:**
  The user explicitly requested not to use Docker. Since a native local MySQL instance runs on the same port (`3306`) and uses the same credentials and connector protocols, it is fully compatible with all Python loaders, scoring, and analytics scripts.

