# AuditReasoningAgent
# Attempts to determine the audit cause using rules, examples, and the classified type.
# Output may be:
#   - `sufficient` → proceed
#   - `insufficient` → missing fields list returned to Orchestrator

import json
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.append('..')

from prompts.prompts import REASONING_SYSTEM_PROMPT, REASONING_USER_PROMPT, BILL_WEIGHT_AUDIT_PROMPT
from config import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE


class AuditReasoningAgent:
    """
    Agent responsible for determining the audit cause and checking data sufficiency.
    Uses LLM to analyze the discrepancy and explain the root cause.
    """
    
    # Required fields by audit category (from actual database categories)
    # Field names are in camelCase to match Spring Boot JSON response
    REQUIRED_FIELDS = {
        # Weight audit
        "BILL_WEIGHT_AUDIT": [
            "carrierBillWeight", "calcBillWeight", "actualWeight"
        ],
        
        # Discount audits
        "BASE_DISCOUNTS_PERCENTAGE_AUDIT": [
            "carrierBaseDiscountEffectivePercentage", 
            "calcBaseDiscountEffectivePercentage",
            "baseDiscountPercentage"
        ],
        "DISCOUNTS_PERCENTAGE_AUDIT": [
            "carrierTotalDiscountPercentage", 
            "calcTotalDiscountPercentage"
        ],
        "EARNED_DISCOUNTS_PERCENTAGE_AUDIT": [
            "carrierEarnedDiscountEffectivePercentage",
            "calcEarnedDiscountEffectivePercentage",
            "earnedDiscountPercentage"
        ],
        
        # Rate audits
        "LIST_RATE_AUDIT": [
            "carrierListRate", "calcListRate"
        ],
        "LIST_RATE_NULL_AUDIT": [
            "carrierListRate"
        ],
        "MWT_LIST_RATE_AUDIT": [
            "carrierListRate", "calcListRate",
            "isCarrierMultiweight", "isCalcMultiweight"
        ],
        
        # Transportation audit
        "NET_TRANSPORTATION_AUDIT": [
            "carrierNetTransportationCharge", 
            "calcNetTransportationCharge"
        ],
        
        # Surcharge audits
        "SURCHARGE_AUDIT": [
            "carrierTotalSurcharges", "calcTotalSurcharges"
        ],
        "SURCHARGE_APPLICABILITY_AUDIT": [
            "carrierTotalSurcharges", "calcTotalSurcharges"
        ],
        "SURCHARGE_NULL_AUDIT": [
            "carrierTotalSurcharges"
        ],
        "FUEL_SURCHARGE_AUDIT": [
            "fuelPercentage",
            "carrierTransportationFuelAmount",
            "calcTransportationFuelAmount"
        ],
        
        # Status categories
        "Matched": [],  # No fields needed for matched
        "EXCEPTION": [],
    }
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=LLM_TEMPERATURE
        )
    
    def reason(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the audit and determine if data is sufficient.
        
        Args:
            state: Current graph state with all available data
            
        Returns:
            Updated state with reasoning_status, reasoning_result, missing_fields, audit_cause, error_case
        """
        audit_type = state.get("audit_type", "UNKNOWN")
        rated_data = state.get("rated_data", {}) or {}
        parcel_data = state.get("parcel_characteristics", {}) or {}
        
        # Handle "Matched" case - no audit needed
        if audit_type == "Matched":
            return {
                "reasoning_status": "sufficient",
                "reasoning_result": "No discrepancy found. Carrier charges match calculated charges.",
                "missing_fields": [],
                "audit_cause": "Matched - No audit required. Carrier charges are correct.",
                "error_case": "Case 4: No Error - Calculation Correct"
            }
        
        # Handle "EXCEPTION" case
        if audit_type == "EXCEPTION":
            message = rated_data.get("message", "Exception occurred during rating")
            return {
                "reasoning_status": "sufficient",
                "reasoning_result": f"Exception: {message}",
                "missing_fields": [],
                "audit_cause": f"Rating exception: {message}",
                "error_case": "Exception"
            }
        
        # First check if we have sufficient data
        missing_fields = self._check_required_fields(audit_type, rated_data, parcel_data)
        
        if missing_fields:
            return {
                "reasoning_status": "insufficient",
                "reasoning_result": f"Missing required fields for {audit_type}",
                "missing_fields": missing_fields,
                "audit_cause": None,
                "error_case": "Case 3: Improperly Populated Parcel Characteristic (Possible - need invoice details)"
            }
        
        # Let LLM analyze and generate the case
        cause, llm_case = self._analyze_discrepancy_with_case(audit_type, rated_data, parcel_data, state)
        
        # LLM MUST generate a case - the prompt is designed to always return error_case
        final_case = llm_case or f"Case: {audit_type} - Analysis Complete"
        
        return {
            "reasoning_status": "sufficient",
            "reasoning_result": cause,
            "missing_fields": [],
            "audit_cause": cause,
            "error_case": final_case
        }
    
    
    def _check_required_fields(
        self, 
        audit_type: str, 
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> List[str]:
        """Check if all required fields are present for the audit type."""
        required = self.REQUIRED_FIELDS.get(audit_type, [])
        combined_data = {**parcel_data, **rated_data}
        
        missing = []
        for field in required:
            value = combined_data.get(field)
            if value is None:
                missing.append(field)
        
        return missing
    
    def _analyze_discrepancy(
        self,
        audit_type: str,
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any],
        state: Dict[str, Any]
    ) -> str:
        """Use LLM to analyze the discrepancy and generate explanation."""
        # Prepare focused data for LLM
        relevant_data = self._extract_relevant_data(audit_type, rated_data, parcel_data)
        
        # Use specialized prompt for BILL_WEIGHT_AUDIT
        if audit_type == "BILL_WEIGHT_AUDIT":
            from utils.logger import logger
            logger.info("🎯 Using BILL_WEIGHT_AUDIT specialized prompt")
            system_prompt = BILL_WEIGHT_AUDIT_PROMPT
        else:
            system_prompt = REASONING_SYSTEM_PROMPT

        
        user_prompt = REASONING_USER_PROMPT.format(
            audit_type=audit_type,
            rated_data=json.dumps(relevant_data, indent=2, default=str),
            parcel_characteristics=json.dumps(parcel_data, indent=2, default=str),
            agreements=json.dumps(state.get("agreements", {}), indent=2, default=str),
            reference_data=json.dumps(state.get("reference_data", {}), indent=2, default=str),
            enriched_data=json.dumps(state.get("enriched_data", {}), indent=2, default=str)
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        from utils.logger import logger
        response = self.llm.invoke(messages)
        result = self._parse_response(response.content)
        
        logger.info(f"🤖 LLM Result Status: {result.get('status', 'N/A')}")
        logger.info(f"🤖 LLM Result Cause Preview: {str(result.get('cause', ''))[:200]}")
        
        return result.get("cause", result.get("reasoning", response.content))
    
    def _analyze_discrepancy_with_case(
        self,
        audit_type: str,
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any],
        state: Dict[str, Any]
    ) -> tuple:
        """
        Use LLM to analyze the discrepancy and generate both explanation and error case.
        Returns: (cause, error_case)
        """
        # Prepare focused data for LLM
        relevant_data = self._extract_relevant_data(audit_type, rated_data, parcel_data)
        
        # Use specialized prompt for BILL_WEIGHT_AUDIT
        if audit_type == "BILL_WEIGHT_AUDIT":
            from utils.logger import logger
            logger.info("🎯 Using BILL_WEIGHT_AUDIT specialized prompt")
            system_prompt = BILL_WEIGHT_AUDIT_PROMPT + """

## Additional Instruction for Case Generation

If the data doesn't match Cases 1-4 exactly, you MUST generate a custom error case by analyzing the data.

Your response MUST include an "error_case" field with a descriptive case name like:
- "Case: Carrier Overbilling by X lbs"
- "Case: DIM Weight Calculation Difference"
- "Case: Actual Weight Used Instead of DIM Weight"
- "Case: Weight Rounding Discrepancy"
- Or any other case that accurately describes the issue found

Response Format:
{
    "status": "sufficient",
    "auditResult": "RIGHT" | "WRONG",
    "cause": "<detailed explanation>",
    "error_case": "<Case Name: Brief description of the specific issue>",
    "reasoning": "<your analysis>"
}
"""
        else:
            system_prompt = REASONING_SYSTEM_PROMPT
        
        user_prompt = REASONING_USER_PROMPT.format(
            audit_type=audit_type,
            rated_data=json.dumps(relevant_data, indent=2, default=str),
            parcel_characteristics=json.dumps(parcel_data, indent=2, default=str),
            agreements=json.dumps(state.get("agreements", {}), indent=2, default=str),
            reference_data=json.dumps(state.get("reference_data", {}), indent=2, default=str),
            enriched_data=json.dumps(state.get("enriched_data", {}), indent=2, default=str)
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        from utils.logger import logger
        response = self.llm.invoke(messages)
        result = self._parse_response(response.content)
        
        cause = result.get("cause", result.get("reasoning", response.content))
        error_case = result.get("error_case", None)
        
        logger.info(f"🤖 LLM Result Status: {result.get('status', 'N/A')}")
        logger.info(f"🤖 LLM Generated Case: {error_case}")
        logger.info(f"🤖 LLM Result Cause Preview: {str(cause)[:200]}")
        
        return cause, error_case
    
    def _extract_relevant_data(
        self, 
        audit_type: str, 
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract only the relevant fields for the audit type."""
        relevant = {}
        
        # Common fields
        common_fields = [
            "tracking_number", "invoice_number", "category",
            "carrier_total_net_charge", "calc_total_net_charge",
            "over_rated", "message"
        ]
        
        # Type-specific fields
        type_fields = self.REQUIRED_FIELDS.get(audit_type, [])
        all_fields = common_fields + type_fields
        
        for field in all_fields:
            if field in rated_data:
                relevant[field] = rated_data[field]
            elif field in parcel_data:
                relevant[field] = parcel_data[field]
        
        return relevant
    
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse the LLM response to extract reasoning details."""
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                return json.loads(content.strip())
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "status": "sufficient",
                "cause": content.strip(),
                "reasoning": content.strip()
            }


def reason_audit(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node function for the LangGraph workflow.
    Determines the audit cause and data sufficiency.
    """
    from utils.logger import log_node_start, log_node_end, log_llm_call, log_llm_result, logger
    
    log_node_start("reason_audit", audit_type=state.get("audit_type", ""))
    
    agent = AuditReasoningAgent()
    
    # Log LLM initialization
    logger.info(f"🤖 Initializing LLM: {LLM_MODEL}")
    
    result = agent.reason(state)
    
    # Log results
    logger.info(f"📊 Reasoning Status: {result.get('reasoning_status')}")
    
    # Log the detected error case
    if result.get('error_case'):
        logger.info(f"📋 Detected Error Case: {result.get('error_case')}")
    
    if result.get('missing_fields'):
        logger.warning(f"⚠️  Missing Fields: {result.get('missing_fields')}")
    if result.get('audit_cause'):
        cause_preview = result.get('audit_cause', '')[:100]
        logger.info(f"💡 Audit Cause: {cause_preview}...")
    
    log_node_end("reason_audit", {"status": result.get("reasoning_status")})
    return result

