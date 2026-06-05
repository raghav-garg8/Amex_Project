# LifeEventRadar 🎯
## Behavioral Signal Detection & Offer Intelligence Platform

> **Built to mirror the analytical thinking of American Express's Risk Product & Data Strategy team.**
> Detects customers approaching major life events through transaction + engagement signals,
> scores behavioral intent using weighted rule engines, and surfaces product recommendations
> through three audience-specific Power BI dashboards.

---

## The Business Question This Solves

> *"What card product or offer should AmEx show this customer — 90 days before their life changes?"*

A customer buying furniture, visiting real estate portals, and opening a home-offer email is not
just spending money. They are sending behavioral signals that, read correctly, represent a
₹45,000+ annual spend opportunity on a premium card. This project builds the engine that reads
those signals, scores them, and turns them into product actions — before the customer ever
tells anyone their life is changing.

---

## Project Architecture

```
Raw Transaction Data          Raw Engagement Data
         │                            │
         ▼                            ▼
┌─────────────────────────────────────────────┐
│         Layer 1 — Data Ingestion            │
│   Anomaly detection · Cleaning · Typing     │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│         Layer 2 — SQL Analytics Engine      │
│  Rolling windows · Cohorts · CTEs · Ranks   │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│     Layer 3 — Python Scoring Engine         │
│  Life event scoring · EWMA engagement ·     │
│  Combined opportunity score · Arbitration   │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│     Layer 4 — Engagement Intelligence       │
│  Email opens · Offer clicks · Redemptions · │
│  Channel diversity · CTR by category        │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│     Layer 5 — Outcome Feedback Loop         │
│  Conversion tracking · Score validation ·   │
│  Back-test · A/B simulation                 │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│     Layer 6 — Power BI Dashboards           │
│  Executive · Customer Intelligence ·        │
│  Product Recommendation                     │
└─────────────────────────────────────────────┘
```

---

## The 5 Life Events Detected

| Life Event | Score Threshold | Key Signals | AmEx Product Action |
|---|---|---|---|
| 🏠 Home Purchase | ≥ 70 | Furniture, appliances, real estate, insurance | Home loan offer, concierge upgrade |
| 📦 Relocation | ≥ 65 | Moving cos., cargo, forex, new city utilities | Travel card, lounge access |
| 💍 Marriage | ≥ 60 | Jewelry, venues, catering, honeymoon travel | Luxury rewards card, partner card |
| 👶 New Child | ≥ 60 | Hospital, baby products, pharmacy spike, pediatrics | Family benefits, cashback essentials |
| 🎓 Higher Education | ≥ 55 | University fees, test prep, student housing | Student card, education loan referral |

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Generation | Python · Faker · NumPy | Realistic synthetic transaction + engagement data |
| Data Cleaning | Python · Pandas | Anomaly detection, type correction, deduplication |
| Analytics Engine | MySQL | Rolling windows, cohorts, CTEs, window functions |
| Scoring Engine | Python | Weighted rule-based signal scoring |
| Engagement Engine | Python · EWMA | Recency-weighted multi-channel engagement scoring |
| Feedback Loop | Python | Outcome simulation, back-test, A/B analysis |
| Visualization | Power BI | 3 audience-specific dashboards |
| Documentation | Markdown | Full IDE-ready project docs |

---

## Repository Structure

```
LifeEventRadar/
│
├── README.md                        ← You are here
├── PROJECT.md                       ← Project vision and workflows
├── ARCHITECTURE.md                  ← Full system design and boundaries
├── DECISIONS.md                     ← Architectural decisions and tradeoffs
├── TASKS.md                         ← Project milestone backlog
├── AGENTS.md                        ← AI Agent operating guidelines
├── DATA_DICTIONARY.md               ← Every table and column explained
├── SCORING_METHODOLOGY.md          ← Weight justification (interview-ready)
│
├── docs/
│   ├── POWERBI_GUIDE.md             ← Dashboard design and DAX measures
│   ├── ETHICS_AND_GOVERNANCE.md     ← Data ethics, compliance, opt-out
│   └── INTERVIEW_PREP.md            ← Anticipated questions + answers
│
├── database/
│   ├── schema.sql                   ← All CREATE TABLE statements
│   ├── seed_data.sql                ← Sample inserts for testing
│   └── queries/
│       ├── rolling_window.sql       ← 90-day rolling aggregations
│       ├── cohort_analysis.sql      ← Spend cohort segmentation
│       ├── signal_detection.sql     ← Category-level signal queries
│       ├── engagement_analytics.sql ← Email/click/redemption queries
│       └── validation_queries.sql   ← Back-test and sanity checks
│
├── pipeline/
│   ├── generate_data.py             ← Synthetic data generator
│   ├── clean_transform.py           ← Anomaly detection + cleaning
│   └── load_to_db.py                ← MySQL loader
│
├── scoring/
│   ├── life_event_scorer.py         ← All 5 scoring functions
│   ├── arbitration_engine.py        ← Conflict resolution logic
│   └── scoring_config.py            ← Weights + thresholds (configurable)
│
├── engagement/
│   ├── ewma_engine.py               ← Recency-weighted engagement scoring
│   ├── channel_analyser.py          ← Multi-channel diversity scoring
│   └── combined_scorer.py           ← Transaction × Engagement fusion
│
├── tests/
│   ├── test_scoring.py              ← Unit tests for scoring functions
│   ├── test_arbitration.py          ← Arbitration edge case tests
│   └── test_ewma.py                 ← EWMA validation tests
│
└── data/
    ├── sample_transactions.csv      ← 1000-row sample for testing
    ├── sample_engagement.csv        ← 500-row engagement sample
    └── merchant_categories.csv      ← Category → signal weight mapping
```

---

## Key Analytical Techniques Used

- **Rolling 90-day window aggregations** — SQL window functions with ROWS BETWEEN
- **EWMA recency scoring** — Exponentially weighted engagement with α=0.5
- **Multi-signal arbitration** — Conflict resolution when two events score above threshold
- **Spend cohort segmentation** — Equal-population Low/Medium/High splits
- **Channel diversity multiplier** — Rewards multi-channel engagement over single-channel
- **CLV uplift estimation** — Business impact quantification per flagged customer
- **Outcome back-testing** — Simulated conversion validation of scoring accuracy
- **A/B simulation** — Offer conversion comparison between flagged and control groups

---

## Business Impact Estimate

```
Customers flagged for Home Purchase:     ~500
Average incremental annual spend:        ₹45,000
Total revenue opportunity (Home):        ₹2.25 Crore

Customers flagged across all events:     ~2,000
Blended avg. incremental spend:          ₹32,000
Total cross-event opportunity:           ₹6.4 Crore
```

> These estimates use conservative CLV assumptions. Methodology documented
> in `docs/SCORING_METHODOLOGY.md`.

---

## Ethical Framework

This project follows financial services data ethics standards:

- All signals derived from **anonymised, aggregated** transaction patterns
- No individual-level PII used or exposed
- Customer **opt-out simulation** included in schema design
- Signal scoring is **transparent and auditable** — every weight is documented
- No third-party data sharing modelled

Full details in `docs/ETHICS_AND_GOVERNANCE.md`

---

## How to Run

```bash
# 1. Clone and set up environment
git clone https://github.com/yourusername/LifeEventRadar
cd LifeEventRadar
pip install -r requirements.txt

# 2. Generate synthetic data
python pipeline/generate_data.py

# 3. Clean and validate
python pipeline/clean_transform.py

# 4. Load into MySQL
python pipeline/load_to_db.py

# 5. Run scoring engine
python scoring/life_event_scorer.py

# 6. Run engagement layer
python engagement/combined_scorer.py

# 7. Connect Power BI to MySQL and load dashboard template
# See docs/POWERBI_GUIDE.md for step-by-step instructions
```

---

## CV Description (Copy-Ready)

```
LifeEventRadar — Behavioral Signal Detection & Offer Intelligence Platform

Built an end-to-end behavioral analytics platform that detects customers approaching
5 major life events (home purchase, relocation, marriage, new child, higher education)
using 12 months of synthetic transaction data combined with multi-channel engagement
signals. Engineered a weighted rule-based scoring engine with EWMA recency weighting
(α=0.5), multi-signal arbitration logic, and a channel diversity multiplier. Designed
a 15-table MySQL schema with rolling 90-day window aggregations, cohort segmentation,
and CTEs. Built 3 audience-specific Power BI dashboards (Executive, Customer
Intelligence, Product Recommendation) with estimated ₹6.4 Cr revenue opportunity
quantification. Incorporated data ethics governance and outcome back-testing to
validate scoring accuracy — aligned with American Express's behavioral analytics
and offer personalization framework.
```
