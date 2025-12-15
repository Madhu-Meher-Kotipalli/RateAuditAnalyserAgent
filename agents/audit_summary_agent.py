# AuditSummaryAgent
# Once reasoning is confirmed sufficient, produces a clean bullet-based explanation of the audit.

import json
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.append('..')

from prompts.prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT, BILL_WEIGHT_SUMMARY_PROMPT
from config import GOOGLE_API_KEY, LLM_MODEL


class AuditSummaryAgent:
    """
    Agent responsible for generating the final audit summary.
    Uses LLM to create a professional bullet-based explanation.
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3  # Slightly higher for more natural summaries
        )
    
    def summarize(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a professional bullet-based audit summary.
        
        Args:
            state: Current graph state with audit cause and all data
            
        Returns:
            Updated state with audit_summary and summary_bullets
        """
        rated_data = state.get("rated_data", {}) or {}
        parcel_data = state.get("parcel_characteristics", {}) or {}
        
        # Try LLM first, fall back to rule-based if it fails
        try:
            summary = self._generate_llm_summary(state, rated_data, parcel_data)
        except Exception as e:
            summary = self._generate_rule_based_summary(state, rated_data, parcel_data)
        
        bullets = self._extract_bullets(summary)
        
        return {
            "audit_summary": summary,
            "summary_bullets": bullets,
        }
    
    def _generate_llm_summary(
        self,
        state: Dict[str, Any],
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> str:
        """Generate summary using LLM."""
        audit_type = state.get("audit_type", "UNKNOWN")
        error_case = state.get("error_case", "Unknown Case")
        
        # Use specialized prompt for BILL_WEIGHT_AUDIT
        if audit_type == "BILL_WEIGHT_AUDIT":
            system_prompt = BILL_WEIGHT_SUMMARY_PROMPT
        else:
            system_prompt = SUMMARY_SYSTEM_PROMPT
        
        user_prompt = SUMMARY_USER_PROMPT.format(
            audit_type=audit_type,
            error_case=error_case,
            audit_cause=state.get("audit_cause", ""),
            reasoning_result=state.get("reasoning_result", ""),
            rated_data=json.dumps(self._get_summary_data(rated_data), indent=2, default=str),
            parcel_characteristics=json.dumps(parcel_data, indent=2, default=str)
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def _get_summary_data(self, rated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key fields for summary generation."""
        key_fields = [
            "trackingNumber", "invoiceNumber", "category",
            "carrierBillWeight", "calcBillWeight", "actualWeight",
            "carrierZone", "calcZone",
            "carrierOriginalService", "calcOriginalService",
            "carrierTotalNetCharge", "calcTotalNetCharge",
            "carrierTotalDiscountPercentage", "calcTotalDiscountPercentage",
            "carrierTotalSurcharges", "calcTotalSurcharges",
            "overRated", "message"
        ]
        return {k: rated_data.get(k) for k in key_fields if rated_data.get(k) is not None}
    
    def _generate_rule_based_summary(
        self,
        state: Dict[str, Any],
        rated_data: Dict[str, Any],
        parcel_data: Dict[str, Any]
    ) -> str:
        """Generate summary using rules when LLM fails."""
        audit_type = state.get("audit_type", "UNKNOWN")
        audit_cause = state.get("audit_cause", "Unable to determine cause")
        
        tracking = rated_data.get("trackingNumber", "N/A")
        carrier_net = rated_data.get("carrierTotalNetCharge", 0) or 0
        calc_net = rated_data.get("calcTotalNetCharge", 0) or 0
        overcharge = float(carrier_net) - float(calc_net)
        
        # Build summary based on audit type
        summary = f"""**Audit Type**: {audit_type}

**Finding Summary**: {audit_cause}

**Key Details**:
• Tracking Number: {tracking}
• Invoice Number: {rated_data.get('invoiceNumber', 'N/A')}
• Ship Date: {rated_data.get('shipDate', 'N/A')}
"""
        
        # Add type-specific details
        if audit_type in ["BILL_WEIGHT", "WEIGHT", "DIM_WEIGHT"]:
            summary += f"""• Carrier Billed Weight: {rated_data.get('carrierBillWeight', 'N/A')} lbs
• Calculated Weight: {rated_data.get('calcBillWeight', 'N/A')} lbs
• Actual Weight: {rated_data.get('actualWeight', 'N/A')} lbs
"""
            if audit_type == "DIM_WEIGHT":
                l = rated_data.get('length', 0) or 0
                w = rated_data.get('width', 0) or 0
                h = rated_data.get('height', 0) or 0
                summary += f"""• Dimensions: {l}" x {w}" x {h}"
• DIM Divisor: {rated_data.get('calcDimDivisor', 139)}
"""
        
        elif audit_type in ["ZONE", "ZONE_MISMATCH"]:
            summary += f"""• Carrier Zone: {rated_data.get('carrierZone', 'N/A')}
• Calculated Zone: {rated_data.get('calcZone', 'N/A')}
• Origin: {parcel_data.get('senderPostal', 'N/A')}
• Destination: {parcel_data.get('receiverPostal', 'N/A')}
"""
        
        elif audit_type in ["SERVICE", "SERVICE_TYPE"]:
            summary += f"""• Carrier Service: {rated_data.get('carrierOriginalService', 'N/A')}
• Expected Service: {rated_data.get('calcOriginalService', 'N/A')}
"""
        
        elif audit_type in ["DISCOUNT", "BASE_DISCOUNT"]:
            summary += f"""• Carrier Discount: {rated_data.get('carrierTotalDiscountPercentage', 0)}%
• Expected Discount: {rated_data.get('calcTotalDiscountPercentage', 0)}%
"""
        
        # Add charges
        summary += f"""
**Charges**:
• Carrier Net Charge: ${float(carrier_net):.2f}
• Calculated Net Charge: ${float(calc_net):.2f}
• Overcharge Amount: ${overcharge:.2f}

**Recommendation**: {"File dispute with carrier for refund." if overcharge > 0 else "No action required - charges are correct or undercharged."}

**Potential Recovery**: ${max(0, overcharge):.2f}
"""
        
        return summary
    
    def _extract_bullets(self, summary: str) -> List[str]:
        """Extract bullet points from the summary."""
        bullets = []
        lines = summary.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                bullets.append(line.lstrip('•-* '))
        return bullets


def summarize_audit(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node function for the LangGraph workflow.
    Generates the final audit summary.
    """
    from utils.logger import log_node_start, log_node_end, log_llm_call, log_llm_result, log_workflow_end, logger
    
    log_node_start("summarize_audit")
    logger.info(f"🤖 Generating summary using LLM: {LLM_MODEL}")
    
    agent = AuditSummaryAgent()
    result = agent.summarize(state)
    
    # Log summary preview
    summary_preview = result.get('audit_summary', '')[:150] if result.get('audit_summary') else 'N/A'
    logger.info(f"📝 Summary Preview: {summary_preview}...")
    logger.info(f"📝 Bullet Points: {len(result.get('summary_bullets', []))} items")
    
    log_node_end("summarize_audit")
    log_workflow_end(True)
    
    return result

