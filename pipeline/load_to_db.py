# pipeline/load_to_db.py
"""Database Loader Pipeline for FinSight.

Reads sanitized clean CSV files and ingests them into the local MySQL database.
Initializes the database schema by executing schema.sql before loading.
"""

import os
import sys
from typing import List, Dict, Any, Tuple
import pandas as pd
import mysql.connector

# Resolve cross-module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scoring")))
from scoring_config import DB_CONFIG

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/schema.sql"))

# Read connection configurations from DB_CONFIG
DB_HOST = DB_CONFIG["host"]
DB_PORT = DB_CONFIG["port"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]
DB_NAME = DB_CONFIG["database"]


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
        "raise_on_warnings": False
    }
    if include_db:
        config["database"] = DB_NAME
        
    return mysql.connector.connect(**config)


def _verify_database_exists() -> None:
    """Creates the database if it doesn't exist."""
    print(f"Connecting to MySQL on {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    try:
        conn = get_connection(include_db=False)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        print(f"Database '{DB_NAME}' verified/created.")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Failed to verify/create database: {err}")
        sys.exit(1)


def _execute_schema_ddl() -> None:
    """Reads schema.sql and executes DDL statements to drop and recreate all tables."""
    print(f"Initializing schema from {SCHEMA_PATH}...")
    try:
        conn = get_connection(include_db=True)
        cursor = conn.cursor()
        
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        statements = sql_script.split(";")
        for stmt in statements:
            lines = [line.split("--")[0].strip() for line in stmt.split("\n")]
            cleaned_stmt = " ".join([line for line in lines if line])
            if cleaned_stmt:
                cursor.execute(cleaned_stmt)
                
        conn.commit()
        print("Database schema tables successfully recreated.")
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Failed to execute schema DDL: {err}")
        sys.exit(1)


def initialize_database() -> None:
    """Creates the database if it doesn't exist and runs schema DDL statements."""
    _verify_database_exists()
    _execute_schema_ddl()


def bulk_insert_df(
    conn: mysql.connector.MySQLConnection,
    table_name: str,
    df: pd.DataFrame,
    query: str,
    batch_size: int = 5000
) -> int:
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
    records = []
    for row in df.values:
        cleaned_row = tuple(None if pd.isna(x) else x for x in row)
        records.append(cleaned_row)
    
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


def _load_reference_tables(conn: mysql.connector.MySQLConnection) -> pd.DataFrame:
    """Loads merchant categories, customers, and merchants reference tables.

    Args:
        conn: mysql connection.

    Returns:
        DataFrame containing customers.
    """
    print("\nLoading reference data...")
    
    # 1. Ingest merchant_categories
    df_categories = pd.read_csv(os.path.join(DATA_DIR, "merchant_categories.csv"))
    categories_query = """
        INSERT INTO merchant_categories (category_id, category_name, life_event_tag, signal_weight, signal_type, spend_threshold, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "merchant_categories", df_categories, categories_query)

    # 2. Ingest customers
    df_customers = pd.read_csv(os.path.join(DATA_DIR, "customers_clean.csv"))
    df_customers_ordered = df_customers[["customer_id", "age", "city", "income_band", "card_type", "join_date", "life_stage", "opted_out", "created_at"]]
    customers_query = """
        INSERT INTO customers (customer_id, age, city, income_band, card_type, join_date, life_stage, opted_out, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "customers", df_customers_ordered, customers_query)

    # 3. Ingest merchants
    df_merchants = pd.read_csv(os.path.join(DATA_DIR, "merchants_clean.csv"))
    merchants_query = """
        INSERT INTO merchants (merchant_id, merchant_name, category_id, city, is_partner)
        VALUES (%s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "merchants", df_merchants, merchants_query)
    
    return df_customers


def _load_transactional_tables(conn: mysql.connector.MySQLConnection) -> None:
    """Loads transactions, offer views, email opens, reward redemptions, and clicks.

    Args:
        conn: mysql connection.
    """
    print("\nLoading transaction and log datasets...")
    
    # 1. Ingest transactions
    df_transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions_clean.csv"))
    transactions_query = """
        INSERT INTO transactions (txn_id, customer_id, merchant_id, merchant_category, amount, txn_date, txn_city, channel, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "transactions", df_transactions, transactions_query, batch_size=5000)

    # 2. Ingest offer_views
    df_offer_views = pd.read_csv(os.path.join(DATA_DIR, "offer_views_clean.csv"))
    offer_views_query = """
        INSERT INTO offer_views (view_id, customer_id, offer_id, offer_category, channel, viewed_at, was_clicked, placement_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "offer_views", df_offer_views, offer_views_query)

    # 3. Ingest email_opens
    df_email_opens = pd.read_csv(os.path.join(DATA_DIR, "email_opens_clean.csv"))
    email_opens_query = """
        INSERT INTO email_opens (open_id, customer_id, campaign_id, offer_category, opened_at, device_type)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "email_opens", df_email_opens, email_opens_query)

    # 4. Ingest reward_redemptions
    df_reward_redemptions = pd.read_csv(os.path.join(DATA_DIR, "reward_redemptions_clean.csv"))
    reward_redemptions_query = """
        INSERT INTO reward_redemptions (redemption_id, customer_id, points_redeemed, redemption_category, redeemed_at, dollar_value)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "reward_redemptions", df_reward_redemptions, reward_redemptions_query)

    # 5. Ingest campaign_clicks
    df_campaign_clicks = pd.read_csv(os.path.join(DATA_DIR, "campaign_clicks_clean.csv"))
    campaign_clicks_query = """
        INSERT INTO campaign_clicks (click_id, customer_id, campaign_id, offer_category, channel, clicked_at)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    bulk_insert_df(conn, "campaign_clicks", df_campaign_clicks, campaign_clicks_query)


def _load_compliance_registry(conn: mysql.connector.MySQLConnection, df_customers: pd.DataFrame) -> None:
    """Extracts opted out customers and syncs them to compliance opt-out registry table.

    Args:
        conn: mysql connection.
        df_customers: Customer master DataFrame.
    """
    print("\nLoading compliance registry...")
    df_opted_out = df_customers[df_customers["opted_out"] == 1].copy()
    if not df_opted_out.empty:
        df_opt_registry = pd.DataFrame({
            "customer_id": df_opted_out["customer_id"],
            "opted_out_at": df_opted_out["created_at"],
            "opt_out_channel": "app"
        })
        opt_out_query = """
            INSERT INTO opt_out_registry (customer_id, opted_out_at, opt_out_channel)
            VALUES (%s, %s, %s);
        """
        bulk_insert_df(conn, "opt_out_registry", df_opt_registry, opt_out_query)
    else:
        print("Table 'opt_out_registry': 0 customers found with opted_out=1. Skipping.")


def load_data() -> None:
    """Loads cleaned CSV files into MySQL tables in order of dependency constraints."""
    print("Starting data ingestion into MySQL...")
    try:
        conn = get_connection(include_db=True)
    except mysql.connector.Error as err:
        print(f"Failed to connect to '{DB_NAME}': {err}")
        sys.exit(1)

    try:
        df_customers = _load_reference_tables(conn)
        _load_transactional_tables(conn)
        _load_compliance_registry(conn, df_customers)
    finally:
        conn.close()
    print("\nAll datasets successfully loaded to MySQL database!")


if __name__ == "__main__":
    initialize_database()
    load_data()
