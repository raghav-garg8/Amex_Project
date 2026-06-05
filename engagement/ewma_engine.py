# engagement/ewma_engine.py
"""EWMA Engagement Calculation Engine for LifeEventRadar.

Applies Exponentially Weighted Moving Average (EWMA) to sequential digital
engagement logs to determine recency-biased interest multipliers per customer.
"""

from typing import Dict, Tuple
import mysql.connector

# Temporal decay smoothing parameter (α = 0.5)
ALPHA = 0.5

def calculate_ewma_scores(
    conn: mysql.connector.MySQLConnection
) -> Dict[int, Dict[str, float]]:
    """Calculates recency-weighted engagement multipliers for all customers.

    Querying chronological click and open logs from campaign_clicks and email_opens.
    Applies the sequential smoothing formula: S_t = α * x_t + (1 - α) * S_{t-1}.
    Maps raw EWMA scores to multipliers bound between 0.5 and 2.0.

    Args:
        conn: Live MySQL connection object.

    Returns:
        Dict mapping customer_id (int) to a sub-dict of offer_category (str)
        to the final scaled engagement multiplier (float).
    """
    cursor = conn.cursor()
    
    # Query click/open streams chronologically (from engagement_analytics.sql Query 1)
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

    # customer_id -> category -> raw_score
    raw_scores: Dict[int, Dict[str, float]] = {}

    for customer_id, category, value in rows:
        cust_scores = raw_scores.setdefault(customer_id, {})
        prev_score = cust_scores.get(category, 0.0)
        
        # Apply EWMA temporal decay formula
        new_score = (ALPHA * float(value)) + ((1.0 - ALPHA) * prev_score)
        cust_scores[category] = new_score

    # Convert raw EWMA scores into multipliers bound between 0.5 and 2.0
    # Formula: multiplier = 0.5 + raw_score, clamped to [0.5, 2.0]
    multipliers: Dict[int, Dict[str, float]] = {}
    categories = ["home", "travel", "lifestyle", "rewards", "education"]

    for cid, cats in raw_scores.items():
        multipliers[cid] = {}
        for category in categories:
            raw_s = cats.get(category, 0.0)
            # 0.5 is baseline penalization for zero engagement
            scaled_m = min(max(0.5 + raw_s, 0.5), 2.0)
            multipliers[cid][category] = round(scaled_m, 3)

    return multipliers
