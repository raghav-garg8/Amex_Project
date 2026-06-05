# scoring/arbitration_engine.py
"""Arbitration Engine for LifeEventRadar.

Resolves conflicts when a customer triggers multiple life event scores above
thresholds, enforcing regulatory explainability and business priority order.
"""

from typing import Dict, Tuple, Optional
from scoring.scoring_config import THRESHOLDS, RECOMMENDED_PRODUCTS, BUSINESS_PRIORITY

def resolve_priority(
    scores: Dict[str, float],
    recency: Dict[str, str]
) -> Tuple[Optional[str], Optional[str], int, Optional[str]]:
    """Resolves which life event to recommend when multiple events exceed thresholds.

    Rules applied in order:
    1. Filter events exceeding their respective score threshold.
    2. If no event exceeds threshold, return None.
    3. If multiple exceed:
       a. Score Gap Rule: If top score is > 15 points higher than runner-up, top wins.
       b. Recency Rule: If gap is <= 15 points, the event with the most recent signal wins.
       c. Business Priority Rule: If still tied, use business priority ranking.

    Args:
        scores: Dict of life event name (str) to raw score (float).
        recency: Dict of life event name (str) to latest signal date 'YYYY-MM-DD' (str).

    Returns:
        A tuple of:
          - top_event: The selected winning event name, or None.
          - recommended_product: Card recommendation, or None.
          - conflict_flag: 1 if multiple events exceeded threshold, else 0.
          - arbitration_reason: Rationale description, or None.
    """
    # 1. Filter events exceeding their thresholds
    above_threshold = {
        event: score for event, score in scores.items()
        if score >= THRESHOLDS.get(event, 999.0)
    }

    if not above_threshold:
        return None, None, 0, None

    conflict_flag = 1 if len(above_threshold) > 1 else 0

    if len(above_threshold) == 1:
        top_event = list(above_threshold.keys())[0]
        rec_product = RECOMMENDED_PRODUCTS[top_event]
        reason = f"Only event '{top_event}' exceeded score threshold ({above_threshold[top_event]:.1f})."
        return top_event, rec_product, conflict_flag, reason

    # 2. Score Gap Rule
    sorted_events = sorted(above_threshold.items(), key=lambda x: x[1], reverse=True)
    top_event_candidate, top_score = sorted_events[0]
    second_event_candidate, second_score = sorted_events[1]

    if (top_score - second_score) > 15.0:
        rec_product = RECOMMENDED_PRODUCTS[top_event_candidate]
        reason = (
            f"Score gap rule: event '{top_event_candidate}' ({top_score:.1f}) "
            f"exceeded runner-up '{second_event_candidate}' ({second_score:.1f}) by > 15 points."
        )
        return top_event_candidate, rec_product, conflict_flag, reason

    # 3. Recency Rule (Checking events within 15 points of the top score)
    top_group = {
        event: score for event, score in above_threshold.items()
        if (top_score - score) <= 15.0
    }

    # Find the one with the most recent date (maximum string value in YYYY-MM-DD format)
    # Default to empty string for missing dates
    recent_dates = {event: recency.get(event, "") for event in top_group}
    sorted_by_recency = sorted(recent_dates.items(), key=lambda x: x[1], reverse=True)
    
    # Check if there is a single most recent date
    most_recent_event, most_recent_date = sorted_by_recency[0]
    
    if len(sorted_by_recency) > 1:
        second_recent_event, second_recent_date = sorted_by_recency[1]
        
        # If dates are different and the top one is non-empty
        if most_recent_date != second_recent_date and most_recent_date != "":
            rec_product = RECOMMENDED_PRODUCTS[most_recent_event]
            reason = (
                f"Recency rule: event '{most_recent_event}' has a more recent "
                f"signal ({most_recent_date}) than runner-up '{second_recent_event}' ({second_recent_date})."
            )
            return most_recent_event, rec_product, conflict_flag, reason

    # 4. Business Priority Rule
    # Iterate through priority list and select the first one present in the tied top group
    for priority_event in BUSINESS_PRIORITY:
        if priority_event in top_group:
            rec_product = RECOMMENDED_PRODUCTS[priority_event]
            reason = (
                f"Business priority rule: event '{priority_event}' chosen due to tie-breaking "
                f"priority hierarchy (scores within 15 points: "
                f"{', '.join([f'{k}:{v:.1f}' for k, v in top_group.items()])})."
            )
            return priority_event, rec_product, conflict_flag, reason

    # Fallback (should not be reached if BUSINESS_PRIORITY is exhaustive)
    fallback_event = top_event_candidate
    return fallback_event, RECOMMENDED_PRODUCTS[fallback_event], conflict_flag, "Fallback default selection."
