# scoring/scoring_config.py
"""Central Scoring and Target Configuration for FinSight.

Contains all mathematical weights, spend scaling thresholds, and minimum score
boundaries to isolate calculations from hardcoded configurations.
"""

from typing import Dict, Any, List

# Minimum score required to trigger targeted campaign action per life event
THRESHOLDS: Dict[str, float] = {
    "home_purchase": 70.0,
    "relocation": 65.0,
    "marriage": 60.0,
    "new_child": 60.0,
    "higher_education": 55.0
}

# 1. Home Purchase weights and limits
HOME_CONFIG: Dict[str, Any] = {
    "furniture_weight": 30.0,
    "furniture_threshold": 50000.0,
    "appliance_weight": 25.0,
    "appliance_threshold": 30000.0,
    "real_estate_weight": 20.0,
    "insurance_weight": 15.0,
    "growth_weight": 10.0
}

# 2. Relocation weights and limits
RELOCATION_CONFIG: Dict[str, Any] = {
    "moving_weight": 35.0,
    "moving_threshold": 20000.0,
    "utility_weight": 25.0,
    "hotel_weight": 20.0,
    "forex_weight": 10.0,
    "growth_weight": 10.0
}

# 3. Marriage weights and limits
MARRIAGE_CONFIG: Dict[str, Any] = {
    "jewelry_weight": 30.0,
    "jewelry_threshold": 40000.0,
    "venue_weight": 25.0,
    "venue_threshold": 50000.0,
    "travel_weight": 25.0,
    "travel_threshold": 30000.0,
    "formal_weight": 10.0,
    "growth_weight": 10.0
}

# 4. New Child weights and limits
CHILD_CONFIG: Dict[str, Any] = {
    "hospital_weight": 35.0,
    "baby_weight": 25.0,
    "baby_threshold": 15000.0,
    "pharmacy_weight": 20.0,
    "clinic_weight": 10.0,
    "growth_weight": 10.0
}

# 5. Higher Education weights and limits
EDUCATION_CONFIG: Dict[str, Any] = {
    "fee_weight": 35.0,
    "test_weight": 25.0,
    "test_threshold": 10000.0,
    "housing_weight": 20.0,
    "laptop_weight": 10.0,
    "growth_weight": 10.0
}

# Card recommended product mapping based on top event
RECOMMENDED_PRODUCTS: Dict[str, str] = {
    "home_purchase": "Elite tier Card & Home Loan Referral",
    "relocation": "Explorer Travel Card & Lounge Access Package",
    "marriage": "Premium Rewards Card & Luxury Partners Pack",
    "new_child": "Cashback Essentials Card & Family Benefits Plan",
    "higher_education": "Student Cashback Card & Education Loan Referral"
}

# Tie-breaking business priority order (highest to lowest CLV/relevance)
BUSINESS_PRIORITY: List[str] = [
    "home_purchase",
    "new_child",
    "marriage",
    "relocation",
    "higher_education"
]

# ============================================================
# DB Connection Settings
# ============================================================
import os
DB_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "db_user"),
    "password": os.getenv("DB_PASSWORD", "db_password"),
    "database": os.getenv("DB_NAME", "finsight_db")
}

# ============================================================
# RFM Segment Map
# ============================================================
RFM_SEGMENT_MAP: Dict[str, str] = {
    'Champions':          'Best customers',
    'Loyal':              'High frequency',
    'Potential Loyalist': 'Recent, grow frequency',
    'New Customer':       'Just joined',
    'Promising':          'Above average',
    'At Risk':            'Was good, fading',
    'Cannot Lose':        'High value, gone',
    'Hibernating':        'Low engagement',
    'Lost':               'Churned'
}

# ============================================================
# RFM Weight Map
# Used by priority_index.py to convert segment names to weights
# ============================================================
RFM_WEIGHT_MAP = {
    'Champions':          1.50,  # Best customers — highest multiplier
    'Loyal':              1.35,  # High value, consistent
    'Cannot Lose':        1.40,  # High past value, currently fading
    'Potential Loyalist': 1.20,  # Growing relationship
    'At Risk':            1.10,  # Worth recovering
    'Promising':          1.05,  # Above average
    'New Customer':       1.00,  # Neutral — insufficient history
    'Hibernating':        0.85,  # Low engagement penalty
    'Lost':               0.70,  # Lowest weight — unlikely to convert
}

# ============================================================
# Velocity Weight Bounds
# ============================================================
VELOCITY_MAX_MULTIPLIER = 1.50
VELOCITY_MIN_MULTIPLIER = 0.50

# ============================================================
# Priority Index Action Tiers
# ============================================================
PRIORITY_TIERS = {
    'IMMEDIATE': (75, 100),   # Top priority — act within 24 hours
    'HIGH':      (50, 75),    # High priority — act within 7 days
    'MEDIUM':    (25, 50),    # Medium — include in next campaign
    'LOW':       (0,  25),    # Low — monitor, no immediate action
}

