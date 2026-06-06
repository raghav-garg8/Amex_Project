"""priority_index.py
FinSight — Customer Behavioral Intelligence Platform

Customer Priority Index — the fusion engine that combines all
three intelligence engines into a single actionable score.

Formula:
  Priority Index = life_event_score
                   × rfm_weight
                   × velocity_weight
                   × engagement_multiplier
                   × channel_diversity_multiplier

  Capped at 100.
"""

import sys
import os
from datetime import date
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import mysql.connector

# Resolve cross-module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scoring')))
from scoring_config import DB_CONFIG, RFM_WEIGHT_MAP


def load_all_scores(conn: mysql.connector.MySQLConnection) -> pd.DataFrame:
    """Load and join all three engine outputs for every customer.

    Left joins ensure all customers appear even if one engine
    produced no score for them.

    Args:
        conn: MySQL connection object.

    Returns:
        DataFrame containing joined customer demographics, RFM, scores,
        velocity, and engagement features.
    """
    query = """
        SELECT
            c.customer_id,
            c.age,
            c.city,
            c.income_band,
            c.card_type,

            -- RFM scores
            r.R_score,
            r.F_score,
            r.M_score,
            r.rfm_combined,
            r.segment AS rfm_segment,

            -- Life event scores
            s.home_score,
            s.relocation_score,
            s.marriage_score,
            s.child_score,
            s.edu_score,
            s.top_event,
            s.opportunity_score AS life_event_score,
            s.recommended_product,
            s.conflict_flag,

            -- Velocity scores
            v.velocity_score,
            v.velocity_label,
            v.velocity_weight,

            -- Engagement scores
            s.engagement_multiplier,
            s.channel_multiplier

        FROM customers c
        LEFT JOIN customer_rfm r
            ON c.customer_id = r.customer_id
        LEFT JOIN customer_scores s
            ON c.customer_id = s.customer_id
        LEFT JOIN customer_velocity v
            ON c.customer_id = v.customer_id
        WHERE c.opted_out = 0
    """
    return pd.read_sql(query, conn)


def compute_rfm_weight(rfm_segment: Optional[str]) -> float:
    """Convert RFM segment name to a priority weight multiplier.

    Args:
        rfm_segment: Segment name string (e.g. 'Champions', 'Lost').

    Returns:
        Priority weight multiplier float.
    """
    if rfm_segment is None:
        return 1.0
    return RFM_WEIGHT_MAP.get(rfm_segment, 1.0)


def compute_priority_index(row: pd.Series) -> float:
    """Compute the Customer Priority Index for a single customer.

    Handles missing values gracefully — if an engine produced
    no score, its component defaults to 1.0 (neutral multiplier).

    Args:
        row: Series representing customer feature row.

    Returns:
        Customer priority index score bounded between 0.0 and 100.0.
    """
    life_event_score = row.get('life_event_score') or 0.0
    rfm_weight = compute_rfm_weight(row.get('rfm_segment', ''))
    velocity_weight = row.get('velocity_weight') or 1.0
    engagement_multiplier = row.get('engagement_multiplier') or 1.0
    channel_multiplier = row.get('channel_multiplier') or 1.0

    if life_event_score == 0:
        # No life event detected — priority index is RFM-only
        base = (row.get('rfm_combined') or 3) * 3
        priority = base * velocity_weight
    else:
        priority = (
            life_event_score
            * rfm_weight
            * velocity_weight
            * engagement_multiplier
            * channel_multiplier
        )

    return round(min(priority, 100.0), 2)


def build_rfm_life_event_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build the RFM × Life Event matrix pivot table.

    Produces a pivot table: RFM segments as rows,
    life events as columns, average priority index as values.

    Args:
        df: DataFrame containing rfm_segment, top_event, and priority_index.

    Returns:
        Pivot table DataFrame.
    """
    df_flagged = df[df['top_event'].notna()].copy()

    if df_flagged.empty:
        return pd.DataFrame()

    matrix = df_flagged.pivot_table(
        values='priority_index',
        index='rfm_segment',
        columns='top_event',
        aggfunc='mean',
        fill_value=0
    ).round(1)

    # Add count column for context
    counts = df_flagged.groupby('rfm_segment').size().rename('customer_count')
    matrix = matrix.join(counts)

    return matrix


def _clean_val(val: Any) -> Any:
    """Helper to convert NumPy/Pandas scalar values to standard Python values.

    Args:
        val: Value to clean.

    Returns:
        Cleaned Python value or None.
    """
    if pd.isna(val):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


def _action_tier(score: float) -> str:
    """Determine the action tier label for a priority index score.

    Args:
        score: Priority index score.

    Returns:
        Action tier string label.
    """
    if score >= 75:
        return 'IMMEDIATE'
    if score >= 50:
        return 'HIGH'
    if score >= 25:
        return 'MEDIUM'
    return 'LOW'


def _build_priority_insert_rows(df: pd.DataFrame) -> List[Tuple]:
    """Helper to convert the priority DataFrame rows into a list of tuples.

    Args:
        df: DataFrame of computed priority scores.

    Returns:
        List of database row insert tuples.
    """
    rows = []
    today = date.today()
    for _, row in df.iterrows():
        rows.append((
            _clean_val(row['customer_id']), today,
            _clean_val(row.get('life_event_score')),
            _clean_val(row.get('rfm_segment')),
            _clean_val(compute_rfm_weight(row.get('rfm_segment', ''))),
            _clean_val(row.get('velocity_weight')),
            _clean_val(row.get('engagement_multiplier')),
            _clean_val(row.get('channel_multiplier')),
            _clean_val(row['priority_index']),
            _clean_val(row.get('top_event')),
            _clean_val(row.get('recommended_product')),
            _clean_val(_action_tier(row['priority_index']))
        ))
    return rows


def write_priority_index_to_db(df: pd.DataFrame, conn: mysql.connector.MySQLConnection) -> None:
    """Write Priority Index scores to customer_priority table in MySQL database.

    Args:
        df: DataFrame of computed priority scores.
        conn: MySQL connection object.
    """
    cursor = conn.cursor()

    upsert_query = """
        INSERT INTO customer_priority
            (customer_id, score_date, life_event_score,
             rfm_segment, rfm_weight, velocity_weight,
             engagement_multiplier, channel_multiplier,
             priority_index, top_event, recommended_product,
             action_tier)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            life_event_score = VALUES(life_event_score),
            rfm_segment = VALUES(rfm_segment),
            rfm_weight = VALUES(rfm_weight),
            velocity_weight = VALUES(velocity_weight),
            engagement_multiplier = VALUES(engagement_multiplier),
            channel_multiplier = VALUES(channel_multiplier),
            priority_index = VALUES(priority_index),
            top_event = VALUES(top_event),
            recommended_product = VALUES(recommended_product),
            action_tier = VALUES(action_tier)
    """

    rows = _build_priority_insert_rows(df)

    cursor.executemany(upsert_query, rows)
    conn.commit()
    cursor.close()
    print(f"[PRIORITY] Written {len(rows)} priority index records.")


def run_priority_index() -> pd.DataFrame:
    """Main entry point to execute the Priority Index fusion pipeline.

    Returns:
        DataFrame containing final customer priority calculations.
    """
    conn = mysql.connector.connect(**DB_CONFIG)

    try:
        print("[PRIORITY] Loading all engine scores...")
        df = load_all_scores(conn)

        print("[PRIORITY] Computing Priority Index...")
        df['priority_index'] = df.apply(compute_priority_index, axis=1)

        print("[PRIORITY] Building RFM × Life Event matrix...")
        matrix = build_rfm_life_event_matrix(df)
        if not matrix.empty:
            print("\n[PRIORITY] RFM × Life Event Matrix:")
            print(matrix.to_string())

        print("\n[PRIORITY] Action tier distribution:")
        tiers = df['priority_index'].apply(_action_tier)
        print(tiers.value_counts().to_string())

        write_priority_index_to_db(df, conn)
        return df

    finally:
        conn.close()


if __name__ == "__main__":
    run_priority_index()
