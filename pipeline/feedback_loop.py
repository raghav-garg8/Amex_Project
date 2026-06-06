# pipeline/feedback_loop.py
"""Feedback Loop and A/B Test Simulator for FinSight.

Simulates customer campaign conversions, tracks back-test precision/recall,
measures A/B test conversion uplifts, and quantifies estimated business impact.
"""

import os
import sys
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import mysql.connector

# Resolve cross-module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scoring")))
from scoring_config import DB_CONFIG

# Read connection configurations from DB_CONFIG
DB_HOST = DB_CONFIG["host"]
DB_PORT = DB_CONFIG["port"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]
DB_NAME = DB_CONFIG["database"]

# Fixed batch score date
CURDATE_STR = "2026-06-05"

# Business opportunity spend estimates (from PROJECT.md)
SPEND_INCREMENTS = {
    "home_purchase": 45000.0,
    "relocation": 35000.0,
    "marriage": 35000.0,
    "new_child": 25000.0,
    "higher_education": 20000.0
}


def get_connection() -> mysql.connector.MySQLConnection:
    """Connects to the target database.

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


def _simulate_ab_conversions(scored_customers: List[Dict[str, Any]]) -> List[Tuple]:
    """Partitions scored customers into A/B groups and simulates conversion outcomes.

    Args:
        scored_customers: List of customer score records.

    Returns:
        List of conversion tuples.
    """
    conversion_records = []
    for row in scored_customers:
        cid = row["customer_id"]
        event = row["top_event"]
        prod = row["recommended_product"]
        opp_score = float(row["opportunity_score"])
        
        group_type = "treatment" if random.random() < 0.80 else "control"
        offer_sent = datetime.strptime(CURDATE_STR, "%Y-%m-%d") + timedelta(hours=random.randint(8, 24))
        
        base_prob = opp_score / 100.0
        if group_type == "treatment":
            conv_prob = min(base_prob * 0.85, 0.90)
        else:
            conv_prob = max(base_prob * 0.25, 0.10)
            
        converted = 1 if random.random() < conv_prob else 0
        converted_at = None
        conv_days = None
        
        if converted == 1:
            conv_days = random.randint(3, 45)
            converted_at = offer_sent + timedelta(days=conv_days)
            
        conversion_records.append((
            cid, CURDATE_STR, event, prod,
            offer_sent.strftime("%Y-%m-%d %H:%M:%S"),
            converted,
            converted_at.strftime("%Y-%m-%d %H:%M:%S") if converted_at else None,
            conv_days, group_type
        ))
    return conversion_records


def _ingest_conversions_to_db(conn: mysql.connector.MySQLConnection, records: List[Tuple]) -> None:
    """Batch inserts simulated conversion outcomes into the offer_conversions table.

    Args:
        conn: MySQL connection.
        records: List of conversion tuples.
    """
    print("Loading conversion outcomes into offer_conversions...")
    insert_query = """
        INSERT INTO offer_conversions (
            customer_id, score_date, top_event, recommended_product, offer_sent_at,
            converted, converted_at, conversion_window_days, group_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    ins_cursor = conn.cursor()
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        ins_cursor.executemany(insert_query, batch)
    conn.commit()
    ins_cursor.close()


def _query_conversion_statistics(conn: mysql.connector.MySQLConnection) -> Dict[str, Dict[str, Dict[str, int]]]:
    """Retrieves conversion stats grouped by treatment group and event type.

    Args:
        conn: MySQL connection.

    Returns:
        Nested dict of group -> event -> {'offers': int, 'conversions': int}.
    """
    cursor = conn.cursor(dictionary=True)
    stats_query = """
        SELECT
            group_type,
            top_event,
            COUNT(*) AS total_offers,
            SUM(converted) AS total_conversions
        FROM offer_conversions
        WHERE score_date = %s
        GROUP BY group_type, top_event;
    """
    cursor.execute(stats_query, (CURDATE_STR,))
    stats = cursor.fetchall()
    cursor.close()
    
    grouped_stats: Dict[str, Dict[str, Dict[str, int]]] = {}
    for r in stats:
        g = r["group_type"]
        e = r["top_event"]
        grouped_stats.setdefault(g, {})[e] = {
            "offers": int(r["total_offers"] or 0),
            "conversions": int(r["total_conversions"] or 0)
        }
    return grouped_stats


def _print_performance_report(
    scored_customers_count: int,
    grouped_stats: Dict[str, Dict[str, Dict[str, int]]]
) -> None:
    """Formats and prints the back-test and A/B campaign validation report.

    Args:
        scored_customers_count: Total scored customers.
        grouped_stats: Nested statistics dictionary.
    """
    print("\n" + "="*50)
    print("           CAMPAIGN FEEDBACK & VALIDATION REPORT")
    print("="*50)
    print(f"Scoring Date Batch: {CURDATE_STR}")
    print(f"Total Scored Alerts: {scored_customers_count}")
    print("-"*50)
    
    total_revenue_opportunity = 0.0
    print("1. Target Precision Metrics (Treatment Group)")
    print(f"{'Life Event':<20} | {'Offers':<8} | {'Conversions':<12} | {'Precision':<10}")
    print("-"*58)
    
    treat_data = grouped_stats.get("treatment", {})
    for event, metrics in treat_data.items():
        offers = metrics["offers"]
        convs = metrics["conversions"]
        precision = (convs / offers) if offers > 0 else 0.0
        
        inc_spend = SPEND_INCREMENTS.get(event, 0.0)
        total_revenue_opportunity += convs * inc_spend
        print(f"{event:<20} | {offers:<8} | {convs:<12} | {precision:.2%}")

    print("\n2. A/B Simulation Metrics")
    t_offers = sum(x["offers"] for x in treat_data.values())
    t_convs = sum(x["conversions"] for x in treat_data.values())
    t_rate = (t_convs / t_offers) if t_offers > 0 else 0.0
    
    ctrl_data = grouped_stats.get("control", {})
    c_offers = sum(x["offers"] for x in ctrl_data.values())
    c_convs = sum(x["conversions"] for x in ctrl_data.values())
    c_rate = (c_convs / c_offers) if c_offers > 0 else 0.0
    
    uplift = (t_rate - c_rate) / c_rate if c_rate > 0 else 0.0
    
    print(f"Treatment (Group A) Conversion Rate: {t_rate:.2%} ({t_convs}/{t_offers} offers)")
    print(f"Control   (Group B) Conversion Rate: {c_rate:.2%} ({c_convs}/{c_offers} offers)")
    print(f"Targeted Campaign Conversion Uplift: {uplift:+.2%}")

    print("\n3. Estimated Incremental Spend Opportunity")
    print(f"Total Simulated Incremental Spend:  ₹{total_revenue_opportunity:,.2f}")
    
    projected_spend = total_revenue_opportunity / 0.80 if scored_customers_count > 0 else 0.0
    print(f"Projected Annual Portfolio Spend:   ₹{projected_spend:,.2f}")
    print("="*50)


def run_feedback_loop() -> None:
    """Simulates conversion outcomes and evaluates scoring performance."""
    print("Initializing outcome simulation and feedback loop...")
    random.seed(42)
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        sys.exit(1)

    try:
        cursor.execute("""
            SELECT * FROM customer_scores 
            WHERE score_date = %s AND top_event IS NOT NULL;
        """, (CURDATE_STR,))
        scored_customers = cursor.fetchall()
        
        if not scored_customers:
            print("No scored customers with active recommendations found for this date. Run combined_scorer.py first.")
            return

        # Clear previous conversion records
        del_cursor = conn.cursor()
        del_cursor.execute("DELETE FROM offer_conversions WHERE score_date = %s;", (CURDATE_STR,))
        conn.commit()
        del_cursor.close()

        conversion_records = _simulate_ab_conversions(scored_customers)
        _ingest_conversions_to_db(conn, conversion_records)
        
        grouped_stats = _query_conversion_statistics(conn)
        _print_performance_report(len(scored_customers), grouped_stats)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_feedback_loop()
