"""rfm_engine.py
FinSight — Customer Behavioral Intelligence Platform

RFM (Recency, Frequency, Monetary) Customer Value Scoring Engine.

Computes R, F, M scores (1-5 each) for every customer based on
their transaction history, assigns them to one of 8 named segments,
and writes results to the customer_rfm table in MySQL.
"""

import sys
import os
from datetime import date
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import mysql.connector

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from scoring_config import DB_CONFIG, RFM_SEGMENT_MAP


def load_transactions(conn: mysql.connector.MySQLConnection) -> pd.DataFrame:
    """Load completed transactions from MySQL database.

    Args:
        conn: MySQL connection object.

    Returns:
        DataFrame containing customer_id, txn_date, and amount.
    """
    query = """
        SELECT
            customer_id,
            txn_date,
            amount
        FROM transactions
        WHERE status = 'completed'
        AND amount > 0
        ORDER BY customer_id, txn_date
    """
    return pd.read_sql(query, conn)


def compute_rfm_raw(
    df: pd.DataFrame,
    snapshot_date: Optional[date] = None
) -> pd.DataFrame:
    """Compute raw Recency, Frequency, and Monetary values per customer.

    Args:
        df: transactions DataFrame with customer_id, txn_date, amount.
        snapshot_date: reference date for recency (default: today).

    Returns:
        DataFrame containing customer_id, recency_days, frequency, and monetary.
    """
    if snapshot_date is None:
        snapshot_date = pd.Timestamp.today()

    df['txn_date'] = pd.to_datetime(df['txn_date'])

    rfm = df.groupby('customer_id').agg(
        last_txn_date=('txn_date', 'max'),
        frequency=('txn_date', 'count'),
        monetary=('amount', 'sum')
    ).reset_index()

    rfm['recency_days'] = (
        snapshot_date - rfm['last_txn_date']
    ).dt.days

    return rfm[['customer_id', 'recency_days', 'frequency', 'monetary']]


def score_rfm(rfm_raw: pd.DataFrame) -> pd.DataFrame:
    """Convert raw RFM values to 1-5 scores using NTILE-equivalent quintiles.

    Uses pd.qcut for equal-population quintiles.
    Recency: LOWER days = HIGHER score.
    Frequency & Monetary: HIGHER = HIGHER score.

    Args:
        rfm_raw: DataFrame of raw RFM values.

    Returns:
        DataFrame of scored RFM values containing R, F, M, rfm_score, and rfm_combined.
    """
    rfm = rfm_raw.copy()

    rfm['R'] = pd.qcut(
        rfm['recency_days'].rank(method='first'),
        q=5,
        labels=[5, 4, 3, 2, 1]
    ).astype(int)

    rfm['F'] = pd.qcut(
        rfm['frequency'].rank(method='first'),
        q=5,
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    rfm['M'] = pd.qcut(
        rfm['monetary'].rank(method='first'),
        q=5,
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    rfm['rfm_score'] = rfm['R'].astype(str) + \
                       rfm['F'].astype(str) + \
                       rfm['M'].astype(str)

    rfm['rfm_combined'] = rfm[['R', 'F', 'M']].sum(axis=1)

    return rfm


def _segment_row(r: int, f: int) -> str:
    """Classifies a customer segment based on Recency and Frequency scores.

    Args:
        r: Recency score (1-5).
        f: Frequency score (1-5).

    Returns:
        Segment name string.
    """
    if r >= 5 and f >= 5:
        return 'Champions'
    if r <= 2 and f >= 4:
        return 'Cannot Lose'
    if f >= 4:
        return 'Loyal'
    if r >= 4 and f <= 3:
        return 'New Customer' if f == 1 else 'Potential Loyalist'
    if r <= 3 and f >= 3:
        return 'At Risk'
    if r == 3 and f <= 3:
        return 'Promising'
    if r <= 2 and f <= 2:
        return 'Lost' if r == 1 and f == 1 else 'Hibernating'
    return 'Promising'


def assign_segment(rfm_scored: pd.DataFrame) -> pd.DataFrame:
    """Assign named segments based on R and F scores.

    Args:
        rfm_scored: DataFrame containing R and F scores.

    Returns:
        DataFrame with an added 'segment' column.
    """
    rfm_scored['segment'] = rfm_scored.apply(
        lambda row: _segment_row(row['R'], row['F']), axis=1
    )
    return rfm_scored


def write_rfm_to_db(rfm_final: pd.DataFrame, conn: mysql.connector.MySQLConnection) -> None:
    """Write RFM scores to the customer_rfm table in MySQL database.

    Args:
        rfm_final: DataFrame of finalized RFM segments and scores.
        conn: MySQL connection object.
    """
    cursor = conn.cursor()
    today = date.today()

    upsert_query = """
        INSERT INTO customer_rfm
            (customer_id, score_date, recency_days, frequency,
             monetary, R_score, F_score, M_score,
             rfm_score, rfm_combined, segment)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            recency_days = VALUES(recency_days),
            frequency = VALUES(frequency),
            monetary = VALUES(monetary),
            R_score = VALUES(R_score),
            F_score = VALUES(F_score),
            M_score = VALUES(M_score),
            rfm_score = VALUES(rfm_score),
            rfm_combined = VALUES(rfm_combined),
            segment = VALUES(segment)
    """

    rows = [
        (
            row['customer_id'], today,
            row['recency_days'], row['frequency'], row['monetary'],
            row['R'], row['F'], row['M'],
            row['rfm_score'], row['rfm_combined'], row['segment']
        )
        for _, row in rfm_final.iterrows()
    ]

    cursor.executemany(upsert_query, rows)
    conn.commit()
    cursor.close()
    print(f"[RFM] Written {len(rows)} customer RFM records.")


def run_rfm_engine() -> pd.DataFrame:
    """Main entry point to execute the RFM pipeline.

    Returns:
        DataFrame of calculated RFM segments and scores.
    """
    conn = mysql.connector.connect(**DB_CONFIG)

    try:
        print("[RFM] Loading transactions...")
        df = load_transactions(conn)

        print(f"[RFM] Computing RFM for {df['customer_id'].nunique()} customers...")
        rfm_raw = compute_rfm_raw(df)
        rfm_scored = score_rfm(rfm_raw)
        rfm_final = assign_segment(rfm_scored)

        print("[RFM] Segment distribution:")
        print(rfm_final['segment'].value_counts().to_string())

        write_rfm_to_db(rfm_final, conn)
        return rfm_final

    finally:
        conn.close()


if __name__ == "__main__":
    run_rfm_engine()
