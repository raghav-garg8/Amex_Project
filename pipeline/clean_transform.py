# pipeline/clean_transform.py
"""Data Cleaning and Transformation Pipeline for FinSight.

Loads raw generated transaction and engagement logs, identifies and resolves
data anomalies, standardizes formats, and outputs database-ready clean CSV files.
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple, Set

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

# Fixed Current Date threshold for future-date detection (matching system time context)
CURDATE = datetime(2026, 6, 5)


def _read_and_standardize_dates(
    raw_path: str,
    cat_path: str
) -> Tuple[pd.DataFrame, Set[str], Dict[str, int]]:
    """Loads transaction dataframe, valid categories, and standardizes date format.

    Args:
        raw_path: Path to raw transactions CSV.
        cat_path: Path to categories CSV.

    Returns:
        A tuple of (DataFrame, set of valid categories, initialized anomalies dict).
    """
    df = pd.read_csv(raw_path)
    df_cats = pd.read_csv(cat_path)
    valid_categories = set(df_cats["category_name"].unique())
    
    anomalies = {
        "duplicates": 0,
        "negative_spends": 0,
        "future_dates": 0,
        "invalid_categories": 0,
        "date_formats_corrected": 0
    }

    # Date formatting standardization (mixed format parsing)
    is_standard_format = df["txn_date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    anomalies["date_formats_corrected"] = int((~is_standard_format).sum())
    
    df["txn_date_parsed"] = pd.to_datetime(df["txn_date"], errors="coerce", format="mixed")
    df = df[df["txn_date_parsed"].notna()]
    df["txn_date"] = df["txn_date_parsed"].dt.strftime("%Y-%m-%d")
    
    return df, valid_categories, anomalies


def _filter_and_deduplicate(
    df: pd.DataFrame,
    valid_categories: Set[str],
    anomalies: Dict[str, int]
) -> pd.DataFrame:
    """Filters out future dates, negative spend, bad categories, and duplicates.

    Args:
        df: Standardized DataFrame.
        valid_categories: Set of valid categories.
        anomalies: Dictionary of anomaly counts to update.

    Returns:
        Filtered and clean DataFrame.
    """
    # 1. Exclude future dates
    future_mask = df["txn_date_parsed"] > CURDATE
    anomalies["future_dates"] = int(future_mask.sum())
    df = df[~future_mask]
    df = df.drop(columns=["txn_date_parsed"])
    
    # 2. Exclude negative spends
    negative_mask = df["amount"] < 0
    anomalies["negative_spends"] = int(negative_mask.sum())
    df = df[~negative_mask]

    # 3. Standardize invalid categories to 'UNCATEGORISED'
    invalid_cat_mask = ~df["merchant_category"].isin(valid_categories)
    anomalies["invalid_categories"] = int(invalid_cat_mask.sum())
    df.loc[invalid_cat_mask, "merchant_category"] = "UNCATEGORISED"

    # 4. Deduplicate transactions
    dupe_mask = df.duplicated(subset=["customer_id", "merchant_id", "amount", "txn_date"], keep="first")
    anomalies["duplicates"] = int(dupe_mask.sum())
    df = df[~dupe_mask]
    
    return df


def clean_transactions() -> Tuple[int, int, Dict[str, int]]:
    """Cleans raw transaction records.

    Handles duplicates, negative spends, future dates, date formats, and category mapping.

    Returns:
        A tuple of (initial_row_count, final_row_count, anomaly_counts).
    """
    raw_path = os.path.join(DATA_DIR, "transactions_raw.csv")
    clean_path = os.path.join(DATA_DIR, "transactions_clean.csv")
    cat_path = os.path.join(DATA_DIR, "merchant_categories.csv")

    df, valid_categories, anomalies = _read_and_standardize_dates(raw_path, cat_path)
    initial_rows = len(df)
    
    df_clean = _filter_and_deduplicate(df, valid_categories, anomalies)
    df_clean.to_csv(clean_path, index=False)
    
    return initial_rows, len(df_clean), anomalies


def clean_offer_views() -> Tuple[int, int, Dict[str, int]]:
    """Cleans offer views data, casting boolean type mismatches.

    Returns:
        A tuple of (initial_row_count, final_row_count, anomaly_counts).
    """
    raw_path = os.path.join(DATA_DIR, "offer_views_raw.csv")
    clean_path = os.path.join(DATA_DIR, "offer_views_clean.csv")

    df = pd.read_csv(raw_path)
    initial_rows = len(df)
    
    anomalies = {
        "type_mismatches_resolved": 0,
        "duplicates": 0
    }

    # Count boolean conversions
    string_mismatches = df["was_clicked"].astype(str).str.lower().isin(["true", "false"])
    anomalies["type_mismatches_resolved"] = int(string_mismatches.sum())

    # Map boolean representations to 1 and 0 integers
    df["was_clicked"] = df["was_clicked"].astype(str).str.lower().map({
        "true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0
    }).fillna(0).astype(int)

    # Standardize timestamp format
    df["viewed_at"] = pd.to_datetime(df["viewed_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Drop duplicates
    dupe_mask = df.duplicated(subset=["view_id"])
    anomalies["duplicates"] = int(dupe_mask.sum())
    df = df[~dupe_mask]

    df.to_csv(clean_path, index=False)
    
    return initial_rows, len(df), anomalies


def copy_and_standardize_others() -> Dict[str, Tuple[int, int]]:
    """Standardizes date types and copies remaining files to clean destinations.

    Returns:
        A mapping of file basenames to (initial_rows, final_rows) tuples.
    """
    files_to_process = {
        "customers_raw.csv": ("customers_clean.csv", "customer_id", "%Y-%m-%d"),
        "merchants_raw.csv": ("merchants_clean.csv", "merchant_id", None),
        "email_opens_raw.csv": ("email_opens_clean.csv", "open_id", "%Y-%m-%d %H:%M:%S"),
        "reward_redemptions_raw.csv": ("reward_redemptions_clean.csv", "redemption_id", "%Y-%m-%d %H:%M:%S"),
        "campaign_clicks_raw.csv": ("campaign_clicks_clean.csv", "click_id", "%Y-%m-%d %H:%M:%S"),
    }

    row_counts = {}

    for raw_file, (clean_file, pk_col, date_format) in files_to_process.items():
        raw_path = os.path.join(DATA_DIR, raw_file)
        clean_path = os.path.join(DATA_DIR, clean_file)

        df = pd.read_csv(raw_path)
        initial_rows = len(df)

        if date_format:
            date_cols = [c for c in df.columns if "date" in c or c.endswith("_at")]
            for col in date_cols:
                df[col] = pd.to_datetime(df[col]).dt.strftime(date_format)

        df = df.drop_duplicates(subset=[pk_col])
        df.to_csv(clean_path, index=False)
        row_counts[clean_file] = (initial_rows, len(df))

    return row_counts


def _generate_summary_statistics(
    txn_stats: Tuple[int, int, Dict[str, int]],
    view_stats: Tuple[int, int, Dict[str, int]],
    other_stats: Dict[str, Tuple[int, int]]
) -> Dict[str, Any]:
    """Generates a structured dictionary containing report summary statistics.

    Args:
        txn_stats: Clean transaction results tuple.
        view_stats: Clean view results tuple.
        other_stats: Clean other results mapping.

    Returns:
        Summary statistics dictionary.
    """
    return {
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "transactions": {
            "initial_rows": txn_stats[0],
            "clean_rows": txn_stats[1],
            "anomalies_detected": txn_stats[2]
        },
        "offer_views": {
            "initial_rows": view_stats[0],
            "clean_rows": view_stats[1],
            "anomalies_detected": view_stats[2]
        },
        "other_tables": {
            k: {"initial_rows": v[0], "clean_rows": v[1]}
            for k, v in other_stats.items()
        }
    }


def _write_markdown_report(report_md_path: str, stats: Dict[str, Any]) -> None:
    """Writes the markdown clean report based on the statistics dictionary.

    Args:
        report_md_path: Target markdown filepath.
        stats: Summary statistics dictionary.
    """
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Data Cleaning & Transformation Report\n\n")
        f.write(f"**Execution Date:** {stats['execution_time']}\n")
        f.write(f"**Date Filter Threshold:** {CURDATE.strftime('%Y-%m-%d')}\n\n")
        
        f.write("## 1. Transaction Table Anomalies\n\n")
        f.write("| Anomaly Type | Detected & Resolved Count |\n")
        f.write("|---|---|\n")
        for k, v in stats["transactions"]["anomalies_detected"].items():
            f.write(f"| {k.replace('_', ' ').capitalize()} | {v} |\n")
        
        f.write("\n## 2. Offer Views Anomalies\n\n")
        f.write("| Anomaly Type | Detected & Resolved Count |\n")
        f.write("|---|---|\n")
        for k, v in stats["offer_views"]["anomalies_detected"].items():
            f.write(f"| {k.replace('_', ' ').capitalize()} | {v} |\n")
            
        f.write("\n## 3. Dataset Row Summary\n\n")
        f.write("| Dataset | Raw Row Count | Clean Row Count | Rows Excluded | Error Rate |\n")
        f.write("|---|---|---|---|---|\n")
        
        # Transactions
        t_raw = stats["transactions"]["initial_rows"]
        t_clean = stats["transactions"]["clean_rows"]
        t_excl = t_raw - t_clean
        t_err = (t_excl / t_raw * 100) if t_raw > 0 else 0
        f.write(f"| transactions | {t_raw} | {t_clean} | {t_excl} | {t_err:.2f}% |\n")
        
        # Views
        v_raw = stats["offer_views"]["initial_rows"]
        v_clean = stats["offer_views"]["clean_rows"]
        v_excl = v_raw - v_clean
        v_err = (v_excl / v_raw * 100) if v_raw > 0 else 0
        f.write(f"| offer_views | {v_raw} | {v_clean} | {v_excl} | {v_err:.2f}% |\n")
        
        # Others
        for name, data in stats["other_tables"].items():
            r = data["initial_rows"]
            c = data["clean_rows"]
            excl = r - c
            err = (excl / r * 100) if r > 0 else 0
            f.write(f"| {name.replace('_clean.csv', '')} | {r} | {c} | {excl} | {err:.2f}% |\n")


def write_reports(
    txn_stats: Tuple[int, int, Dict[str, int]],
    view_stats: Tuple[int, int, Dict[str, int]],
    other_stats: Dict[str, Tuple[int, int]]
) -> None:
    """Writes JSON and Markdown cleaning report files to logs/."""
    report_json_path = os.path.join(LOGS_DIR, "cleaning_report.json")
    report_md_path = os.path.join(LOGS_DIR, "cleaning_report.md")

    stats = _generate_summary_statistics(txn_stats, view_stats, other_stats)

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)

    _write_markdown_report(report_md_path, stats)

    print(f"Generated {report_json_path}")
    print(f"Generated {report_md_path}")


if __name__ == "__main__":
    print("Starting data cleaning and transformation...")
    t_s = clean_transactions()
    print(f"Transactions: Cleaned from {t_s[0]} to {t_s[1]} rows.")
    
    v_s = clean_offer_views()
    print(f"Offer Views: Cleaned from {v_s[0]} to {v_s[1]} rows.")
    
    o_s = copy_and_standardize_others()
    write_reports(t_s, v_s, o_s)
    print("Data cleaning complete!")
