# engagement/combined_scorer.py
"""Combined Scorer & Fusion Pipeline Coordinator for LifeEventRadar.

Orchestrates the transactional scoring rules, arbitration, engagement EWMA,
and channel diversity logic, executing the full pipeline and writing outputs to MySQL.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, Tuple
import mysql.connector

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

# Connection parameters
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "amex_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "amex_password")
DB_NAME = os.getenv("DB_NAME", "life_event_radar_db")

# Fixed Execution Date
CURDATE_STR = "2026-06-05"

def get_connection() -> mysql.connector.MySQLConnection:
    """Connects to the MySQL database."""
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
        # Format date object to string YYYY-MM-DD
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

def run_pipeline() -> None:
    """Executes the scoring pipeline for all customers and saves outcomes."""
    print("Initializing scoring & engagement fusion pipeline...")
    try:
        conn = get_connection()
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        sys.exit(1)

    # 1. Fetch features and engagement stats
    print("Loading pre-aggregated customer features...")
    customer_features = fetch_features(conn)
    print("Loading transaction recency logs...")
    recency_data = fetch_transaction_recency(conn)
    print("Loading digital engagement multipliers...")
    ewma_multipliers = calculate_ewma_scores(conn)
    print("Loading channel diversity counts...")
    channel_diversity = fetch_channel_diversity(conn)

    # 2. Reset score tables
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM customer_scores WHERE score_date = '{CURDATE_STR}';")
    conn.commit()

    score_records = []
    # Map from life event tag to campaign categories
    campaign_category_map = {
        "home_purchase": "home",
        "relocation": "travel",
        "marriage": "lifestyle",
        "new_child": "rewards",
        "higher_education": "education"
    }

    # 3. Process each customer
    for feat in customer_features:
        cid = feat["customer_id"]
        
        # Calculate base scores
        scores = {
            "home_purchase": compute_home_score(feat),
            "relocation": compute_relocation_score(feat),
            "marriage": compute_marriage_score(feat),
            "new_child": compute_child_score(feat),
            "higher_education": compute_edu_score(feat)
        }
        
        # Resolve priority conflicts
        cust_recency = recency_data.get(cid, {})
        top_event, rec_product, conflict_flag, reason = resolve_priority(scores, cust_recency)
        
        # Initalize multipliers
        engagement_mult = 1.000
        channel_mult = 1.000
        opportunity_score = 0.0
        
        if top_event:
            # Fetch matching campaign category multiplier
            campaign_cat = campaign_category_map[top_event]
            engagement_mult = ewma_multipliers.get(cid, {}).get(campaign_cat, 0.5)
            
            # Fetch channel diversity multiplier
            channels = channel_diversity.get(cid, 0)
            channel_mult = 1.0 + (min(channels, 3) * 0.15)
            
            # Fused Opportunity Score
            base_score = scores[top_event]
            opportunity_score = min(base_score * engagement_mult * channel_mult, 100.0)
            
        score_records.append((
            cid,
            CURDATE_STR,
            scores["home_purchase"],
            scores["relocation"],
            scores["marriage"],
            scores["new_child"],
            scores["higher_education"],
            top_event,
            round(engagement_mult, 3),
            round(channel_mult, 3),
            round(opportunity_score, 1),
            rec_product,
            conflict_flag,
            reason
        ))

    # 4. Ingest scores in batch
    print(f"Ingesting final scores into customer_scores...")
    insert_query = """
        INSERT INTO customer_scores (
            customer_id, score_date, home_score, relocation_score, marriage_score, child_score, edu_score,
            top_event, engagement_multiplier, channel_multiplier, opportunity_score, recommended_product,
            conflict_flag, arbitration_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    # Batch load
    batch_size = 1000
    for i in range(0, len(score_records), batch_size):
        batch = score_records[i:i+batch_size]
        cursor.executemany(insert_query, batch)
        
    conn.commit()
    print(f"Scoring pipeline complete. Successfully scored {len(score_records)} customers.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_pipeline()
