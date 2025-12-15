# Graph State Definition
# Defines the TypedDict for the shared state across all nodes in the graph

from typing import TypedDict, Optional, List, Dict, Any, Literal
from typing_extensions import Annotated
from langgraph.graph.message import add_messages


class AuditState(TypedDict):
    """Shared state across all nodes in the audit analysis graph."""
    
    # Input data
    tracking_number: str
    client_id: str
    carrier_id: str
    
    # MCP fetched data
    rated_data: Optional[Dict[str, Any]]
    parcel_characteristics: Optional[Dict[str, Any]]
    agreements: Optional[Dict[str, Any]]
    reference_data: Optional[Dict[str, Any]]
    default_dim_divisors: Optional[List[Dict[str, Any]]]
    
    # Classification output
    audit_type: Optional[str]
    audit_category: Optional[str]
    classification_confidence: Optional[float]
    
    # Reasoning output
    reasoning_status: Optional[Literal["sufficient", "insufficient"]]
    reasoning_result: Optional[str]
    missing_fields: Optional[List[str]]
    audit_cause: Optional[str]
    error_case: Optional[str]  # Case 1, Case 2, Case 3, or Case 4
    
    # Enrichment tracking
    enrichment_iterations: int
    enriched_data: Optional[Dict[str, Any]]
    
    # Final output
    audit_summary: Optional[str]
    summary_bullets: Optional[List[str]]
    
    # Error handling
    error: Optional[str]
    
    # Messages for LLM interactions
    messages: Annotated[list, add_messages]
