# pipeline/feedback_loop.py
"""Feedback Loop and A/B Test Simulator for LifeEventRadar.

Simulates customer campaign conversions, tracks back-test precision/recall,
measures A/B test conversion uplifts, and quantifies estimated business impact.
"""

import os
import sys
import random
from datetime import datetime, timedelta
import mysql.connector

# Central connection configurations
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "amex_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "amex_password")
DB_NAME = os.getenv("DB_NAME", "life_event_radar_db")

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
    """Connects to the target database."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def run_feedback_loop() -> None:
    """Simulates conversion outcomes and evaluates scoring performance."""
    print("Initializing outcome simulation and feedback loop...")
    random.seed(42)  # Deterministic outcome simulation
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        sys.exit(1)

    # 1. Fetch scores above threshold (exceeded top_event)
    cursor.execute("""
        SELECT * FROM customer_scores 
        WHERE score_date = %s AND top_event IS NOT NULL;
    """, (CURDATE_STR,))
    scored_customers = cursor.fetchall()
    
    if not scored_customers:
        print("No scored customers with active recommendations found for this date. Run combined_scorer.py first.")
        cursor.close()
        conn.close()
        return

    # Clear previous conversion records for this score batch to ensure clean run
    del_cursor = conn.cursor()
    del_cursor.execute("DELETE FROM offer_conversions WHERE score_date = %s;", (CURDATE_STR,))
    conn.commit()
    del_cursor.close()

    conversion_records = []
    
    # 2. Partition scored customers into A/B groups
    # Group A (Treatment): ~80% of flagged customers receive targeted offer.
    # Group B (Control): ~20% receive generic offer.
    for row in scored_customers:
        cid = row["customer_id"]
        event = row["top_event"]
        prod = row["recommended_product"]
        opp_score = float(row["opportunity_score"])
        
        # Decide group assignment
        group_type = "treatment" if random.random() < 0.80 else "control"
        
        # Set offer sent time (shortly after scoring)
        offer_sent = datetime.strptime(CURDATE_STR, "%Y-%m-%d") + timedelta(hours=random.randint(8, 24))
        
        # Base conversion probability scaled by opportunity score
        # Higher score = higher conviction spend intent
        base_prob = opp_score / 100.0
        
        if group_type == "treatment":
            # Targeted campaign is highly relevant
            conv_prob = min(base_prob * 0.85, 0.90)
        else:
            # Control group receives generic offer with lower conversion chance
            conv_prob = max(base_prob * 0.25, 0.10)
            
        # Determine conversion outcome
        converted = 1 if random.random() < conv_prob else 0
        
        converted_at = None
        conv_days = None
        if converted == 1:
            conv_days = random.randint(3, 45)
            converted_at = offer_sent + timedelta(days=conv_days)
            
        conversion_records.append((
            cid,
            CURDATE_STR,
            event,
            prod,
            offer_sent.strftime("%Y-%m-%d %H:%M:%S"),
            converted,
            converted_at.strftime("%Y-%m-%d %H:%M:%S") if converted_at else None,
            conv_days,
            group_type
        ))

    # 3. Batch insert conversion records
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
    for i in range(0, len(conversion_records), batch_size):
        batch = conversion_records[i:i+batch_size]
        ins_cursor.executemany(insert_query, batch)
    conn.commit()
    ins_cursor.close()

    # 4. Query statistics to perform back-test evaluation and A/B verification
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
    
    # Aggregate stats for reporting
    grouped_stats = {}
    for r in stats:
        g = r["group_type"]
        e = r["top_event"]
        grouped_stats.setdefault(g, {})[e] = {
            "offers": r["total_offers"],
            "conversions": r["total_conversions"]
        }

    print("\n" + "="*50)
    print("           CAMPAIGN FEEDBACK & VALIDATION REPORT")
    print("="*50)
    print(f"Scoring Date Batch: {CURDATE_STR}")
    print(f"Total Scored Alerts: {len(scored_customers)}")
    print("-"*50)
    
    total_revenue_opportunity = 0.0
    
    # Back-test analysis per event type
    print("1. Target Precision Metrics (Treatment Group)")
    print(f"{'Life Event':<20} | {'Offers':<8} | {'Conversions':<12} | {'Precision':<10}")
    print("-"*58)
    
    treat_data = grouped_stats.get("treatment", {})
    for event, metrics in treat_data.items():
        offers = metrics["offers"]
        convs = metrics["conversions"]
        precision = (convs / offers) if offers > 0 else 0.0
        
        # Calculate revenue impact
        inc_spend = SPEND_INCREMENTS.get(event, 0.0)
        revenue_val = convs * inc_spend
        total_revenue_opportunity += revenue_val
        
        print(f"{event:<20} | {offers:<8} | {convs:<12} | {precision:.2%}")

    # A/B group metrics
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
    
    # Calculate portfolio projection (projected to full 100% targeting)
    projected_spend = total_revenue_opportunity / 0.80 if len(scored_customers) > 0 else 0.0
    print(f"Projected Annual Portfolio Spend:   ₹{projected_spend:,.2f}")
    print("="*50)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_feedback_loop()
