# AuditOrchestrator
# Main LangGraph orchestrator that coordinates all agents
# Manages the flow: Data Retrieval → Classification → Reasoning → Enrichment Loop → Summary

from typing import Dict, Any, Optional
from graph.workflow import compile_workflow
from graph.state import AuditState


class AuditOrchestrator:
    """
    Main orchestrator that runs the audit analysis workflow.
    """
    
    def __init__(self):
        self.workflow = compile_workflow()
    
    def run_audit(
        self,
        tracking_number: str,
        client_id: str,
        carrier_id: str
    ) -> Dict[str, Any]:
        """
        Run the complete audit analysis workflow.
        
        Args:
            tracking_number: The shipment tracking number to audit
            client_id: Client identifier
            carrier_id: Carrier identifier (e.g., UPS, FedEx)
            
        Returns:
            Final state with audit results including summary
        """
        # Initialize the state
        initial_state: AuditState = {
            "tracking_number": tracking_number,
            "client_id": client_id,
            "carrier_id": carrier_id,
            "rated_data": None,
            "parcel_characteristics": None,
            "agreements": None,
            "reference_data": None,
            "audit_type": None,
            "audit_category": None,
            "classification_confidence": None,
            "reasoning_status": None,
            "reasoning_result": None,
            "missing_fields": None,
            "audit_cause": None,
            "enrichment_iterations": 0,
            "enriched_data": None,
            "audit_summary": None,
            "summary_bullets": None,
            "error": None,
            "messages": []
        }
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        return final_state
    
    def run_audit_stream(
        self,
        tracking_number: str,
        client_id: str,
        carrier_id: str
    ):
        """
        Run the audit with streaming to see intermediate steps.
        
        Yields state updates at each node.
        """
        initial_state: AuditState = {
            "tracking_number": tracking_number,
            "client_id": client_id,
            "carrier_id": carrier_id,
            "rated_data": None,
            "parcel_characteristics": None,
            "agreements": None,
            "reference_data": None,
            "audit_type": None,
            "audit_category": None,
            "classification_confidence": None,
            "reasoning_status": None,
            "reasoning_result": None,
            "missing_fields": None,
            "audit_cause": None,
            "enrichment_iterations": 0,
            "enriched_data": None,
            "audit_summary": None,
            "summary_bullets": None,
            "error": None,
            "messages": []
        }
        
        # Stream the workflow execution
        for state in self.workflow.stream(initial_state):
            yield state
    
    def get_audit_result(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract the key results from the final state.
        
        Args:
            final_state: The final workflow state
            
        Returns:
            Cleaned up audit result
        """
        return {
            "tracking_number": final_state.get("tracking_number"),
            "audit_type": final_state.get("audit_type"),
            "audit_cause": final_state.get("audit_cause"),
            "summary": final_state.get("audit_summary"),
            "bullets": final_state.get("summary_bullets", []),
            "confidence": final_state.get("classification_confidence"),
            "enrichment_iterations": final_state.get("enrichment_iterations", 0),
            "error": final_state.get("error")
        }


def run_audit_analysis(
    tracking_number: str,
    client_id: str,
    carrier_id: str
) -> Dict[str, Any]:
    """
    Convenience function to run an audit analysis.
    
    Args:
        tracking_number: The shipment tracking number to audit
        client_id: Client identifier  
        carrier_id: Carrier identifier
        
    Returns:
        Audit results dictionary
    """
    orchestrator = AuditOrchestrator()
    final_state = orchestrator.run_audit(tracking_number, client_id, carrier_id)
    return orchestrator.get_audit_result(final_state)
