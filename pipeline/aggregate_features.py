# pipeline/aggregate_features.py
"""Feature Aggregation Pipeline for LifeEventRadar.

Reads the pre-designed analytical SQL query signal_detection.sql and runs it
on the local MySQL database to populate the customer_features table.
"""

import os
import sys
import mysql.connector

# Central connection configurations (consistent with load_to_db.py)
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "amex_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "amex_password")
DB_NAME = os.getenv("DB_NAME", "life_event_radar_db")

QUERY_PATH = "/Users/raghavgarg/Desktop/AMEX_PROJECT/database/queries/signal_detection.sql"

def get_connection() -> mysql.connector.MySQLConnection:
    """Establishes connection to the target MySQL database."""
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "raise_on_warnings": True
    }
    return mysql.connector.connect(**config)

def run_aggregation() -> None:
    """Reads signal_detection.sql and inserts the aggregated results into customer_features."""
    print(f"Connecting to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Truncate customer_features to ensure a clean rebuild of features
        print("Resetting 'customer_features' table...")
        cursor.execute("TRUNCATE TABLE customer_features;")
        
        # 2. Read the signal_detection aggregation query
        print(f"Reading query from {QUERY_PATH}...")
        if not os.path.exists(QUERY_PATH):
            print(f"Error: SQL query file not found at {QUERY_PATH}")
            sys.exit(1)
            
        with open(QUERY_PATH, "r", encoding="utf-8") as f:
            query_sql = f.read()
            
        # 3. Construct and run the INSERT SELECT aggregation statement
        # This executes the entire feature aggregation directly inside MySQL
        insert_sql = f"""
            INSERT INTO customer_features (
                customer_id, feature_date, furniture_spend_90d, appliance_spend_90d, real_estate_visits_90d, insurance_payment_flag,
                moving_spend_90d, new_city_utility_flag, jewelry_spend_90d, wedding_spend_90d, hospital_payment_flag,
                baby_product_spend_30d, pharmacy_spend_spike, university_fee_flag, test_prep_spend_90d, spend_growth_3m,
                spend_cohort, distinct_cities_90d
            )
            {query_sql}
        """
        
        print("Executing transactional feature aggregation query inside MySQL...")
        cursor.execute(insert_sql)
        conn.commit()
        
        rows_inserted = cursor.rowcount
        print(f"Aggregation complete! Loaded {rows_inserted} customer rows into 'customer_features' table.")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Database error during aggregation: {err}")
        sys.exit(1)

if __name__ == "__main__":
    run_aggregation()
