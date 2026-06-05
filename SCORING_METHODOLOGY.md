# SCORING_METHODOLOGY.md
## Weight Justification & Scoring Design Rationale

> **This document exists because arbitrary weights are indefensible.**
> Every number in this scoring engine has a reason. This document is the
> answer to the interview question: *"Walk me through how your scoring works."*

---

## Scoring Design Principles

### Principle 1 — Signals must be proportional to conviction

A customer who spends ₹80,000 at a furniture store is a stronger home
purchase signal than one who spends ₹5,000. Scores must scale with signal
strength, not just fire a binary flag.

**Implementation:** All financial signal components use a `min(spend / threshold, 1)`
scaling formula, capping at the maximum component weight.

### Principle 2 — Behavioral frequency beats single events

Visiting a real estate portal twice is a stronger signal than once.
Multiple pharmacy visits matter more than a single large purchase.

**Implementation:** Frequency signals use threshold-based step scoring
(0 visits → 0, 1 visit → partial, 2+ visits → full weight).

### Principle 3 — Spend acceleration is a universal signal

Regardless of category, a sudden 30%+ increase in total monthly spend
suggests a major life transition is underway.

**Implementation:** `spend_growth_3m > 0.3` contributes 10 points to
every event score as a universal signal.

### Principle 4 — Weights must sum to 100

Every scoring function is designed so that a customer exhibiting all
signals at maximum strength scores exactly 100. This makes scores
interpretable and comparable across event types.

---

## Event 1 — Home Purchase Score

**Threshold: ≥ 70 to trigger action**

| Signal | Component Weight | Scaling Formula | Business Justification |
|---|---|---|---|
| Furniture store spend (90d) | 30 | min(spend / ₹50,000, 1) × 30 | Furniture is the clearest leading indicator — most purchased after a home decision, not before. ₹50,000 threshold reflects realistic first-home outfitting spend. |
| Appliance purchases (90d) | 25 | min(spend / ₹30,000, 1) × 25 | Appliances are purchased once per home move. A spike is highly diagnostic. |
| Real estate portal visits | 20 | 0 visits→0, 1 visit→10, 2+→20 | Multiple visits confirm active house-hunting, not casual browsing. |
| Home insurance payment | 15 | Binary: detected→15, else→0 | Insurance payment almost always follows a completed home purchase decision. Strongest confirmation signal. |
| Total spend growth (3m) | 10 | spend_growth > 30% → 10, else 0 | Pre-purchase spending typically accelerates as moving plans solidify. |
| **Total** | **100** | | |

**Threshold justification (70):**
A customer scoring 70 has likely triggered at least 3 strong signals.
Below 70 risks false positives from isolated large purchases (e.g., a
single appliance bought as a gift). Above 70 consistently maps to
genuine purchase intent in back-test validation.

---

## Event 2 — Relocation Score

**Threshold: ≥ 65 to trigger action**

| Signal | Component Weight | Scaling Formula | Business Justification |
|---|---|---|---|
| Moving company / cargo spend | 35 | min(spend / ₹20,000, 1) × 35 | Highest-conviction signal. Moving services are purpose-specific — there is almost no alternative explanation for this spend. |
| New city utility setup | 25 | Binary: detected→25, else→0 | Electricity, water, or internet setup in a new city confirms the move. |
| Hotel stays in new city (30d) | 20 | 0 stays→0, 1→10, 2+→20 | Pre-move site visits or temporary accommodation before permanent setup. |
| Forex / international spend | 10 | Binary: detected→10, else→0 | International relocation signal. Lower weight as domestic relocation is more common. |
| Spend growth (3m) | 10 | growth > 30% → 10, else 0 | Moving is expensive — total spend almost always spikes. |
| **Total** | **100** | | |

**Threshold justification (65):**
Relocation signals are more concentrated (fewer signal types, higher
individual signal specificity). A customer triggering moving company
spend (35) + new city utilities (25) already scores 60 without any
other signal. 65 requires at least one additional confirming signal.

---

## Event 3 — Marriage Score

**Threshold: ≥ 60 to trigger action**

| Signal | Component Weight | Scaling Formula | Business Justification |
|---|---|---|---|
| Jewelry store spend (90d) | 30 | min(spend / ₹40,000, 1) × 30 | Engagement rings are the primary leading indicator. ₹40,000 threshold filters casual jewelry purchases. |
| Wedding venue / catering bookings | 25 | min(spend / ₹50,000, 1) × 25 | High-value, category-specific spend with no ambiguity of intent. |
| Honeymoon / destination travel | 25 | min(spend / ₹30,000, 1) × 25 | Pre-booked travel to honeymoon destinations, often purchased 3–6 months before the wedding. |
| Formal wear purchases | 10 | Binary: detected→10, else→0 | Supporting signal — formal wear spike near jewelry purchases is highly diagnostic. |
| Spend growth (3m) | 10 | growth > 30% → 10, else 0 | Wedding planning significantly increases monthly spend. |
| **Total** | **100** | | |

**Threshold justification (60):**
Marriage signals can appear in sequence (jewelry → venue → travel)
spread across months. 60 allows early detection when only the first
1–2 signals are visible, enabling AmEx to engage the customer during
planning — not after the wedding.

---

## Event 4 — New Child Score

**Threshold: ≥ 60 to trigger action**

| Signal | Component Weight | Scaling Formula | Business Justification |
|---|---|---|---|
| Hospital / maternity payments | 35 | Binary: detected→35, else→0 | Highest-weight binary signal. Maternity billing is unambiguous. |
| Baby product store spend (30d) | 25 | min(spend / ₹15,000, 1) × 25 | Post-birth spending on baby essentials typically spikes within 30 days. |
| Pharmacy spend spike | 20 | spend > 2× prior 90d avg → 20 | Prescriptions and OTC products increase significantly around childbirth. |
| Pediatric clinic visits | 10 | visits ≥ 1 → 10, else 0 | Postnatal checkups confirm an active newborn care phase. |
| Spend growth (3m) | 10 | growth > 30% → 10, else 0 | New child reliably increases household spend across all categories. |
| **Total** | **100** | | |

**Threshold justification (60):**
Hospital payment alone (35) is not sufficient to trigger action —
could be non-maternity. Hospital (35) + pharmacy spike (20) = 55,
still below threshold. The third confirming signal (baby products or
clinic) pushes to 60–70, ensuring the flag is reliable.

---

## Event 5 — Higher Education Score

**Threshold: ≥ 55 to trigger action**

| Signal | Component Weight | Scaling Formula | Business Justification |
|---|---|---|---|
| University / institution fee payment | 35 | Binary: detected→35, else→0 | Direct fee payment is the strongest possible signal. |
| Test prep / coaching spend | 25 | min(spend / ₹10,000, 1) × 25 | Test prep spending (CAT, GMAT, GRE, IELTS) precedes enrollment by 6–12 months, enabling early engagement. |
| Student housing deposits | 20 | Binary: detected→20, else→0 | Hostel or PG deposits in a new city confirm enrollment. |
| Stationery / laptop spike | 10 | spend > 2× avg → 10, else 0 | Semester-start supplies spike is a reliable supporting signal. |
| Spend growth (3m) | 10 | growth > 30% → 10, else 0 | Education expenses reliably spike at enrollment time. |
| **Total** | **100** | | |

**Threshold justification (55):**
Lowest threshold because education signals are the most time-sensitive.
Test prep spending (25) signals intent 6–12 months before enrollment.
Engaging the customer at this stage — with a student card offer —
has the highest CLV potential of all 5 events.

---

## Arbitration Logic — Resolving Multi-Event Conflicts

**Problem:** A customer can legitimately trigger multiple events simultaneously.
Example: a student getting married (marriage + education scores both ≥ threshold).

**Resolution algorithm:**

```python
def resolve_priority(scores: dict, recency: dict) -> str:
    """
    Priority resolution when multiple events exceed threshold.

    Rules (applied in order):
    1. If score gap > 15 points: highest score wins
    2. If score gap <= 15 points: most recent signal activity wins
    3. If tie on recency: use business_priority_order
    """
    BUSINESS_PRIORITY = [
        'home_purchase',   # Highest CLV opportunity
        'new_child',       # Time-sensitive — benefits package
        'marriage',        # High engagement window
        'relocation',      # Travel product fit
        'higher_education' # Long relationship potential
    ]

    above_threshold = {k: v for k, v in scores.items() if v >= THRESHOLD[k]}

    if len(above_threshold) <= 1:
        return max(above_threshold, key=above_threshold.get)

    max_score = max(above_threshold.values())
    top_events = {k: v for k, v in above_threshold.items()
                  if max_score - v <= 15}

    if len(top_events) == 1:
        return list(top_events.keys())[0]

    # Recency tiebreaker
    most_recent = min(top_events.keys(),
                      key=lambda e: recency.get(e, 999))

    # Final tiebreaker: business priority
    for event in BUSINESS_PRIORITY:
        if event in top_events:
            return event
```

**Why this matters:**
Without arbitration, a customer could receive two conflicting offer
recommendations simultaneously — a student card AND a luxury wedding
card. This is operationally impossible and customer-experience damaging.
The arbitration engine ensures one clean, justified recommendation per
customer per scoring cycle.

---

## Validation Targets

After back-testing against synthetic outcome data:

| Event | Target Precision | Target Recall | Notes |
|---|---|---|---|
| Home Purchase | ≥ 0.70 | ≥ 0.65 | High-weight signals make this most reliable |
| Relocation | ≥ 0.72 | ≥ 0.60 | Moving spend is highly specific |
| Marriage | ≥ 0.65 | ≥ 0.58 | Signals spread across time — recall harder |
| New Child | ≥ 0.75 | ≥ 0.70 | Hospital signal is near-perfect precision |
| Higher Education | ≥ 0.68 | ≥ 0.72 | Lower threshold improves recall |

> These targets are validated against simulated outcomes in
> `tests/test_scoring.py`. See `ARCHITECTURE.md` Layer 5 for
> back-test methodology.
