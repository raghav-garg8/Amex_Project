# engagement/combined_scorer.py
"""Combined Scorer & Fusion Pipeline Coordinator for FinSight.

Orchestrates the transactional scoring rules, arbitration, engagement EWMA,
and channel diversity logic, executing the full pipeline and writing outputs to MySQL.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, Tuple, List
import mysql.connector

# Resolve cross-module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scoring")))

# Scoring imports
from scoring.life_event_scorer import (
    compute_home_score,
    compute_relocation_score,
    compute_marriage_score,
    compute_child_score,
    compute_edu_score
)
from scoring.arbitration_engine import resolve_priority
from engagement.ewma_engine import calculate_ewma_scores
from scoring_config import DB_CONFIG

# Read connection configurations from DB_CONFIG
DB_HOST = DB_CONFIG["host"]
DB_PORT = DB_CONFIG["port"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]
DB_NAME = DB_CONFIG["database"]

# Fixed Execution Date
CURDATE_STR = "2026-06-05"

# Map from life event tag to campaign categories
CAMPAIGN_CATEGORY_MAP: Dict[str, str] = {
    "home_purchase": "home",
    "relocation": "travel",
    "marriage": "lifestyle",
    "new_child": "rewards",
    "higher_education": "education"
}


def get_connection() -> mysql.connector.MySQLConnection:
    """Connects to the MySQL database.

    Returns:
        MySQL connection object.
    """
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def fetch_features(conn: mysql.connector.MySQLConnection) -> List[Dict[str, Any]]:
    """Retrieves all aggregated customer feature records.

    Args:
        conn: MySQL connection.

    Returns:
        List of feature dictionaries.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer_features;")
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_transaction_recency(conn: mysql.connector.MySQLConnection) -> Dict[int, Dict[str, str]]:
    """Queries the date of the latest transaction for each customer and event tag.

    Used by the arbitration engine for tie-breaking.

    Args:
        conn: MySQL connection.

    Returns:
        Dict mapping customer_id (int) to a sub-dict of event_tag (str) to latest date string (str).
    """
    cursor = conn.cursor()
    query = """
        SELECT
            t.customer_id,
            mc.life_event_tag,
            MAX(t.txn_date) AS latest_date
        FROM transactions t
        INNER JOIN merchants m ON t.merchant_id = m.merchant_id
        INNER JOIN merchant_categories mc ON m.category_id = mc.category_id
        WHERE t.status = 'completed'
        GROUP BY t.customer_id, mc.life_event_tag;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    recency_map: Dict[int, Dict[str, str]] = {}
    for cid, tag, date_val in rows:
        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)
        recency_map.setdefault(cid, {})[tag] = date_str
        
    return recency_map


def fetch_channel_diversity(conn: mysql.connector.MySQLConnection) -> Dict[int, int]:
    """Queries the number of distinct channels used in the last 30 days.

    Args:
        conn: MySQL connection.

    Returns:
        Dict mapping customer_id (int) to channel count (int).
    """
    cursor = conn.cursor()
    query = """
        SELECT
            customer_id,
            COUNT(DISTINCT channel) AS distinct_channels_30d
        FROM (
            SELECT customer_id, channel, clicked_at AS event_time FROM campaign_clicks WHERE clicked_at >= DATE_SUB('2026-06-05', INTERVAL 30 DAY)
            UNION ALL
            SELECT customer_id, 'email' AS channel, opened_at AS event_time FROM email_opens WHERE opened_at >= DATE_SUB('2026-06-05', INTERVAL 30 DAY)
        ) AS combined_engagement
        GROUP BY customer_id;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return {cid: count for cid, count in rows}


def _reset_customer_scores(conn: mysql.connector.MySQLConnection) -> None:
    """Deletes existing scores for the current execution date.

    Args:
        conn: MySQL connection.
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM customer_scores WHERE score_date = '{CURDATE_STR}';")
    conn.commit()
    cursor.close()


def _calculate_opportunity_score_records(
    customer_features: List[Dict[str, Any]],
    recency_data: Dict[int, Dict[str, str]],
    ewma_multipliers: Dict[int, Dict[str, float]],
    channel_diversity: Dict[int, int]
) -> List[Tuple]:
    """Computes base scoring and fusions to build opportunity score insert tuples.

    Args:
        customer_features: List of customer features from DB.
        recency_data: Transaction recency maps.
        ewma_multipliers: EWMA recency-biased categories multipliers.
        channel_diversity: Number of distinct active channels per customer.

    Returns:
        List of database row insert tuples.
    """
    score_records = []
    for feat in customer_features:
        cid = feat["customer_id"]
        
        scores = {
            "home_purchase": compute_home_score(feat),
            "relocation": compute_relocation_score(feat),
            "marriage": compute_marriage_score(feat),
            "new_child": compute_child_score(feat),
            "higher_education": compute_edu_score(feat)
        }
        
        cust_recency = recency_data.get(cid, {})
        top_event, rec_product, conflict_flag, reason = resolve_priority(scores, cust_recency)
        
        engagement_mult = 1.000
        channel_mult = 1.000
        opportunity_score = 0.0
        
        if top_event:
            campaign_cat = CAMPAIGN_CATEGORY_MAP[top_event]
            engagement_mult = ewma_multipliers.get(cid, {}).get(campaign_cat, 0.5)
            
            channels = channel_diversity.get(cid, 0)
            channel_mult = 1.0 + (min(channels, 3) * 0.15)
            
            base_score = scores[top_event]
            opportunity_score = min(base_score * engagement_mult * channel_mult, 100.0)
            
        score_records.append((
            cid, CURDATE_STR,
            scores["home_purchase"], scores["relocation"], scores["marriage"],
            scores["new_child"], scores["higher_education"],
            top_event, round(engagement_mult, 3), round(channel_mult, 3),
            round(opportunity_score, 1), rec_product, conflict_flag, reason
        ))
    return score_records


def _write_scores_to_db(score_records: List[Tuple], conn: mysql.connector.MySQLConnection) -> None:
    """Inserts computed scores into the database in batches.

    Args:
        score_records: List of tuples to insert.
        conn: MySQL connection object.
    """
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO customer_scores (
            customer_id, score_date, home_score, relocation_score, marriage_score, child_score, edu_score,
            top_event, engagement_multiplier, channel_multiplier, opportunity_score, recommended_product,
            conflict_flag, arbitration_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    batch_size = 1000
    for i in range(0, len(score_records), batch_size):
        batch = score_records[i:i+batch_size]
        cursor.executemany(insert_query, batch)
        
    conn.commit()
    cursor.close()
    print(f"Scoring pipeline complete. Successfully scored {len(score_records)} customers.")


def run_pipeline() -> None:
    """Executes the scoring pipeline for all customers and saves outcomes."""
    print("Initializing scoring & engagement fusion pipeline...")
    try:
        conn = get_connection()
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        sys.exit(1)

    try:
        print("Loading pre-aggregated customer features...")
        customer_features = fetch_features(conn)
        print("Loading transaction recency logs...")
        recency_data = fetch_transaction_recency(conn)
        print("Loading digital engagement multipliers...")
        ewma_multipliers = calculate_ewma_scores(conn)
        print("Loading channel diversity counts...")
        channel_diversity = fetch_channel_diversity(conn)

        print("Resetting current score partition...")
        _reset_customer_scores(conn)

        print("Calculating opportunity scores...")
        score_records = _calculate_opportunity_score_records(
            customer_features, recency_data, ewma_multipliers, channel_diversity
        )

        print("Ingesting final scores into customer_scores...")
        _write_scores_to_db(score_records, conn)

    finally:
        conn.close()


if __name__ == "__main__":
    run_pipeline()
