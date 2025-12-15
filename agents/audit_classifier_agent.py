# AuditClassifierAgent
# Reviews the available dataset and classifies the audit type.
# Uses the 'category' column from RatedData - NO LLM needed.

from typing import Dict, Any, Optional


class AuditClassifierAgent:
    """
    Agent responsible for classifying the audit type based on the category field in RatedData.
    This is a simple rule-based classifier - no LLM required.
    """
    
    # Actual categories from the rated_data table (from database)
    KNOWN_CATEGORIES = {
        # Discount audits
        "BASE_DISCOUNTS_PERCENTAGE_AUDIT": "Base Discount Percentage Audit",
        "DISCOUNTS_PERCENTAGE_AUDIT": "Discount Percentage Audit",
        "EARNED_DISCOUNTS_PERCENTAGE_AUDIT": "Earned Discount Percentage Audit",
        
        # Weight audit
        "BILL_WEIGHT_AUDIT": "Bill Weight Audit",
        
        # Rate audits
        "LIST_RATE_AUDIT": "List Rate Audit",
        "LIST_RATE_NULL_AUDIT": "List Rate Null Audit",
        "MWT_LIST_RATE_AUDIT": "Multi-Weight List Rate Audit",
        
        # Transportation audit
        "NET_TRANSPORTATION_AUDIT": "Net Transportation Audit",
        
        # Surcharge audits
        "SURCHARGE_AUDIT": "Surcharge Audit",
        "SURCHARGE_APPLICABILITY_AUDIT": "Surcharge Applicability Audit",
        "SURCHARGE_NULL_AUDIT": "Surcharge Null Audit",
        
        # Fuel audit
        "FUEL_SURCHARGE_AUDIT": "Fuel Surcharge Audit",
        
        # Status categories
        "Matched": "Matched - No Discrepancy",
        "EXCEPTION": "Exception",
    }
    
    # Group categories by audit type for reasoning
    CATEGORY_GROUPS = {
        "DISCOUNT": [
            "BASE_DISCOUNTS_PERCENTAGE_AUDIT",
            "DISCOUNTS_PERCENTAGE_AUDIT", 
            "EARNED_DISCOUNTS_PERCENTAGE_AUDIT"
        ],
        "WEIGHT": [
            "BILL_WEIGHT_AUDIT"
        ],
        "RATE": [
            "LIST_RATE_AUDIT",
            "LIST_RATE_NULL_AUDIT",
            "MWT_LIST_RATE_AUDIT"
        ],
        "TRANSPORTATION": [
            "NET_TRANSPORTATION_AUDIT"
        ],
        "SURCHARGE": [
            "SURCHARGE_AUDIT",
            "SURCHARGE_APPLICABILITY_AUDIT",
            "SURCHARGE_NULL_AUDIT",
            "FUEL_SURCHARGE_AUDIT"
        ],
        "NO_AUDIT": [
            "Matched"
        ],
        "ERROR": [
            "EXCEPTION"
        ]
    }
    
    def __init__(self):
        pass
    
    def classify(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the audit type based on the 'category' field in rated_data.
        
        Args:
            state: Current graph state with rated_data containing 'category'
            
        Returns:
            Updated state with audit_type, audit_category, and classification_confidence
        """
        rated_data = state.get("rated_data", {})
        
        # Get the category from rated data
        category = None
        if isinstance(rated_data, dict):
            category = rated_data.get("category")
        
        if not category:
            # Try to infer category from other fields if category is missing/NULL
            category = self._infer_category(rated_data)
        
        # Normalize category (handle case variations)
        normalized_category = self._normalize_category(category)
        
        # Get description
        category_description = self.KNOWN_CATEGORIES.get(
            normalized_category, 
            f"Unknown: {category}"
        )
        
        # Get the group this category belongs to
        audit_group = self._get_category_group(normalized_category)
        
        # Calculate confidence based on whether we found a known category
        confidence = 1.0 if normalized_category in self.KNOWN_CATEGORIES else 0.5
        
        return {
            "audit_type": normalized_category,
            "audit_category": category_description,
            "audit_group": audit_group,
            "classification_confidence": confidence,
        }
    
    def _normalize_category(self, category: Optional[str]) -> str:
        """Normalize the category string to match known categories."""
        if not category:
            return "UNKNOWN"
        
        category = category.strip()
        
        # Direct match (case-sensitive since DB values are specific)
        if category in self.KNOWN_CATEGORIES:
            return category
        
        # Try uppercase match
        upper_category = category.upper()
        for known in self.KNOWN_CATEGORIES.keys():
            if known.upper() == upper_category:
                return known
        
        return category  # Return original if no mapping found
    
    def _get_category_group(self, category: str) -> str:
        """Get the group that this category belongs to."""
        for group, categories in self.CATEGORY_GROUPS.items():
            if category in categories:
                return group
        return "UNKNOWN"
    
    def _infer_category(self, rated_data: Dict[str, Any]) -> str:
        """
        Infer audit category from rated_data fields when category is NULL.
        Compares carrier vs calc values to determine discrepancy type.
        """
        if not rated_data:
            return "UNKNOWN"
        
        # Check for weight discrepancy
        carrier_bill_weight = rated_data.get("carrierBillWeight", 0) or 0
        calc_bill_weight = rated_data.get("calcBillWeight", 0) or 0
        if float(carrier_bill_weight) != float(calc_bill_weight):
            return "BILL_WEIGHT_AUDIT"
        
        # Check for list rate discrepancy
        carrier_list_rate = rated_data.get("carrierListRate", 0) or 0
        calc_list_rate = rated_data.get("calcListRate", 0) or 0
        if carrier_list_rate and calc_list_rate:
            if float(carrier_list_rate) != float(calc_list_rate):
                return "LIST_RATE_AUDIT"
        elif carrier_list_rate and not calc_list_rate:
            return "LIST_RATE_NULL_AUDIT"
        
        # Check for discount discrepancy
        carrier_discount = rated_data.get("carrierTotalDiscountPercentage", 0) or 0
        calc_discount = rated_data.get("calcTotalDiscountPercentage", 0) or 0
        if float(carrier_discount) != float(calc_discount):
            # Determine which type of discount
            carrier_base = rated_data.get("carrierBaseDiscountEffectivePercentage", 0) or 0
            calc_base = rated_data.get("calcBaseDiscountEffectivePercentage", 0) or 0
            if float(carrier_base) != float(calc_base):
                return "BASE_DISCOUNTS_PERCENTAGE_AUDIT"
            
            carrier_earned = rated_data.get("carrierEarnedDiscountEffectivePercentage", 0) or 0
            calc_earned = rated_data.get("calcEarnedDiscountEffectivePercentage", 0) or 0
            if float(carrier_earned) != float(calc_earned):
                return "EARNED_DISCOUNTS_PERCENTAGE_AUDIT"
            
            return "DISCOUNTS_PERCENTAGE_AUDIT"
        
        # Check for surcharge discrepancy
        carrier_surcharges = rated_data.get("carrierTotalSurcharges", 0) or 0
        calc_surcharges = rated_data.get("calcTotalSurcharges", 0) or 0
        if float(carrier_surcharges) != float(calc_surcharges):
            # Check fuel specifically
            carrier_fuel = rated_data.get("carrierTransportationFuelAmount", 0) or 0
            calc_fuel = rated_data.get("calcTransportationFuelAmount", 0) or 0
            if float(carrier_fuel) != float(calc_fuel):
                return "FUEL_SURCHARGE_AUDIT"
            return "SURCHARGE_AUDIT"
        
        # Check for net transportation discrepancy
        carrier_net_trans = rated_data.get("carrierNetTransportationCharge", 0) or 0
        calc_net_trans = rated_data.get("calcNetTransportationCharge", 0) or 0
        if float(carrier_net_trans) != float(calc_net_trans):
            return "NET_TRANSPORTATION_AUDIT"
        
        # Check if charges match
        carrier_net = rated_data.get("carrierTotalNetCharge", 0) or 0
        calc_net = rated_data.get("calcTotalNetCharge", 0) or 0
        if float(carrier_net) == float(calc_net):
            return "Matched"
        
        # Check over_rated flag
        if rated_data.get("overRated"):
            return "EXCEPTION"
        
        return "UNKNOWN"


def classify_audit(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node function for the LangGraph workflow.
    Classifies the audit type based on category in rated_data.
    """
    from utils.logger import log_node_start, log_node_end, logger
    
    log_node_start("classify_audit")
    
    agent = AuditClassifierAgent()
    result = agent.classify(state)
    
    logger.info(f"🏷️  Audit Type: {result.get('audit_type')}")
    logger.info(f"🏷️  Audit Category: {result.get('audit_category')}")
    logger.info(f"🏷️  Confidence: {result.get('classification_confidence', 0):.0%}")
    
    log_node_end("classify_audit", result)
    return result

