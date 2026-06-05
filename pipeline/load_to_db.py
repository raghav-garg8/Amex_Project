# pipeline/load_to_db.py
"""Database Loader Pipeline for LifeEventRadar.

Reads sanitized clean CSV files and ingests them into the local MySQL database.
Initializes the database schema by executing schema.sql before loading.
"""

import os
import sys
import pandas as pd
from typing import List, Dict, Any, Tuple
import mysql.connector
from mysql.connector import errorcode

DATA_DIR = "/Users/raghavgarg/Desktop/AMEX_PROJECT/data"
SCHEMA_PATH = "/Users/raghavgarg/Desktop/AMEX_PROJECT/database/schema.sql"

# Read connection configurations from environment variables or defaults
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "amex_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "amex_password")
DB_NAME = os.getenv("DB_NAME", "life_event_radar_db")

def get_connection(include_db: bool = True) -> mysql.connector.MySQLConnection:
    """Establishes connection to MySQL.

    Args:
        include_db: If True, connects directly to DB_NAME.

    Returns:
        A mysql connection object.
    """
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "raise_on_warnings": True
    }
    if include_db:
        config["database"] = DB_NAME
        
    return mysql.connector.connect(**config)

def initialize_database() -> None:
    """Creates the database if it doesn't exist and runs schema DDL statements."""
    print(f"Connecting to MySQL on {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    try:
        conn = get_connection(include_db=False)
        cursor = conn.cursor()
        
        # Ensure database exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"Database '{DB_NAME}' verified/created.")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Failed to verify/create database: {err}")
        sys.exit(1)

    # Execute schema.sql DDL to drop/recreate all tables
    print(f"Initializing schema from {SCHEMA_PATH}...")
    try:
        conn = get_connection(include_db=True)
        cursor = conn.cursor()
        
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        # Standard parser: split by semicolon and run statements
        # Handles comments and empty lines safely
        statements = sql_script.split(";")
        for stmt in statements:
            cleaned_stmt = stmt.strip()
            if cleaned_stmt and not cleaned_stmt.startswith("--"):
                cursor.execute(cleaned_stmt)
                
        conn.commit()
        print("Database schema tables successfully recreated.")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Failed to execute schema DDL: {err}")
        sys.exit(1)

def bulk_insert_df(conn: mysql.connector.MySQLConnection, table_name: str, df: pd.DataFrame, query: str, batch_size: int = 5000) -> int:
    """Inserts a pandas DataFrame into a SQL table in parameterized batches.

    Args:
        conn: mysql connection object.
        table_name: Destination table name.
        df: Pandas DataFrame containing clean records.
        query: Parameterized INSERT query string.
        batch_size: Batch size of records to insert at once.

    Returns:
        Number of successfully inserted rows.
    """
    cursor = conn.cursor()
    # Convert dataframe NaN to None for SQL NULL mapping
    df_clean = df.where(pd.notnull(df), None)
    records = [tuple(row) for row in df_clean.values]
    
    total_rows = len(records)
    inserted_rows = 0
    
    for i in range(0, total_rows, batch_size):
        batch = records[i:i+batch_size]
        cursor.executemany(query, batch)
        inserted_rows += len(batch)
        
    conn.commit()
    cursor.close()
    print(f"Table '{table_name}': Loaded {inserted_rows}/{total_rows} rows.")
    return inserted_rows

def load_data() -> None:
    """Loads cleaned CSV files into MySQL tables in order of dependency constraints."""
    print("Starting data ingestion into MySQL...")
    try:
        conn = get_connection(include_db=True)
    except mysql.connector.Error as err:
        print(f"Failed to connect to '{DB_NAME}': {err}")
        sys.exit(1)

    # 1. Ingest merchant_categories
    print("\nLoading reference data...")
    df_categories = pd.read_csv(os.path.join(DATA_DIR, "merchant_categories.csv"))
    categories_query = """
        INSERT INTO merchant_categories (category_id, category_name, life_event_tag, signal_weight, signal_type, spend_threshold, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "merchant_categories", df_categories, categories_query)

    # 2. Ingest customers
    df_customers = pd.read_csv(os.path.join(DATA_DIR, "customers_clean.csv"))
    # Match schema column ordering
    df_customers_ordered = df_customers[["customer_id", "age", "city", "income_band", "card_type", "join_date", "life_stage", "opted_out", "created_at"]]
    customers_query = """
        INSERT INTO customers (customer_id, age, city, income_band, card_type, join_date, life_stage, opted_out, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "customers", df_customers_ordered, customers_query)

    # 3. Ingest merchants
    df_merchants = pd.read_csv(os.path.join(DATA_DIR, "merchants_clean.csv"))
    # merchants_clean has: merchant_id, merchant_name, category_id, city, is_amex_partner
    merchants_query = """
        INSERT INTO merchants (merchant_id, merchant_name, category_id, city, is_amex_partner)
        VALUES (%s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "merchants", df_merchants, merchants_query)

    # 4. Ingest transactions (batched 5000 rows at a time)
    print("\nLoading transaction and log datasets...")
    df_transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions_clean.csv"))
    transactions_query = """
        INSERT INTO transactions (txn_id, customer_id, merchant_id, merchant_category, amount, txn_date, txn_city, channel, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "transactions", df_transactions, transactions_query, batch_size=5000)

    # 5. Ingest offer_views
    df_offer_views = pd.read_csv(os.path.join(DATA_DIR, "offer_views_clean.csv"))
    offer_views_query = """
        INSERT INTO offer_views (view_id, customer_id, offer_id, offer_category, channel, viewed_at, was_clicked, placement_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "offer_views", df_offer_views, offer_views_query)

    # 6. Ingest email_opens
    df_email_opens = pd.read_csv(os.path.join(DATA_DIR, "email_opens_clean.csv"))
    email_opens_query = """
        INSERT INTO email_opens (open_id, customer_id, campaign_id, offer_category, opened_at, device_type)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "email_opens", df_email_opens, email_opens_query)

    # 7. Ingest reward_redemptions
    df_reward_redemptions = pd.read_csv(os.path.join(DATA_DIR, "reward_redemptions_clean.csv"))
    reward_redemptions_query = """
        INSERT INTO reward_redemptions (redemption_id, customer_id, points_redeemed, redemption_category, redeemed_at, dollar_value)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "reward_redemptions", df_reward_redemptions, reward_redemptions_query)

    # 8. Ingest campaign_clicks
    df_campaign_clicks = pd.read_csv(os.path.join(DATA_DIR, "campaign_clicks_clean.csv"))
    campaign_clicks_query = """
        INSERT INTO campaign_clicks (click_id, customer_id, campaign_id, offer_category, channel, clicked_at)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "campaign_clicks", df_campaign_clicks, campaign_clicks_query)

    # 9. Ingest compliance opt-out registry
    # Automatically sync opted_out = 1 customers from customers table to registry
    print("\nLoading compliance registry...")
    df_opted_out = df_customers[df_customers["opted_out"] == 1].copy()
    if not df_opted_out.empty:
        df_opt_registry = pd.DataFrame({
            "customer_id": df_opted_out["customer_id"],
            "opted_out_at": df_opted_out["created_at"],
            "opt_out_channel": "app"  # default simulation channel
        })
        opt_out_query = """
            INSERT INTO opt_out_registry (customer_id, opted_out_at, opt_out_channel)
            VALUES (%s, %s, %s);
        """
        bulk_insert_df(conn, "opt_out_registry", df_opt_registry, opt_out_query)
    else:
        print("Table 'opt_out_registry': 0 customers found with opted_out=1. Skipping.")

    conn.close()
    print("\nAll datasets successfully loaded to MySQL database!")

# -------------------------------------------------------------------------
# Main Execution Entry
# -------------------------------------------------------------------------
if __name__ == "__main__":
    initialize_database()
    load_data()
