from enum import Enum
from typing import Optional, Dict, Any

class LeadTier(str, Enum):
    TIER_1 = "Tier 1 (Instant Priority)"
    TIER_2 = "Tier 2 (Follow-up)"
    TIER_3 = "Tier 3 (Nurture)"

def calculate_usage_from_sqft(sqft: float, segment: str) -> float:
    """
    Estimates annual MWh usage based on square footage.
    Multipliers: Industrial ~ 0.15 MWh/sqft, Commercial ~ 0.08 MWh/sqft
    """
    if not sqft:
        return 0
    
    multiplier = 0.15 if segment == "Industrial" else 0.08
    return round(sqft * multiplier, 2)

def evaluate_lead_tier(data: Dict[str, Any]) -> LeadTier:
    segment = str(data.get("business_segment", "")).lower()
    usage = data.get("annual_usage_mwh")
    sq_ft = data.get("square_footage")
    contract_status = str(data.get("contract_status", "")).lower().replace(" ", "").replace("-", "")
    expiry_months = data.get("months_to_expiry")
    building_age = data.get("building_age")
    has_provider = data.get("has_current_provider", True)

    if usage is None and sq_ft is not None:
        usage = calculate_usage_from_sqft(sq_ft, segment)

    if not has_provider:
        return LeadTier.TIER_1

    if segment == "industrial":
        if usage and usage > 500 and (expiry_months is not None and expiry_months < 6):
            return LeadTier.TIER_1
        if usage and 100 <= usage <= 500 and (expiry_months is not None and expiry_months < 12) and (building_age is not None and building_age < 5):
            return LeadTier.TIER_2

    if segment == "commercial":
        if usage and usage > 50 and (expiry_months == 0 or contract_status == "monthtomonth"):
            return LeadTier.TIER_1
        if usage and 20 <= usage <= 50 and (building_age is not None and building_age < 2):
            return LeadTier.TIER_3

    return LeadTier.TIER_3