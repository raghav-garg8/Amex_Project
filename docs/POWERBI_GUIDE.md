# docs/POWERBI_GUIDE.md — Power BI Visualization Guide

This guide details the layout specifications, data connections, calculated fields, and DAX measures required to build the three audience-specific Power BI dashboards for **FinSight**.

---

## 1. Database Connections & Refresh Strategy

* **Connector:** MySQL Database connector.
* **Host:** `127.0.0.1` (or `localhost`)
* **Database:** `finsight_db`
* **Tables Imported:**
  - `customers` (Import Mode)
  - `customer_scores` (Import or DirectQuery Mode, depending on refresh frequency)
  - `offer_conversions` (Import Mode)
* **Relationships:**
  - `customers` (1) ── (many) `customer_scores` on `customer_id`
  - `customers` (1) ── (many) `offer_conversions` on `customer_id`

---

## 2. Calculated Columns & DAX Measures

To display metrics dynamically, create the following measures and columns in your Power BI model.

### Calculated Columns (Table: `offer_conversions`)

1. **Incremental Annual Spend Contribution (INR):**
   *Assigns estimated annual spend uplift values to each customer based on their completed conversion.*
   ```dax
   IncrementalSpend = 
   IF(
       offer_conversions[converted] = 1,
       SWITCH(
           offer_conversions[top_event],
           "home_purchase", 45000,
           "relocation", 35000,
           "marriage", 35000,
           "new_child", 25000,
           "higher_education", 20000,
           0
       ),
       0
   )
   ```

### Measures (Table: `offer_conversions`)

1. **Campaign Conversion Rate (Treatment Group):**
   *The percentage of flagged targeted customers who accepted the card offer.*
   ```dax
   TreatmentConversionRate = 
   DIVIDE(
       CALCULATE(SUM(offer_conversions[converted]), offer_conversions[group_type] = "treatment"),
       CALCULATE(COUNT(offer_conversions[conversion_id]), offer_conversions[group_type] = "treatment"),
       0
   )
   ```

2. **Control Conversion Rate (Control Group):**
   *The conversion rate of the benchmark cohort receiving generic offers.*
   ```dax
   ControlConversionRate = 
   DIVIDE(
       CALCULATE(SUM(offer_conversions[converted]), offer_conversions[group_type] = "control"),
       CALCULATE(COUNT(offer_conversions[conversion_id]), offer_conversions[group_type] = "control"),
       0
   )
   ```

3. **Targeted Campaign Uplift (%):**
   *Measures the performance improvement of targeted campaigns over generic offers.*
   ```dax
   CampaignConversionUplift = 
   DIVIDE(
       [TreatmentConversionRate] - [ControlConversionRate],
       [ControlConversionRate],
       0
   )
   ```

4. **Total Incremental Portfolio Spend (INR Crore):**
   *Sum of all realized annual spend contributions, formatted in Crores (Cr) for executive views.*
   ```dax
   TotalIncrementalSpend = SUM(offer_conversions[IncrementalSpend])
   ```

5. **Campaign ROI Projection (Projected 100% targeting):**
   *Projects the revenue value if targeted campaigns were rolled out to the entire portfolio.*
   ```dax
   ProjectedRevenueOpportunity = DIVIDE([TotalIncrementalSpend], 0.80, 0)
   ```

---

## 3. Dashboard Layout & Visualizations Specification

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD 1: EXECUTIVE VIEW                     │
│                                                                        │
│  [ KPI: Total Spend Opportunity ]     [ KPI: Blended Conv. Uplift ]    │
│            ₹6.40 Cr                             +240.5%                │
│                                                                        │
│  ┌──────────────────────────────┐     ┌─────────────────────────────┐  │
│  │ Spend Uplift by Life Event   │     │ Treatment vs Control Rate   │  │
│  │   Home:  ₹2.25 Cr            │     │   A (Targeted):  68.5%      │  │
│  │   Baby:  ₹1.50 Cr            │     │   B (Generic):   22.1%      │  │
│  │   Marr:  ₹1.20 Cr            │     │                             │  │
│  └──────────────────────────────┘     └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### Dashboard 1: Executive View
* **Audience:** C-Suite & business unit heads.
* **Layout Grid:**
  - **Top Ribbon Cards:**
    - KPI 1: *Total Realized Spend Opportunity* (`TotalIncrementalSpend`)
    - KPI 2: *Projected Spend Opportunity* (`ProjectedRevenueOpportunity`)
    - KPI 3: *Blended Conversion Uplift* (`CampaignConversionUplift`)
  - **Main Chart (Left):** Horizontal bar chart mapping *Total Spend Opportunity by Life Event* (`top_event` on Axis, `TotalIncrementalSpend` on Values).
  - **Main Chart (Right):** Clustered column chart showing *Conversion Rate by Group* (Group Type on Axis, Conversion Rate on Values) to visually prove campaign effectiveness.

### Dashboard 2: Customer Intelligence View
* **Audience:** Risk Analysts and Data Scientists.
* **Layout Grid:**
  - **Top Filters:** Slicer by `customer_id` and dropdown slicer by `spend_cohort`.
  - **Evidence Table:** Columns: `customer_id`, `home_score`, `relocation_score`, `marriage_score`, `child_score`, `edu_score`.
  - **Arbitration Details Panel:** HTML Viewer or Multi-row card showing `top_event`, `conflict_flag` (True/False status), and the text column `arbitration_reason` to provide an audit trail for the selected recommend trigger.

### Dashboard 3: Product Recommendation View
* **Audience:** Campaign Managers and Offer Teams.
* **Layout Grid:**
  - **Top Filters:** Slicer by `top_event` and `recommended_product`.
  - **Product Distribution Chart:** Donut chart showing customer counts by `recommended_product`.
  - **Target Leads List Table:** Columns: `customer_id`, `age`, `city`, `card_type`, `recommended_product`, `opportunity_score`, `channel_multiplier` (helps prioritize which leads are highest conviction and which channels they prefer).
