# tests/test_scoring.py
"""Unit Tests for LifeEventScorer rules.

Tests all five life event scoring functions for zero spends, full scaling,
and missing keys/null variables.
"""

import pytest
from scoring.life_event_scorer import (
    compute_home_score,
    compute_relocation_score,
    compute_marriage_score,
    compute_child_score,
    compute_edu_score
)

def test_home_score_limits():
    # 1. Zero state (empty features)
    assert compute_home_score({}) == 0.0

    # 2. Maximum scaling state (all signals at threshold caps)
    max_features = {
        "furniture_spend_90d": 60000.0,  # threshold 50k
        "appliance_spend_90d": 35000.0,  # threshold 30k
        "real_estate_visits_90d": 3,      # threshold 2+ visits
        "insurance_payment_flag": 1,     # binary flag
        "spend_growth_3m": 0.45          # growth flag > 30%
    }
    # Should evaluate to 30 (furniture) + 25 (appliance) + 20 (visits) + 15 (ins) + 10 (growth) = 100
    assert compute_home_score(max_features) == 100.0

    # 3. Partial scaling
    partial_features = {
        "furniture_spend_90d": 25000.0,  # 50% of threshold (15.0 points)
        "appliance_spend_90d": 0.0,      # 0 points
        "real_estate_visits_90d": 1,      # 1 visit (10.0 points)
        "insurance_payment_flag": 0,     # 0 points
        "spend_growth_3m": 0.10          # 0 points
    }
    # Sum: 15.0 + 10.0 = 25.0
    assert compute_home_score(partial_features) == 25.0

def test_relocation_score_limits():
    # 1. Zero state
    assert compute_relocation_score({}) == 0.0

    # 2. Max state
    max_features = {
        "moving_spend_90d": 25000.0,
        "new_city_utility_flag": 1,
        "distinct_cities_90d": 4,
        "spend_growth_3m": 0.50
    }
    # Sum: 35 (moving) + 25 (utility) + 30 (cities >= 3) + 10 (growth) = 100
    assert compute_relocation_score(max_features) == 100.0

    # 3. Partial state
    partial_features = {
        "moving_spend_90d": 10000.0,  # 50% of threshold (17.5 points)
        "new_city_utility_flag": 0,
        "distinct_cities_90d": 2,      # 15.0 points
        "spend_growth_3m": 0.20
    }
    # Sum: 17.5 + 15.0 = 32.5
    assert compute_relocation_score(partial_features) == 32.5

def test_marriage_score_limits():
    assert compute_marriage_score({}) == 0.0

    max_features = {
        "jewelry_spend_90d": 45000.0,
        "wedding_spend_90d": 85000.0, # Combined venue+travel threshold is 80k
        "spend_growth_3m": 0.40
    }
    assert compute_marriage_score(max_features) == 100.0

def test_child_score_limits():
    assert compute_child_score({}) == 0.0

    max_features = {
        "hospital_payment_flag": 1,
        "baby_product_spend_30d": 20000.0,
        "pharmacy_spend_spike": 1,
        "spend_growth_3m": 0.35
    }
    assert compute_child_score(max_features) == 100.0

def test_education_score_limits():
    assert compute_edu_score({}) == 0.0

    max_features = {
        "university_fee_flag": 1,
        "test_prep_spend_90d": 12000.0,
        "spend_growth_3m": 0.32
    }
    assert compute_edu_score(max_features) == 100.0
