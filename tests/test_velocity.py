"""
test_velocity.py
FinSight — Customer Behavioral Intelligence Platform

Unit tests for spend velocity anomaly detector.
"""

import pytest
import pandas as pd
import numpy as np
from scoring.velocity_detector import compute_velocity_scores, compute_velocity_weight

def test_compute_velocity_scores_normal():
    # Setup spend history for a customer with normal variations
    # 7 months: 6 baseline + 1 current
    history = {
        'customer_id': [1]*7,
        'month_start': [
            '2025-11-01', '2025-12-01', '2026-01-01',
            '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01'
        ],
        'monthly_spend': [
            1000.0, 1200.0, 1100.0, 1300.0, 1000.0, 1200.0, 2000.0
        ]
    }
    df = pd.DataFrame(history)
    results = compute_velocity_scores(df)
    
    assert len(results) == 1
    row = results.iloc[0]
    
    # Baseline mean = (1000+1200+1100+1300+1000+1200)/6 = 1133.33
    # Baseline std = standard deviation of those 6 values = 121.106
    # Current spend = 2000
    # Z-score = (2000 - 1133.33) / 121.106 = 7.156
    assert row['current_spend'] == 2000.0
    assert row['baseline_mean'] == 1133.33
    assert row['baseline_std'] == 121.11
    assert row['velocity_score'] > 2.0
    assert row['velocity_label'] == 'Strong Positive Anomaly'

def test_compute_velocity_scores_zero_std():
    # Customer spends exactly the same amount every month
    history = {
        'customer_id': [2]*7,
        'month_start': [
            '2025-11-01', '2025-12-01', '2026-01-01',
            '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01'
        ],
        'monthly_spend': [1000.0]*7
    }
    df = pd.DataFrame(history)
    results = compute_velocity_scores(df)
    
    assert len(results) == 1
    row = results.iloc[0]
    assert row['baseline_std'] == 0.0
    assert row['velocity_score'] == 0.0
    assert row['velocity_label'] == 'Normal'

def test_compute_velocity_scores_insufficient_history():
    # Customer has only 2 months of history
    history = {
        'customer_id': [3]*2,
        'month_start': ['2026-04-01', '2026-05-01'],
        'monthly_spend': [1000.0, 1500.0]
    }
    df = pd.DataFrame(history)
    results = compute_velocity_scores(df)
    
    assert len(results) == 1
    row = results.iloc[0]
    assert row['velocity_label'] == 'Insufficient History'
    assert row['velocity_score'] == 0.0

def test_compute_velocity_weight():
    # Test clamping limits [0.5, 1.5]
    # Formula: multiplier = 1.0 + (velocity_score * 0.15)
    
    # 1. Normal (velocity_score = 0.0) -> multiplier = 1.0
    assert compute_velocity_weight(0.0) == 1.0
    
    # 2. Positive anomaly (velocity_score = 2.0) -> multiplier = 1.0 + 0.30 = 1.30
    assert compute_velocity_weight(2.0) == 1.30
    
    # 3. Very high anomaly (velocity_score = 10.0) -> multiplier = 1.0 + 1.50 = 2.50 -> clamped to 1.50
    assert compute_velocity_weight(10.0) == 1.50
    
    # 4. Negative anomaly (velocity_score = -2.0) -> multiplier = 1.0 - 0.30 = 0.70
    assert compute_velocity_weight(-2.0) == 0.70
    
    # 5. Very low anomaly (velocity_score = -5.0) -> multiplier = 1.0 - 0.75 = 0.25 -> clamped to 0.50
    assert compute_velocity_weight(-5.0) == 0.50
    
    # 6. Null input -> multiplier = 1.0
    assert compute_velocity_weight(None) == 1.0
    assert compute_velocity_weight(np.nan) == 1.0
