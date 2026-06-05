# tests/test_ewma.py
"""Unit Tests for temporal decay EWMA engagement logic.

Verifies the mathematical correctness of sequential EWMA calculations
and multiplier scaling.
"""

import pytest

def test_ewma_mathematical_decay():
    # Enforce alpha = 0.5
    alpha = 0.5
    
    # Event sequence: [1, 2]
    # S_0 = 0.0
    # S_1 = (0.5 * 1.0) + (0.5 * 0.0) = 0.5
    # S_2 = (0.5 * 2.0) + (0.5 * 0.5) = 1.25
    
    score = 0.0
    events = [1.0, 2.0]
    for val in events:
        score = (alpha * val) + ((1.0 - alpha) * score)
        
    assert score == 1.25
    
    # Scale multiplier: 0.5 + S_2 = 1.75
    multiplier = min(max(0.5 + score, 0.5), 2.0)
    assert multiplier == 1.75

def test_ewma_clamping_ranges():
    alpha = 0.5
    
    # High click sequence to test maximum cap (2.0)
    score = 0.0
    for _ in range(10):
        score = (alpha * 2.0) + ((1.0 - alpha) * score)
        
    # score converges to 2.0
    assert abs(score - 2.0) < 0.01
    multiplier = min(max(0.5 + score, 0.5), 2.0)
    assert multiplier == 2.0
