# pipeline/generate_data.py
"""Synthetic Data Generator for LifeEventRadar.

Generates realistic transaction and engagement datasets, injecting typical
data anomalies to validate the cleaning and ingestion layer.
"""

import os
import csv
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
from faker import Faker

# Initialize settings and deterministic seeds
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

fake = Faker()
fake.seed_instance(RANDOM_SEED)

DATA_DIR = "/Users/raghavgarg/Desktop/AMEX_PROJECT/data"
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------------------------------
# Reference Configuration: Merchant Categories
# -------------------------------------------------------------------------
CATEGORIES = [
    # Home Purchase (Thresholds and weights from SCORING_METHODOLOGY.md)
    {"id": 1, "name": "FURNITURE_STORES", "tag": "home_purchase", "weight": 30, "type": "spend_scaled", "threshold": 50000.0, "desc": "Furniture purchases for home outfitting"},
    {"id": 2, "name": "APPLIANCES", "tag": "home_purchase", "weight": 25, "type": "spend_scaled", "threshold": 30000.0, "desc": "Kitchen and household appliances"},
    {"id": 3, "name": "REAL_ESTATE_PORTALS", "tag": "home_purchase", "weight": 20, "type": "frequency", "threshold": None, "desc": "House hunting web portals"},
    {"id": 4, "name": "HOME_INSURANCE", "tag": "home_purchase", "weight": 15, "type": "binary", "threshold": None, "desc": "Home insurance policy payment"},

    # Relocation
    {"id": 5, "name": "MOVING_COMPANIES", "tag": "relocation", "weight": 35, "type": "spend_scaled", "threshold": 20000.0, "desc": "Moving and cargo logistics services"},
    {"id": 6, "name": "NEW_CITY_UTILITIES", "tag": "relocation", "weight": 25, "type": "binary", "threshold": None, "desc": "Utility deposits or setup in a new city"},
    {"id": 7, "name": "HOTELS", "tag": "relocation", "weight": 20, "type": "frequency", "threshold": None, "desc": "Hotel bookings and lodging"},
    {"id": 8, "name": "FOREX", "tag": "relocation", "weight": 10, "type": "binary", "threshold": None, "desc": "Foreign currency exchange and overseas spend"},

    # Marriage
    {"id": 9, "name": "JEWELRY_STORES", "tag": "marriage", "weight": 30, "type": "spend_scaled", "threshold": 40000.0, "desc": "Engagement ring and fine jewelry spends"},
    {"id": 10, "name": "WEDDING_VENUES", "tag": "marriage", "weight": 25, "type": "spend_scaled", "threshold": 50000.0, "desc": "Venue and banquet bookings"},
    {"id": 11, "name": "HONEYMOON_TRAVEL", "tag": "marriage", "weight": 25, "type": "spend_scaled", "threshold": 30000.0, "desc": "Honeymoon flights and travel packages"},
    {"id": 12, "name": "FORMAL_WEAR", "tag": "marriage", "weight": 10, "type": "binary", "threshold": None, "desc": "Suits, gowns, and wedding apparel"},

    # New Child
    {"id": 13, "name": "MATERNITY_HOSPITAL", "tag": "new_child", "weight": 35, "type": "binary", "threshold": None, "desc": "Maternity care and delivery costs"},
    {"id": 14, "name": "BABY_PRODUCTS", "tag": "new_child", "weight": 25, "type": "spend_scaled", "threshold": 15000.0, "desc": "Baby toys, clothing, and strollers"},
    {"id": 15, "name": "PHARMACY", "tag": "new_child", "weight": 20, "type": "binary", "threshold": None, "desc": "Spike in medication and wellness purchases"},
    {"id": 16, "name": "PEDIATRIC_CLINICS", "tag": "new_child", "weight": 10, "type": "binary", "threshold": None, "desc": "Child immunization and clinic checkups"},

    # Higher Education
    {"id": 17, "name": "UNIVERSITY_FEES", "tag": "higher_education", "weight": 35, "type": "binary", "threshold": None, "desc": "Tuition and enrollment fees"},
    {"id": 18, "name": "TEST_PREP", "tag": "higher_education", "weight": 25, "type": "spend_scaled", "threshold": 10000.0, "desc": "Coaching classes and test prep books"},
    {"id": 19, "name": "STUDENT_HOUSING", "tag": "higher_education", "weight": 20, "type": "binary", "threshold": None, "desc": "Hostel and student lodging deposits"},
    {"id": 20, "name": "STATIONERY_LAPTOPS", "tag": "higher_education", "weight": 10, "type": "binary", "threshold": None, "desc": "Laptop and study supplies purchase"},

    # Neutral Spend (No signal for life events)
    {"id": 21, "name": "GROCERIES", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Supermarkets and food stores"},
    {"id": 22, "name": "GAS_STATIONS", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Fuel and service stations"},
    {"id": 23, "name": "DINING", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Restaurants and bars"},
    {"id": 24, "name": "UTILITIES", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Electricity, gas, water billings"},
    {"id": 25, "name": "ENTERTAINMENT", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Movie halls, events, streaming"},
    {"id": 26, "name": "CLOTHING", "tag": "neutral", "weight": 0, "type": "neutral", "threshold": None, "desc": "Apparel and accessories store"},
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Pune", "Ahmedabad"]

# -------------------------------------------------------------------------
# Helper Functions for Data Simulation
# -------------------------------------------------------------------------
def generate_merchant_categories() -> None:
    """Generates the static merchant categories reference file."""
    path = os.path.join(DATA_DIR, "merchant_categories.csv")
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category_id", "category_name", "life_event_tag", "signal_weight", "signal_type", "spend_threshold", "description"])
        for cat in CATEGORIES:
            writer.writerow([
                cat["id"],
                cat["name"],
                cat["tag"],
                cat["weight"],
                cat["type"],
                "" if cat["threshold"] is None else cat["threshold"],
                cat["desc"]
            ])
    print(f"Generated {path}")

def generate_customers(num_customers: int = 1000) -> List[Dict[str, Any]]:
    """Simulates customer master profiles and writes to CSV.

    Args:
        num_customers: Number of customers to generate.

    Returns:
        List of simulated customer profiles.
    """
    customers = []
    path = os.path.join(DATA_DIR, "customers_raw.csv")

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "age", "city", "income_band", "card_type", "join_date", "life_stage", "opted_out", "created_at"])
        
        for cid in range(1, num_customers + 1):
            age = int(np.random.randint(18, 76))
            city = random.choice(CITIES)
            
            # Determine income band with probabilities
            income_band = np.random.choice(
                ["LOW", "MEDIUM", "HIGH", "PREMIUM"],
                p=[0.3, 0.4, 0.2, 0.1]
            )
            
            # Assign appropriate AmEx cards
            card_map = {
                "LOW": ["Blue", "Green"],
                "MEDIUM": ["Green", "Gold"],
                "HIGH": ["Gold", "Platinum"],
                "PREMIUM": ["Platinum"]
            }
            card_type = random.choice(card_map[income_band])
            
            # Simulated dates
            days_ago = np.random.randint(365, 365 * 5)
            join_date = (datetime.now() - timedelta(days=int(days_ago))).date()
            
            # Assign life stage dynamically based on age
            if age < 24:
                life_stage = "Student"
            elif age < 35:
                life_stage = "Young Professional"
            elif age < 60:
                life_stage = "Family"
            else:
                life_stage = "Senior"
                
            # 2% opted-out registry rate
            opted_out = 1 if np.random.rand() < 0.02 else 0
            created_at = datetime.now() - timedelta(days=int(days_ago) - 10)
            
            customers.append({
                "customer_id": cid,
                "age": age,
                "city": city,
                "income_band": income_band,
                "card_type": card_type,
                "join_date": join_date,
                "life_stage": life_stage,
                "opted_out": opted_out,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            writer.writerow([
                cid, age, city, income_band, card_type,
                join_date.strftime("%Y-%m-%d"), life_stage, opted_out,
                created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])
            
    print(f"Generated {path}")
    return customers

def generate_merchants(num_merchants: int = 200) -> List[Dict[str, Any]]:
    """Simulates merchant master list and writes to CSV.

    Args:
        num_merchants: Number of merchants to generate.

    Returns:
        List of simulated merchant profiles.
    """
    merchants = []
    path = os.path.join(DATA_DIR, "merchants_raw.csv")

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["merchant_id", "merchant_name", "category_id", "city", "is_amex_partner"])
        
        for mid in range(1, num_merchants + 1):
            cat = random.choice(CATEGORIES)
            city = random.choice(CITIES)
            is_partner = 1 if np.random.rand() < 0.15 else 0
            
            # Form clean name suffix based on category type
            name_suffixes = {
                "FURNITURE_STORES": ["Furniture Co", "Decors", "Comforts"],
                "APPLIANCES": ["Appliances Store", "Kitchens", "Electronics"],
                "REAL_ESTATE_PORTALS": ["Homes Tech", "Realty Direct", "Properties Portal"],
                "HOME_INSURANCE": ["Surety Home", "Shield Insurance", "Covered Corp"],
                "MOVING_COMPANIES": ["Movers & Shippers", "Cargo Express", "Relo logistics"],
                "NEW_CITY_UTILITIES": ["Power Grid", "Gas Supply", "Broadband Net"],
                "HOTELS": ["Suites Hotel", "Inns & Resorts", "Lodge & Stays"],
                "FOREX": ["Forex Swap", "Exchanges", "FX Global"],
                "JEWELRY_STORES": ["Fine Jewelers", "Ornaments", "Diamonds Gold"],
                "WEDDING_VENUES": ["Banquets Hall", "Events Lawn", "Wedlock Arena"],
                "HONEYMOON_TRAVEL": ["Travel Horizons", "Tours Destinations", "Escapes Packages"],
                "FORMAL_WEAR": ["Apparels Wedding", "Formal Tailors", "Attire Store"],
                "MATERNITY_HOSPITAL": ["Maternity Care Centre", "Cradles Hospital", "Women Health Clinic"],
                "BABY_PRODUCTS": ["Baby Bazaar", "Toddler Toys", "Nursery Essentials"],
                "PHARMACY": ["Medicines Pharmacy", "Apothecary Wellness", "Drugstore Plus"],
                "PEDIATRIC_CLINICS": ["Pediatrics clinic", "Childcare Doctors", "Infant Clinic"],
                "UNIVERSITY_FEES": ["Global University", "Technological Institute", "Business School"],
                "TEST_PREP": ["Exam Academy", "Prep Coaching Classes", "Tutors Hub"],
                "STUDENT_HOUSING": ["Student Residency", "Hostels Co", "Lodgings PG"],
                "STATIONERY_LAPTOPS": ["Office & Study Supplies", "Computers Center", "Gadgets Hub"],
                "GROCERIES": ["Super Grocers", "Bazaar Grocery", "Fresh Mart"],
                "GAS_STATIONS": ["Fuel Point", "Petrol Mart", "Energy Refills"],
                "DINING": ["Gourmet Bistro", "Flavors Restaurant", "Eats Diner"],
                "FAST_FOOD": ["Quick Bites", "Cafe Corner", "Burgers Co"],
                "UTILITIES": ["Power Utilities", "Water Board", "Telecom Corp"],
                "ENTERTAINMENT": ["Cinema Hall", "Events Club", "Streamings Online"],
                "CLOTHING": ["Trendy Outfits", "Fashions store", "Attire Emporium"]
            }
            
            suffix = random.choice(name_suffixes.get(cat["name"], ["Mart", "Stores"]))
            name = f"{fake.company()} {suffix}"
            
            merchants.append({
                "merchant_id": mid,
                "merchant_name": name,
                "category_id": cat["id"],
                "category_name": cat["name"],
                "city": city,
                "is_amex_partner": is_partner
            })
            
            writer.writerow([mid, name, cat["id"], city, is_partner])
            
    print(f"Generated {path}")
    return merchants

# -------------------------------------------------------------------------
# Transactions Simulation
# -------------------------------------------------------------------------
def generate_transactions(
    customers: List[Dict[str, Any]],
    merchants: List[Dict[str, Any]],
    target_count: int = 50000
) -> None:
    """Simulates 12 months of transactional logs with life event triggers and anomalies.

    Args:
        customers: List of simulated customer dictionaries.
        merchants: List of simulated merchant dictionaries.
        target_count: Target number of transactions to generate.
    """
    path = os.path.join(DATA_DIR, "transactions_raw.csv")
    
    # Organize merchants by category for quick lookup
    merchants_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for m in merchants:
        merchants_by_cat.setdefault(m["category_name"], []).append(m)
        
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    
    # Segment customers for life-stage spending simulations (excluding opted_out)
    active_customers = [c for c in customers if c["opted_out"] == 0]
    
    # We assign subsets of customers to trigger specific events in the last 90 days
    # home_purchase, relocation, marriage, new_child, higher_education
    cohort_size = 50
    cohort_home = active_customers[:cohort_size]
    cohort_relo = active_customers[cohort_size:cohort_size*2]
    cohort_marr = active_customers[cohort_size*2:cohort_size*3]
    cohort_baby = active_customers[cohort_size*3:cohort_size*4]
    cohort_educ = active_customers[cohort_size*4:cohort_size*5]
    
    transactions: List[List[Any]] = []
    txn_id_counter = 10000001
    
    # Base multiplier based on income band
    income_multipliers = {"LOW": 0.6, "MEDIUM": 1.0, "HIGH": 1.8, "PREMIUM": 3.0}

    # Generate standard transaction distribution (neutral spend)
    for c in customers:
        cid = c["customer_id"]
        mult = income_multipliers[c["income_band"]]
        
        # Simulate regular transactions month-by-month
        for month in range(12):
            month_start = start_date + timedelta(days=month * 30.5)
            # 5 to 10 purchases per customer per month
            num_txns = np.random.randint(4, 9)
            
            for _ in range(num_txns):
                days_offset = np.random.randint(0, 30)
                txn_date = month_start + timedelta(days=days_offset)
                if txn_date > end_date:
                    txn_date = end_date
                    
                # Pick a neutral category
                neutral_cats = ["GROCERIES", "GAS_STATIONS", "DINING", "FAST_FOOD", "UTILITIES", "ENTERTAINMENT", "CLOTHING"]
                cat_name = random.choice(neutral_cats)
                
                # Fetch random merchant in category
                m_list = merchants_by_cat.get(cat_name, merchants)
                merchant = random.choice(m_list)
                
                # Dynamic spend amount
                base_spend = np.random.uniform(500, 4500)
                amount = round(base_spend * mult, 2)
                
                channel = np.random.choice(["online", "in_store", "contactless", "international"], p=[0.4, 0.35, 0.2, 0.05])
                status = np.random.choice(["completed", "pending", "reversed"], p=[0.96, 0.03, 0.01])
                
                transactions.append([
                    txn_id_counter,
                    cid,
                    merchant["merchant_id"],
                    cat_name,
                    amount,
                    txn_date.strftime("%Y-%m-%d"),
                    c["city"] if channel != "international" else fake.country(),
                    channel,
                    status
                ])
                txn_id_counter += 1

    # -------------------------------------------------------------------------
    # Inject Life Event Specific Triggers (Months 10 - 12, last 90 days)
    # -------------------------------------------------------------------------
    trigger_start_date = end_date - timedelta(days=90)
    
    # 1. HOME PURCHASE COHORT
    for c in cohort_home:
        cid = c["customer_id"]
        # Trigger Large Furniture Spend (threshold 50k, weight 30)
        t_date = trigger_start_date + timedelta(days=random.randint(10, 45))
        m = random.choice(merchants_by_cat["FURNITURE_STORES"])
        amt = round(random.uniform(52000.0, 75000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "FURNITURE_STORES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Appliance Spend (threshold 30k, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(40, 75))
        m = random.choice(merchants_by_cat["APPLIANCES"])
        amt = round(random.uniform(31000.0, 42000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "APPLIANCES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1
        
        # Trigger Real Estate portal visits (frequency, weight 20)
        for _ in range(3):
            t_date = trigger_start_date + timedelta(days=random.randint(5, 30))
            m = random.choice(merchants_by_cat["REAL_ESTATE_PORTALS"])
            amt = round(random.uniform(99.0, 1500.0), 2)
            transactions.append([txn_id_counter, cid, m["merchant_id"], "REAL_ESTATE_PORTALS", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
            txn_id_counter += 1
            
        # Trigger Home Insurance Payment (binary, weight 15)
        t_date = trigger_start_date + timedelta(days=random.randint(70, 89))
        m = random.choice(merchants_by_cat["HOME_INSURANCE"])
        amt = round(random.uniform(12000.0, 24000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "HOME_INSURANCE", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1

    # 2. RELOCATION COHORT
    for c in cohort_relo:
        cid = c["customer_id"]
        target_city = random.choice([ct for ct in CITIES if ct != c["city"]])
        
        # Trigger Moving Company Spend (threshold 20k, weight 35)
        t_date = trigger_start_date + timedelta(days=random.randint(20, 60))
        m = random.choice(merchants_by_cat["MOVING_COMPANIES"])
        amt = round(random.uniform(21000.0, 35000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "MOVING_COMPANIES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Utility Setup in new city (binary, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(55, 80))
        m = random.choice(merchants_by_cat["NEW_CITY_UTILITIES"])
        amt = round(random.uniform(1500.0, 4500.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "NEW_CITY_UTILITIES", amt, t_date.strftime("%Y-%m-%d"), target_city, "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Hotels in target city (frequency, weight 20)
        for _ in range(2):
            t_date = trigger_start_date + timedelta(days=random.randint(10, 45))
            m = random.choice(merchants_by_cat["HOTELS"])
            amt = round(random.uniform(6000.0, 14000.0), 2)
            transactions.append([txn_id_counter, cid, m["merchant_id"], "HOTELS", amt, t_date.strftime("%Y-%m-%d"), target_city, "contactless", "completed"])
            txn_id_counter += 1
            
        # Trigger Forex spend (binary, weight 10)
        t_date = trigger_start_date + timedelta(days=random.randint(40, 80))
        m = random.choice(merchants_by_cat["FOREX"])
        amt = round(random.uniform(5000.0, 12000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "FOREX", amt, t_date.strftime("%Y-%m-%d"), target_city, "international", "completed"])
        txn_id_counter += 1

    # 3. MARRIAGE COHORT
    for c in cohort_marr:
        cid = c["customer_id"]
        # Trigger Jewelry Store Spend (threshold 40k, weight 30)
        t_date = trigger_start_date + timedelta(days=random.randint(5, 30))
        m = random.choice(merchants_by_cat["JEWELRY_STORES"])
        amt = round(random.uniform(42000.0, 80000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "JEWELRY_STORES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1
        
        # Trigger Wedding Venue Booking (threshold 50k, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(25, 60))
        m = random.choice(merchants_by_cat["WEDDING_VENUES"])
        amt = round(random.uniform(55000.0, 120000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "WEDDING_VENUES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Honeymoon / Travel package (threshold 30k, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(50, 80))
        m = random.choice(merchants_by_cat["HONEYMOON_TRAVEL"])
        amt = round(random.uniform(32000.0, 58000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "HONEYMOON_TRAVEL", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Formal Wear (binary, weight 10)
        t_date = trigger_start_date + timedelta(days=random.randint(30, 75))
        m = random.choice(merchants_by_cat["FORMAL_WEAR"])
        amt = round(random.uniform(6000.0, 20000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "FORMAL_WEAR", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1

    # 4. NEW CHILD COHORT
    for c in cohort_baby:
        cid = c["customer_id"]
        # Trigger Maternity Hospital bill (binary, weight 35)
        t_date = trigger_start_date + timedelta(days=random.randint(20, 50))
        m = random.choice(merchants_by_cat["MATERNITY_HOSPITAL"])
        amt = round(random.uniform(35000.0, 75000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "MATERNITY_HOSPITAL", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1
        
        # Trigger Baby Products Spend (threshold 15k, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(45, 80))
        m = random.choice(merchants_by_cat["BABY_PRODUCTS"])
        amt = round(random.uniform(16000.0, 25000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "BABY_PRODUCTS", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Pharmacy Spikes (binary, weight 20)
        for d in range(5):
            t_date = trigger_start_date + timedelta(days=random.randint(30, 85))
            m = random.choice(merchants_by_cat["PHARMACY"])
            amt = round(random.uniform(1500.0, 4500.0), 2)
            transactions.append([txn_id_counter, cid, m["merchant_id"], "PHARMACY", amt, t_date.strftime("%Y-%m-%d"), c["city"], "contactless", "completed"])
            txn_id_counter += 1
            
        # Trigger Pediatric Clinic Visits (binary, weight 10)
        t_date = trigger_start_date + timedelta(days=random.randint(60, 88))
        m = random.choice(merchants_by_cat["PEDIATRIC_CLINICS"])
        amt = round(random.uniform(1500.0, 4000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "PEDIATRIC_CLINICS", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1

    # 5. HIGHER EDUCATION COHORT
    for c in cohort_educ:
        cid = c["customer_id"]
        # Trigger University fee payment (binary, weight 35)
        t_date = trigger_start_date + timedelta(days=random.randint(40, 75))
        m = random.choice(merchants_by_cat["UNIVERSITY_FEES"])
        amt = round(random.uniform(60000.0, 180000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "UNIVERSITY_FEES", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Test Prep (threshold 10k, weight 25)
        t_date = trigger_start_date + timedelta(days=random.randint(5, 45))
        m = random.choice(merchants_by_cat["TEST_PREP"])
        amt = round(random.uniform(11000.0, 19000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "TEST_PREP", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Student Housing deposit (binary, weight 20)
        t_date = trigger_start_date + timedelta(days=random.randint(60, 85))
        m = random.choice(merchants_by_cat["STUDENT_HOUSING"])
        amt = round(random.uniform(15000.0, 25000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "STUDENT_HOUSING", amt, t_date.strftime("%Y-%m-%d"), c["city"], "online", "completed"])
        txn_id_counter += 1
        
        # Trigger Stationery/Laptop purchase (binary, weight 10)
        t_date = trigger_start_date + timedelta(days=random.randint(45, 80))
        m = random.choice(merchants_by_cat["STATIONERY_LAPTOPS"])
        amt = round(random.uniform(45000.0, 75000.0), 2)
        transactions.append([txn_id_counter, cid, m["merchant_id"], "STATIONERY_LAPTOPS", amt, t_date.strftime("%Y-%m-%d"), c["city"], "in_store", "completed"])
        txn_id_counter += 1

    # -------------------------------------------------------------------------
    # Inject raw transaction anomalies (~1% of transaction records)
    # -------------------------------------------------------------------------
    total_injected = 0
    anomaly_indices = random.sample(range(len(transactions)), int(len(transactions) * 0.015))
    
    for idx in anomaly_indices:
        anomaly_type = random.choice(["negative_spend", "future_date", "invalid_cat", "mismatch_date", "duplicate"])
        
        if anomaly_type == "negative_spend":
            transactions[idx][4] = -1 * abs(transactions[idx][4])
            total_injected += 1
        elif anomaly_type == "future_date":
            f_date = datetime.now() + timedelta(days=random.randint(10, 45))
            transactions[idx][5] = f_date.strftime("%Y-%m-%d")
            total_injected += 1
        elif anomaly_type == "invalid_cat":
            transactions[idx][3] = "UNKNOWN_RETAIL_ANOMALY"
            total_injected += 1
        elif anomaly_type == "mismatch_date":
            # Convert YYYY-MM-DD -> DD/MM/YYYY
            dt_obj = datetime.strptime(transactions[idx][5], "%Y-%m-%d")
            transactions[idx][5] = dt_obj.strftime("%d/%m/%Y")
            total_injected += 1
        elif anomaly_type == "duplicate":
            # Duplicate the row and append it (using same transaction details)
            dupe_row = list(transactions[idx])
            transactions.append(dupe_row)
            total_injected += 1
            
    print(f"Injected {total_injected} transaction anomalies.")
    
    # Save transactions
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["txn_id", "customer_id", "merchant_id", "merchant_category", "amount", "txn_date", "txn_city", "channel", "status"])
        writer.writerows(transactions)
        
    print(f"Generated {path} with {len(transactions)} rows.")
    
    # Write a small sample for test verification
    sample_path = os.path.join(DATA_DIR, "sample_transactions.csv")
    with open(sample_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["txn_id", "customer_id", "merchant_id", "merchant_category", "amount", "txn_date", "txn_city", "channel", "status"])
        writer.writerows(transactions[:1000])
    print(f"Generated sample file {sample_path}")

# -------------------------------------------------------------------------
# Engagement Simulation
# -------------------------------------------------------------------------
def generate_engagement(customers: List[Dict[str, Any]]) -> None:
    """Simulates 12 months of multi-channel engagement events across four tables.

    Args:
        customers: List of simulated customer dictionaries.
    """
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    
    active_customers = [c for c in customers if c["opted_out"] == 0]
    
    views: List[List[Any]] = []
    opens: List[List[Any]] = []
    redemptions: List[List[Any]] = []
    clicks: List[List[Any]] = []
    
    view_id = 20000001
    open_id = 30000001
    red_id = 40000001
    click_id = 50000001
    
    campaign_cats = ["home", "travel", "lifestyle", "rewards", "education"]
    devices = ["mobile", "desktop", "tablet"]
    channels = ["email", "app", "web", "sms"]
    
    # Setup bias: customers in life-event cohorts interact highly with related campaigns
    cohort_mapping = {
        "home": range(1, 51),        # home purchase
        "travel": range(51, 101),     # relocation
        "lifestyle": range(101, 151),  # marriage
        "rewards": range(151, 201),    # new child
        "education": range(201, 251)   # higher education
    }

    # Generate records
    for c in active_customers:
        cid = c["customer_id"]
        
        # Decide if this customer is highly responsive
        is_responsive = False
        fav_cat = None
        for cat, cid_range in cohort_mapping.items():
            if cid in cid_range:
                is_responsive = True
                fav_cat = cat
                break
                
        # Generate impressions and actions (views & clicks)
        # 10 to 20 views per customer across 12 months
        num_views = np.random.randint(12, 22) if is_responsive else np.random.randint(3, 10)
        
        for _ in range(num_views):
            # Recency bias: concentrate 60% of events in the last 90 days
            if np.random.rand() < 0.60:
                days_offset = np.random.randint(0, 90)
                event_time = end_date - timedelta(days=days_offset)
            else:
                days_offset = np.random.randint(90, 365)
                event_time = end_date - timedelta(days=days_offset)
                
            cat = fav_cat if (is_responsive and np.random.rand() < 0.70) else random.choice(campaign_cats)
            channel = random.choice(channels)
            offer_id = f"OFFER_{cat.upper()}_{random.randint(100, 999)}"
            
            # Click probability
            click_prob = 0.45 if (is_responsive and cat == fav_cat) else 0.08
            was_clicked = 1 if np.random.rand() < click_prob else 0
            
            # Type anomaly injection on clicked field (some string, some numeric)
            was_clicked_val: Any = was_clicked
            if np.random.rand() < 0.05:
                was_clicked_val = "True" if was_clicked == 1 else "False"
                
            views.append([
                view_id, cid, offer_id, cat, channel,
                event_time.strftime("%Y-%m-%d %H:%M:%S"),
                was_clicked_val, f"placement_{random.randint(1, 4)}"
            ])
            
            # If viewed by email, simulate open rate
            if channel == "email":
                open_prob = 0.75 if (is_responsive and cat == fav_cat) else 0.25
                if np.random.rand() < open_prob:
                    # Open happens shortly after view
                    open_time = event_time + timedelta(minutes=random.randint(1, 180))
                    opens.append([
                        open_id, cid, f"CAMP_{cat.upper()}", cat,
                        open_time.strftime("%Y-%m-%d %H:%M:%S"),
                        random.choice(devices)
                    ])
                    open_id += 1
                    
            # If clicked, record campaign click event
            if was_clicked == 1:
                click_time = event_time + timedelta(seconds=random.randint(5, 600))
                clicks.append([
                    click_id, cid, f"CAMP_{cat.upper()}", cat, channel,
                    click_time.strftime("%Y-%m-%d %H:%M:%S")
                ])
                click_id += 1
                
            view_id += 1
            
        # Generate point redemptions
        # 1 to 5 redemptions per customer across 12 months
        num_reds = np.random.randint(1, 6)
        for _ in range(num_reds):
            days_offset = np.random.randint(0, 365)
            event_time = end_date - timedelta(days=days_offset)
            points = int(np.random.choice([2000, 5000, 10000, 25000], p=[0.5, 0.3, 0.15, 0.05]))
            dollar_val = round(points * 0.007, 2)  # value in dollars
            
            red_cat = "shopping"
            if fav_cat == "travel":
                red_cat = "travel"
            elif fav_cat == "lifestyle":
                red_cat = "dining"
                
            redemptions.append([
                red_id, cid, points, red_cat,
                event_time.strftime("%Y-%m-%d %H:%M:%S"),
                dollar_val
            ])
            red_id += 1

    # Save outputs
    # 1. Offer Views
    path_views = os.path.join(DATA_DIR, "offer_views_raw.csv")
    with open(path_views, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["view_id", "customer_id", "offer_id", "offer_category", "channel", "viewed_at", "was_clicked", "placement_id"])
        writer.writerows(views)
        
    # 2. Email Opens
    path_opens = os.path.join(DATA_DIR, "email_opens_raw.csv")
    with open(path_opens, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["open_id", "customer_id", "campaign_id", "offer_category", "opened_at", "device_type"])
        writer.writerows(opens)
        
    # 3. Reward Redemptions
    path_reds = os.path.join(DATA_DIR, "reward_redemptions_raw.csv")
    with open(path_reds, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["redemption_id", "customer_id", "points_redeemed", "redemption_category", "redeemed_at", "dollar_value"])
        writer.writerows(redemptions)
        
    # 4. Campaign Clicks
    path_clicks = os.path.join(DATA_DIR, "campaign_clicks_raw.csv")
    with open(path_clicks, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["click_id", "customer_id", "campaign_id", "offer_category", "channel", "clicked_at"])
        writer.writerows(clicks)
        
    print(f"Generated engagement CSV files in {DATA_DIR}.")
    
    # Save a combined engagement sample file (representing a click logs view or similar subset)
    sample_path = os.path.join(DATA_DIR, "sample_engagement.csv")
    with open(sample_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "customer_id", "offer_category", "channel", "event_type", "occurred_at"])
        # Take a subset of views to act as sample_engagement rows
        for v in views[:500]:
            writer.writerow([v[0], v[1], v[3], v[4], "view", v[5]])
    print(f"Generated sample file {sample_path}")

# -------------------------------------------------------------------------
# Main Execution Entry
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting synthetic data generation...")
    generate_merchant_categories()
    cust = generate_customers(1000)
    merch = generate_merchants(200)
    generate_transactions(cust, merch, 50000)
    generate_engagement(cust)
    print("Data generation complete!")
