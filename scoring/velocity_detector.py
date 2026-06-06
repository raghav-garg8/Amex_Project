"""velocity_detector.py
FinSight — Customer Behavioral Intelligence Platform

Spend Velocity Anomaly Detection Engine.

Detects abnormal changes in a customer's spending behavior by
comparing their current 30-day spend to their personal 6-month
baseline — using Z-score normalisation.
"""

import sys
import os
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import date
import mysql.connector

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from scoring_config import DB_CONFIG


def load_customer_spend_history(conn: mysql.connector.MySQLConnection) -> pd.DataFrame:
    """Load monthly spend per customer for the past 7 months from MySQL.

    7 months = 1 month current + 6 months baseline.

    Args:
        conn: MySQL connection object.

    Returns:
        DataFrame containing columns: customer_id, month_start, monthly_spend, txn_count.
    """
    query = """
        SELECT
            customer_id,
            DATE_FORMAT(txn_date, '%Y-%m-01') AS month_start,
            SUM(amount) AS monthly_spend,
            COUNT(*) AS txn_count
        FROM transactions
        WHERE status = 'completed'
        AND amount > 0
        AND txn_date >= DATE_SUB(CURDATE(), INTERVAL 7 MONTH)
        GROUP BY customer_id, DATE_FORMAT(txn_date, '%Y-%m-01')
        ORDER BY customer_id, month_start
    """
    return pd.read_sql(query, conn)


def _compute_single_velocity(customer_id: int, group: pd.DataFrame) -> Dict[str, Any]:
    """Computes spend velocity Z-score and label for a single customer.

    Args:
        customer_id: Unique customer ID.
        group: DataFrame group containing sorted spend history for the customer.

    Returns:
        A dictionary of calculated velocity metrics.
    """
    if len(group) < 3:
        # Insufficient history — cannot compute meaningful baseline
        return {
            'customer_id': customer_id,
            'current_spend': group['monthly_spend'].iloc[-1],
            'baseline_mean': None,
            'baseline_std': None,
            'velocity_score': 0.0,
            'velocity_label': 'Insufficient History',
            'months_of_data': len(group)
        }

    # Split: last month = current, rest = baseline
    current = group.iloc[-1]['monthly_spend']
    baseline = group.iloc[:-1]['monthly_spend']

    baseline_mean = baseline.mean()
    baseline_std = baseline.std()

    # Handle zero std (customer spends same amount every month)
    if baseline_std == 0 or pd.isna(baseline_std):
        velocity_score = 0.0
    else:
        velocity_score = (current - baseline_mean) / baseline_std

    # Label the velocity
    if velocity_score > 2.0:
        label = 'Strong Positive Anomaly'
    elif velocity_score > 1.0:
        label = 'Moderate Increase'
    elif velocity_score >= -1.0:
        label = 'Normal'
    elif velocity_score >= -2.0:
        label = 'Declining'
    else:
        label = 'Strong Negative Anomaly'

    return {
        'customer_id': customer_id,
        'current_spend': round(current, 2),
        'baseline_mean': round(baseline_mean, 2),
        'baseline_std': round(baseline_std, 2) if not pd.isna(baseline_std) else None,
        'velocity_score': round(velocity_score, 4),
        'velocity_label': label,
        'months_of_data': len(group)
    }


def compute_velocity_scores(spend_history: pd.DataFrame) -> pd.DataFrame:
    """Compute spend velocity Z-score for each customer.

    Process:
    1. Current period = most recent month in data
    2. Baseline = all months EXCEPT the most recent
    3. Z-score = (current - baseline_mean) / baseline_std
    4. Handle customers with < 3 months of history (insufficient baseline)

    Args:
        spend_history: DataFrame with columns: customer_id, month_start, monthly_spend.

    Returns:
        DataFrame with columns: customer_id, current_spend, baseline_mean, baseline_std,
        velocity_score, velocity_label, months_of_data.
    """
    spend_history['month_start'] = pd.to_datetime(
        spend_history['month_start']
    )

    results = []
    for customer_id, group in spend_history.groupby('customer_id'):
        sorted_group = group.sort_values('month_start')
        results.append(_compute_single_velocity(customer_id, sorted_group))

    return pd.DataFrame(results)


def compute_velocity_weight(velocity_score: Optional[float]) -> float:
    """Convert velocity score to a multiplier for the Priority Index.

    Positive anomaly → multiplier > 1 (boosts priority)
    Normal → multiplier = 1 (neutral)
    Negative anomaly → multiplier < 1 (reduces priority)

    Capped at [0.5, 1.5] to prevent extreme values from
    overwhelming the other scoring components.

    Args:
        velocity_score: Spend velocity Z-score.

    Returns:
        Weight multiplier float in range [0.5, 1.5].
    """
    if velocity_score is None or pd.isna(velocity_score):
        return 1.0

    # Sigmoid-inspired scaling: smooth, bounded
    raw_multiplier = 1.0 + (velocity_score * 0.15)
    return round(max(0.5, min(1.5, raw_multiplier)), 3)


def write_velocity_to_db(velocity_df: pd.DataFrame, conn: mysql.connector.MySQLConnection) -> None:
    """Write velocity scores to customer_velocity table in MySQL database.

    Args:
        velocity_df: DataFrame of computed velocity results.
        conn: MySQL connection object.
    """
    cursor = conn.cursor()
    today = date.today()

    upsert_query = """
        INSERT INTO customer_velocity
            (customer_id, score_date, current_spend, baseline_mean,
             baseline_std, velocity_score, velocity_label,
             velocity_weight, months_of_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            current_spend = VALUES(current_spend),
            baseline_mean = VALUES(baseline_mean),
            baseline_std = VALUES(baseline_std),
            velocity_score = VALUES(velocity_score),
            velocity_label = VALUES(velocity_label),
            velocity_weight = VALUES(velocity_weight),
            months_of_data = VALUES(months_of_data)
    """

    rows = [
        (
            row['customer_id'], today,
            row['current_spend'], row['baseline_mean'],
            row['baseline_std'], row['velocity_score'],
            row['velocity_label'],
            compute_velocity_weight(row['velocity_score']),
            row['months_of_data']
        )
        for _, row in velocity_df.iterrows()
    ]

    cursor.executemany(upsert_query, rows)
    conn.commit()
    cursor.close()
    print(f"[VELOCITY] Written {len(rows)} velocity records.")


def run_velocity_detector() -> pd.DataFrame:
    """Main entry point for the velocity detection engine.

    Returns:
        DataFrame containing computed velocity scores.
    """
    conn = mysql.connector.connect(**DB_CONFIG)

    try:
        print("[VELOCITY] Loading spend history...")
        spend_history = load_customer_spend_history(conn)

        print("[VELOCITY] Computing velocity scores...")
        velocity_df = compute_velocity_scores(spend_history)

        print("[VELOCITY] Velocity distribution:")
        print(velocity_df['velocity_label'].value_counts().to_string())

        write_velocity_to_db(velocity_df, conn)
        return velocity_df

    finally:
        conn.close()


if __name__ == "__main__":
    run_velocity_detector()
