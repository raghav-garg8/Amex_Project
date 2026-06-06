"""
test_rfm.py
FinSight — Customer Behavioral Intelligence Platform

Unit tests for RFM Customer Value Scoring Engine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
from scoring.rfm_engine import compute_rfm_raw, score_rfm, assign_segment

def test_compute_rfm_raw():
    # Setup simple transactions
    data = {
        'customer_id': [1, 1, 2],
        'txn_date': ['2026-06-01', '2026-06-03', '2026-05-20'],
        'amount': [100.0, 150.0, 50.0]
    }
    df = pd.DataFrame(data)
    
    snapshot = datetime.strptime('2026-06-05', '%Y-%m-%d')
    rfm_raw = compute_rfm_raw(df, snapshot_date=snapshot)
    
    assert len(rfm_raw) == 2
    
    # Customer 1: last txn June 3 (2 days recency), freq 2, monetary 250
    c1 = rfm_raw[rfm_raw['customer_id'] == 1].iloc[0]
    assert c1['recency_days'] == 2
    assert c1['frequency'] == 2
    assert c1['monetary'] == 250.0

    # Customer 2: last txn May 20 (16 days recency), freq 1, monetary 50
    c2 = rfm_raw[rfm_raw['customer_id'] == 2].iloc[0]
    assert c2['recency_days'] == 16
    assert c2['frequency'] == 1
    assert c2['monetary'] == 50.0

def test_score_rfm_quintiles():
    # Setup 5 customers to fill 5 quintiles (NTILE(5))
    raw_data = {
        'customer_id': [1, 2, 3, 4, 5],
        # Recency: lower days should get higher R score (recent = best)
        'recency_days': [5, 10, 15, 20, 25],
        'frequency': [10, 8, 6, 4, 2],
        'monetary': [1000.0, 800.0, 600.0, 400.0, 200.0]
    }
    df_raw = pd.DataFrame(raw_data)
    scored = score_rfm(df_raw)
    
    # Customer 1 (best): R=5, F=5, M=5
    c1 = scored[scored['customer_id'] == 1].iloc[0]
    assert c1['R'] == 5
    assert c1['F'] == 5
    assert c1['M'] == 5
    assert c1['rfm_score'] == '555'
    assert c1['rfm_combined'] == 15

    # Customer 5 (worst): R=1, F=1, M=1
    c5 = scored[scored['customer_id'] == 5].iloc[0]
    assert c5['R'] == 1
    assert c5['F'] == 1
    assert c5['M'] == 1
    assert c5['rfm_score'] == '111'
    assert c5['rfm_combined'] == 3

def test_assign_segment():
    # Setup various R and F scores to test segment mapping
    test_cases = [
        {'customer_id': 1, 'R': 5, 'F': 5, 'M': 5, 'recency_days': 1, 'frequency': 10, 'monetary': 100},
        {'customer_id': 2, 'R': 3, 'F': 4, 'M': 5, 'recency_days': 10, 'frequency': 8, 'monetary': 100},
        {'customer_id': 3, 'R': 4, 'F': 1, 'M': 1, 'recency_days': 2, 'frequency': 1, 'monetary': 10},
        {'customer_id': 4, 'R': 1, 'F': 1, 'M': 1, 'recency_days': 30, 'frequency': 1, 'monetary': 10},
        {'customer_id': 5, 'R': 2, 'F': 4, 'M': 4, 'recency_days': 20, 'frequency': 8, 'monetary': 100},
        {'customer_id': 6, 'R': 3, 'F': 2, 'M': 2, 'recency_days': 10, 'frequency': 2, 'monetary': 50},
    ]
    df = pd.DataFrame(test_cases)
    df['rfm_score'] = df['R'].astype(str) + df['F'].astype(str) + df['M'].astype(str)
    df['rfm_combined'] = df[['R', 'F', 'M']].sum(axis=1)
    
    segmented = assign_segment(df)
    
    # Verify mappings
    assert segmented[segmented['customer_id'] == 1].iloc[0]['segment'] == 'Champions'
    assert segmented[segmented['customer_id'] == 2].iloc[0]['segment'] == 'Loyal'
    assert segmented[segmented['customer_id'] == 3].iloc[0]['segment'] == 'New Customer'
    assert segmented[segmented['customer_id'] == 4].iloc[0]['segment'] == 'Lost'
    assert segmented[segmented['customer_id'] == 5].iloc[0]['segment'] == 'Cannot Lose'
    assert segmented[segmented['customer_id'] == 6].iloc[0]['segment'] == 'Promising'
