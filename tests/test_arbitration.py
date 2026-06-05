# tests/test_arbitration.py
"""Unit Tests for Arbitration Engine conflict resolution.

Tests Score Gap win rules, Recency date tie-breaking, and Business Priority
rules in the arbitration_engine module.
"""

import pytest
from scoring.arbitration_engine import resolve_priority

def test_no_event_above_threshold():
    scores = {"home_purchase": 50.0, "relocation": 40.0}
    event, prod, flag, reason = resolve_priority(scores, {})
    assert event is None
    assert flag == 0

def test_single_event_wins():
    scores = {"home_purchase": 75.0, "relocation": 50.0}
    event, prod, flag, reason = resolve_priority(scores, {})
    assert event == "home_purchase"
    assert flag == 0

def test_score_gap_rule():
    # Gap > 15: home_purchase (85) exceeds relocation (68) by 17 points
    scores = {"home_purchase": 85.0, "relocation": 68.0}
    event, prod, flag, reason = resolve_priority(scores, {})
    assert event == "home_purchase"
    assert flag == 1
    assert "Score gap rule" in reason

def test_recency_rule_wins():
    # Gap <= 15 (75 vs 70), relocation has a more recent transaction signal
    scores = {"home_purchase": 75.0, "relocation": 70.0}
    recency = {"home_purchase": "2026-05-10", "relocation": "2026-06-01"}
    event, prod, flag, reason = resolve_priority(scores, recency)
    assert event == "relocation"
    assert flag == 1
    assert "Recency rule" in reason

def test_business_priority_rule():
    # Gap <= 15 (75 vs 72), same date (or no date)
    # home_purchase has higher business priority than relocation
    scores = {"home_purchase": 72.0, "relocation": 75.0}
    recency = {"home_purchase": "2026-06-01", "relocation": "2026-06-01"}
    event, prod, flag, reason = resolve_priority(scores, recency)
    assert event == "home_purchase"
    assert flag == 1
    assert "Business priority rule" in reason
