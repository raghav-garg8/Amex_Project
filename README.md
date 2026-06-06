# FinSight 🔍
## Customer Behavioral Intelligence Platform

> A multi-dimensional behavioral analytics platform that combines
> life event signal detection, RFM customer value scoring, and
> spend velocity anomaly detection to generate a Customer Priority
> Index — enabling financial institutions to make proactive,
> data-driven product decisions.

---

## The Business Question This Solves

> *"Which customers are about to change — and how valuable are
> they to us right now?"*

A customer buying furniture AND scoring as a Champion in RFM
AND showing a 280% spend velocity spike is not just a signal.
They are your highest-priority customer at their most receptive
moment. FinSight is the engine that identifies them — before
any competitor does.

---

## Platform Architecture

```
Raw Transaction Data (1.85M rows · 1,000 customers · 2 years)
                        │
                        ▼
        ┌───────────────────────────────┐
        │      Data Cleaning Layer      │
        │  Anomalies · Types · Dupes    │
        └───────────────┬───────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌───────────────┐
   │    RFM     │ │  Life    │ │    Spend      │
   │   Engine   │ │  Event   │ │   Velocity    │
   │            │ │  Scorer  │ │   Anomaly     │
   │ Past Value │ │  Future  │ │   Detector    │
   │ Recency    │ │  Intent  │ │   Behavioral  │
   │ Frequency  │ │  5 types │ │   Shift       │
   │ Monetary   │ │  EWMA    │ │   Z-score     │
   └─────┬──────┘ └────┬─────┘ └──────┬────────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
        ┌───────────────────────────────┐
        │    Customer Priority Index    │
        │   Arbitration · Fusion        │
        │   RFM × Life Event Matrix     │
        └───────────────┬───────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │Executive │  │Customer  │  │ Segment  │
   │Dashboard │  │Intel     │  │ Strategy │
   │Power BI  │  │Power BI  │  │ Power BI │
   └──────────┘  └──────────┘  └──────────┘
```

---

## Three Intelligence Engines

### Engine 1 — RFM Customer Value Scoring
Segments customers into 8 value groups (Champions, Loyal,
Potential Loyalist, At Risk, Cannot Lose, Hibernating, Lost,
New Customer) using Recency, Frequency, and Monetary scores
(each 1–5). Provides the "current relationship value" dimension.

### Engine 2 — Life Event Signal Detection
Detects customers approaching 5 major life events through
category-level transaction signals, weighted rule scoring,
and EWMA recency weighting. Provides the "future intent"
dimension.

| Life Event | Threshold | Key Signals |
|---|---|---|
| 🏠 Home Purchase | ≥ 70 | Home, shopping, insurance |
| 📦 Relocation | ≥ 65 | Travel, gas/transport, new city |
| 💍 Marriage | ≥ 60 | Personal care, shopping, travel |
| 👶 New Child | ≥ 60 | Health/fitness, kids/pets |
| 🎓 Higher Education | ≥ 55 | Misc net, shopping net |

### Engine 3 — Spend Velocity Anomaly Detection
Computes a Z-score comparing each customer's current 30-day
spend to their personal 6-month baseline. Customer-relative,
not population-relative. Catches life events that don't appear
clearly in any single category.

```
velocity_score = (spend_30d - baseline_avg) / baseline_std
score > 2.0  → significant positive anomaly
score < -2.0 → significant negative anomaly (disengagement)
```

---

## The Customer Priority Index

The fusion output that combines all three engines:

```
Priority Index = RFM_score × life_event_score
                 × engagement_multiplier
                 × velocity_weight
                 × channel_diversity_multiplier
```

A 2D RFM × Life Event matrix surfaces the most actionable
customer segments — Champions approaching home purchase score
highest; Lost customers with no signals score lowest.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data | Python · Pandas · Faker | Loading, cleaning, enrichment |
| Analytics | MySQL · Window Functions · CTEs | Feature computation |
| RFM Engine | Python · SQL NTILE | Customer value segmentation |
| Life Event Engine | Python · Weighted rules · EWMA | Signal scoring |
| Velocity Engine | Python · Z-score · Rolling stats | Anomaly detection |
| Fusion | Python · Priority Index formula | Multi-signal combination |
| Visualisation | Power BI · DAX | 3 audience dashboards |

---

## Repository Structure

```
FinSight/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SCORING_METHODOLOGY.md
│   ├── DATA_DICTIONARY.md
│   ├── POWERBI_GUIDE.md
│   ├── ETHICS_AND_GOVERNANCE.md
│   └── INTERVIEW_PREP.md
├── database/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── queries/
│       ├── rfm_scoring.sql
│       ├── rolling_window.sql
│       ├── cohort_analysis.sql
│       ├── signal_detection.sql
│       ├── velocity_anomaly.sql
│       ├── engagement_analytics.sql
│       └── validation_queries.sql
├── pipeline/
│   ├── generate_data.py
│   ├── clean_transform.py
│   └── load_to_db.py
├── scoring/
│   ├── rfm_engine.py
│   ├── life_event_scorer.py
│   ├── velocity_detector.py
│   ├── arbitration_engine.py
│   └── scoring_config.py
├── engagement/
│   ├── ewma_engine.py
│   ├── channel_analyser.py
│   └── combined_scorer.py
├── fusion/
│   └── priority_index.py
├── tests/
│   ├── test_rfm.py
│   ├── test_scoring.py
│   ├── test_velocity.py
│   └── test_arbitration.py
└── data/
    ├── sample_transactions.csv
    └── merchant_categories.csv
```

---

## Industry Applications

This platform is applicable across any financial institution
that holds transaction-level customer data:

- **Retail banks** — HDFC, ICICI, SBI, Axis, Kotak
- **Card networks** — Visa, Mastercard, RuPay
- **Fintech lenders** — Bajaj Finserv, Capital Float, KreditBee
- **Payment platforms** — Paytm, PhonePe, Razorpay
- **BNPL providers** — LazyPay, ZestMoney, Simpl
- **Wealth platforms** — Zerodha, Groww, Scripbox
- **Insurance** — PolicyBazaar, Digit, Acko
- **Global card issuers** — Any institution with transaction
  and engagement data and a product recommendation objective

---

## Key Analytical Techniques

- **RFM segmentation** — 8-group customer value classification
- **Rolling 90-day window aggregations** — SQL ROWS BETWEEN
- **EWMA recency scoring** — α=0.5 recency-weighted engagement
- **Z-score velocity anomaly detection** — customer-relative baseline
- **Multi-signal arbitration** — conflict resolution engine
- **RFM × Life Event matrix** — 2D priority heatmap
- **CLV uplift estimation** — revenue impact quantification
- **Outcome back-testing** — simulated conversion validation
- **A/B simulation** — flagged vs control group comparison
- **Channel diversity multiplier** — multi-channel engagement reward

---

## Business Impact Estimate

```
Champion customers flagged for home purchase:    ~120
Average incremental annual spend (premium card): ₹60,000
Revenue opportunity (Champions only):            ₹72 Lakh

At-Risk customers with life event signals:       ~180
Recovery opportunity (correct re-engagement):    ₹45 Lakh

Total cross-segment revenue opportunity:         ₹6.4 Crore+
```

---

## CV Description (Copy-Ready)

```
FinSight — Customer Behavioral Intelligence Platform

Built an end-to-end multi-dimensional behavioral analytics
platform combining three intelligence engines: RFM customer
value scoring (8-segment classification), life event signal
detection (5 event types, EWMA-weighted rule engine with
arbitration logic), and Z-score spend velocity anomaly
detection. Fused outputs into a Customer Priority Index with
a 2D RFM × Life Event matrix. Built on 1.85M real transactions
(kaggle.com/datasets/kartik2112/fraud-detection) across 1,000
customers using Python, MySQL (20+ window function queries,
CTEs, rolling aggregations), and Power BI (3 audience-specific
dashboards: Executive, Customer Intelligence, Segment Strategy).
Includes data ethics governance, outcome back-testing, and A/B
simulation. Applicable across retail banking, fintech lending,
BNPL, and payment platforms.
```
