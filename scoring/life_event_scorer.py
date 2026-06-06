# scoring/life_event_scorer.py
"""Scoring Engine Rules for FinSight.

Calculates the base transaction signal score (0 to 100) for all 5 life events
using pre-aggregated customer features and configurable weights.
"""

from typing import Dict, Any
from scoring.scoring_config import (
    HOME_CONFIG,
    RELOCATION_CONFIG,
    MARRIAGE_CONFIG,
    CHILD_CONFIG,
    EDUCATION_CONFIG
)

def compute_home_score(features: Dict[str, Any]) -> float:
    """Calculates the probability score for the Home Purchase event.

    Args:
        features: Dictionary of pre-aggregated customer features.

    Returns:
        A score float between 0.0 and 100.0.
    """
    cfg = HOME_CONFIG
    score = 0.0

    # 1. Furniture spend (spend-scaled, weight 30)
    furniture_spend = float(features.get("furniture_spend_90d", 0.0))
    score += min(furniture_spend / cfg["furniture_threshold"], 1.0) * cfg["furniture_weight"]

    # 2. Appliance spend (spend-scaled, weight 25)
    appliance_spend = float(features.get("appliance_spend_90d", 0.0))
    score += min(appliance_spend / cfg["appliance_threshold"], 1.0) * cfg["appliance_weight"]

    # 3. Real estate portal visits (frequency, weight 20)
    visits = int(features.get("real_estate_visits_90d", 0))
    if visits >= 2:
        score += cfg["real_estate_weight"]
    elif visits == 1:
        score += cfg["real_estate_weight"] / 2.0

    # 4. Home insurance payment (binary, weight 15)
    insurance = int(features.get("insurance_payment_flag", 0))
    score += (1.0 if insurance > 0 else 0.0) * cfg["insurance_weight"]

    # 5. Spend growth rate bonus (weight 10)
    growth = float(features.get("spend_growth_3m", 0.0))
    if growth > 0.30:
        score += cfg["growth_weight"]

    return min(score, 100.0)

def compute_relocation_score(features: Dict[str, Any]) -> float:
    """Calculates the probability score for the Relocation event.

    Args:
        features: Dictionary of pre-aggregated customer features.

    Returns:
        A score float between 0.0 and 100.0.
    """
    cfg = RELOCATION_CONFIG
    score = 0.0

    # 1. Moving company spend (spend-scaled, weight 35)
    moving_spend = float(features.get("moving_spend_90d", 0.0))
    score += min(moving_spend / cfg["moving_threshold"], 1.0) * cfg["moving_weight"]

    # 2. New city utility setup (binary, weight 25)
    utility = int(features.get("new_city_utility_flag", 0))
    score += (1.0 if utility > 0 else 0.0) * cfg["utility_weight"]

    # 3. Stays/Travel City Diversity (weight 30, combining hotel and forex weights)
    # 3+ distinct cities = full 30 points; 2 distinct cities = 15 points
    cities = int(features.get("distinct_cities_90d", 1))
    if cities >= 3:
        score += cfg["hotel_weight"] + cfg["forex_weight"]
    elif cities == 2:
        score += (cfg["hotel_weight"] + cfg["forex_weight"]) / 2.0

    # 4. Spend growth rate bonus (weight 10)
    growth = float(features.get("spend_growth_3m", 0.0))
    if growth > 0.30:
        score += cfg["growth_weight"]

    return min(score, 100.0)

def compute_marriage_score(features: Dict[str, Any]) -> float:
    """Calculates the probability score for the Marriage event.

    Args:
        features: Dictionary of pre-aggregated customer features.

    Returns:
        A score float between 0.0 and 100.0.
    """
    cfg = MARRIAGE_CONFIG
    score = 0.0

    # 1. Jewelry spend (spend-scaled, weight 30)
    jewelry_spend = float(features.get("jewelry_spend_90d", 0.0))
    score += min(jewelry_spend / cfg["jewelry_threshold"], 1.0) * cfg["jewelry_weight"]

    # 2. Wedding venue booking and catering (spend-scaled, weight 60, combining venue/travel/formal)
    wedding_spend = float(features.get("wedding_spend_90d", 0.0))
    combined_wedding_threshold = cfg["venue_threshold"] + cfg["travel_threshold"]
    combined_wedding_weight = cfg["venue_weight"] + cfg["travel_weight"] + cfg["formal_weight"]
    
    score += min(wedding_spend / combined_wedding_threshold, 1.0) * combined_wedding_weight

    # 3. Spend growth rate bonus (weight 10)
    growth = float(features.get("spend_growth_3m", 0.0))
    if growth > 0.30:
        score += cfg["growth_weight"]

    return min(score, 100.0)

def compute_child_score(features: Dict[str, Any]) -> float:
    """Calculates the probability score for the New Child event.

    Args:
        features: Dictionary of pre-aggregated customer features.

    Returns:
        A score float between 0.0 and 100.0.
    """
    cfg = CHILD_CONFIG
    score = 0.0

    # 1. Maternity hospital bills (binary, weight 35)
    hospital = int(features.get("hospital_payment_flag", 0))
    score += (1.0 if hospital > 0 else 0.0) * cfg["hospital_weight"]

    # 2. Baby products spend (spend-scaled, weight 25)
    baby_spend = float(features.get("baby_product_spend_30d", 0.0))
    score += min(baby_spend / cfg["baby_threshold"], 1.0) * cfg["baby_weight"]

    # 3. Pharmacy spike and clinic visits (binary, weight 30, combining pharmacy/clinic)
    pharmacy_spike = int(features.get("pharmacy_spend_spike", 0))
    combined_pharmacy_weight = cfg["pharmacy_weight"] + cfg["clinic_weight"]
    score += (1.0 if pharmacy_spike > 0 else 0.0) * combined_pharmacy_weight

    # 4. Spend growth rate bonus (weight 10)
    growth = float(features.get("spend_growth_3m", 0.0))
    if growth > 0.30:
        score += cfg["growth_weight"]

    return min(score, 100.0)

def compute_edu_score(features: Dict[str, Any]) -> float:
    """Calculates the probability score for the Higher Education event.

    Args:
        features: Dictionary of pre-aggregated customer features.

    Returns:
        A score float between 0.0 and 100.0.
    """
    cfg = EDUCATION_CONFIG
    score = 0.0

    # 1. University fee payment and housing deposits (binary, weight 65, combining fee/housing)
    fee = int(features.get("university_fee_flag", 0))
    combined_fee_weight = cfg["fee_weight"] + cfg["housing_weight"] + cfg["laptop_weight"]
    score += (1.0 if fee > 0 else 0.0) * combined_fee_weight

    # 2. Test prep spend (spend-scaled, weight 25)
    test_prep = float(features.get("test_prep_spend_90d", 0.0))
    score += min(test_prep / cfg["test_threshold"], 1.0) * cfg["test_weight"]

    # 3. Spend growth rate bonus (weight 10)
    growth = float(features.get("spend_growth_3m", 0.0))
    if growth > 0.30:
        score += cfg["growth_weight"]

    return min(score, 100.0)
