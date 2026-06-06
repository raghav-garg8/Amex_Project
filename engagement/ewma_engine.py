# engagement/ewma_engine.py
"""EWMA Engagement Calculation Engine for FinSight.

Applies Exponentially Weighted Moving Average (EWMA) to sequential digital
engagement logs to determine recency-biased interest multipliers per customer.
"""

from typing import Dict, Tuple, List
import mysql.connector

# Temporal decay smoothing parameter (α = 0.5)
ALPHA = 0.5
CATEGORIES = ["home", "travel", "lifestyle", "rewards", "education"]


def _fetch_raw_engagement_values(
    conn: mysql.connector.MySQLConnection
) -> List[Tuple[int, str, int]]:
    """Retrieves chronological click and open events from MySQL.

    Clicks are valued at 2; opens at 1.

    Args:
        conn: Live MySQL connection.

    Returns:
        List of tuples containing customer_id, offer_category, and event_value.
    """
    cursor = conn.cursor()
    query = """
        SELECT
            customer_id,
            offer_category,
            event_value
        FROM (
            SELECT
                customer_id,
                offer_category,
                clicked_at AS event_time,
                2 AS event_value
            FROM campaign_clicks
            UNION ALL
            SELECT
                customer_id,
                offer_category,
                opened_at AS event_time,
                1 AS event_value
            FROM email_opens
        ) AS combined_events
        ORDER BY customer_id ASC, event_time ASC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return [(r[0], r[1], int(r[2])) for r in rows]


def _compute_ewma_scores(
    rows: List[Tuple[int, str, int]]
) -> Dict[int, Dict[str, float]]:
    """Applies the sequential EWMA temporal decay formula on engagement streams.

    Formula: S_t = α * x_t + (1 - α) * S_{t-1}

    Args:
        rows: Chronological click and open records list.

    Returns:
        Dict mapping customer_id to raw category engagement scores.
    """
    raw_scores: Dict[int, Dict[str, float]] = {}
    for customer_id, category, value in rows:
        cust_scores = raw_scores.setdefault(customer_id, {})
        prev_score = cust_scores.get(category, 0.0)
        
        # Apply EWMA temporal decay formula
        new_score = (ALPHA * float(value)) + ((1.0 - ALPHA) * prev_score)
        cust_scores[category] = new_score
    return raw_scores


def _scale_to_multipliers(
    raw_scores: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, float]]:
    """Converts raw EWMA scores into multipliers bound between 0.5 and 2.0.

    Formula: multiplier = 0.5 + raw_score, clamped to [0.5, 2.0]

    Args:
        raw_scores: Raw EWMA scores dict.

    Returns:
        Dict mapping customer_id to category multipliers.
    """
    multipliers: Dict[int, Dict[str, float]] = {}
    for cid, cats in raw_scores.items():
        multipliers[cid] = {}
        for category in CATEGORIES:
            raw_s = cats.get(category, 0.0)
            # 0.5 is baseline penalization for zero engagement
            scaled_m = min(max(0.5 + raw_s, 0.5), 2.0)
            multipliers[cid][category] = round(scaled_m, 3)
    return multipliers


def calculate_ewma_scores(
    conn: mysql.connector.MySQLConnection
) -> Dict[int, Dict[str, float]]:
    """Calculates recency-weighted engagement multipliers for all customers.

    Args:
        conn: Live MySQL connection object.

    Returns:
        Dict mapping customer_id (int) to a sub-dict of offer_category (str)
        to the final scaled engagement multiplier (float).
    """
    rows = _fetch_raw_engagement_values(conn)
    raw_scores = _compute_ewma_scores(rows)
    return _scale_to_multipliers(raw_scores)
