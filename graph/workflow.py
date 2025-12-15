# LangGraph Workflow
# Defines the StateGraph with nodes and edges for the audit analysis flow

from typing import Literal
from langgraph.graph import StateGraph, END

from graph.state import AuditState
from agents.audit_classifier_agent import classify_audit
from agents.audit_reasoning_agent import reason_audit
from agents.data_enrichment_agent import enrich_data
from agents.audit_summary_agent import summarize_audit
from mcp_tools.mcp_data_fetcher import MCPDataFetcher
from config import MAX_ENRICHMENT_ITERATIONS
from utils.logger import (
    log_node_start, log_node_end, log_mcp_call, log_mcp_result, 
    log_error, log_workflow_start, logger
)


def fetch_initial_data(state: AuditState) -> dict:
    """
    Node: Fetch initial data from MCP.
    This is the first step in the workflow.
    
    Fetches:
    - rated_data by tracking_number
    - rated_data_additional_services by rated_data.id
    - parcel_characteristics by tracking_number
    - agreements by client_id and carrier_id
    """
    from config import MCP_SSE_URL, USE_MOCK_DATA
    
    tracking_number = state.get("tracking_number", "")
    client_id = state.get("client_id", "")
    carrier_id = state.get("carrier_id", "")
    
    # Log workflow start
    log_workflow_start(tracking_number, client_id, carrier_id)
    log_node_start("fetch_initial_data", tracking_number=tracking_number, client_id=client_id, carrier_id=carrier_id)
    
    fetcher = MCPDataFetcher(MCP_SSE_URL)
    
    # Enable mock mode if configured or MCP server not available
    if USE_MOCK_DATA:
        logger.info("📌 Using MOCK DATA mode")
        fetcher.enable_mock_mode(True)
    else:
        logger.info(f"📌 Connecting to MCP server: {MCP_SSE_URL}")
    
    # Fetch rated data by tracking number
    log_mcp_call("get_rated_data", {"trackingNumber": tracking_number})
    rated_data = fetcher.get_rated_data(tracking_number, client_id, carrier_id)
    
    # Check for errors and log appropriately
    if isinstance(rated_data, dict) and rated_data.get("error"):
        log_mcp_result("get_rated_data", False, f"ERROR: {rated_data.get('error')}")
        logger.error(f"❌ get_rated_data failed: {rated_data.get('error')}")
    else:
        log_mcp_result("get_rated_data", True, 
                       f"category: {rated_data.get('category', 'N/A')}" if isinstance(rated_data, dict) else "data received")
    
    # Fetch rated data additional services using rated_data.id
    rated_data_additional_services = []
    if rated_data and isinstance(rated_data, dict) and rated_data.get("id"):
        rated_data_id = str(rated_data.get("id"))
        log_mcp_call("get_rated_data_additional_services", {"ratedDataId": rated_data_id})
        rated_data_additional_services = fetcher.get_rated_data_additional_services(rated_data_id)
        log_mcp_result("get_rated_data_additional_services", True, f"services count: {len(rated_data_additional_services)}")
    
    # Combine rated_data with its additional services
    if rated_data and isinstance(rated_data, dict):
        rated_data["additional_services"] = rated_data_additional_services
    
    # Fetch parcel characteristics by tracking number
    log_mcp_call("get_parcel_characteristic", {"trackingNumber": tracking_number})
    parcel_characteristics = fetcher.get_parcel_characteristics(tracking_number)
    log_mcp_result("get_parcel_characteristic", not parcel_characteristics.get("error") if isinstance(parcel_characteristics, dict) else True)
    
    # Fetch agreements by client_id and carrier_id
    log_mcp_call("get_agreement_details_json", {"clientId": client_id, "carrierId": carrier_id})
    agreements = fetcher.get_agreements(client_id, carrier_id)
    log_mcp_result("get_agreement_details_json", not agreements.get("error") if isinstance(agreements, dict) else True)
    
    # Fetch default DIM divisors if ship date is available
    default_dim_divisors = []
    ship_date = ""
    if parcel_characteristics and isinstance(parcel_characteristics, dict):
        ship_date = parcel_characteristics.get("shipDate", "")
        # Handle potential date format issues or missing date
        if not ship_date and rated_data and isinstance(rated_data, dict):
            ship_date = rated_data.get("shipDate", "")
            
    if ship_date:
        log_mcp_call("get_default_dim_divisors", {"shipDate": ship_date})
        default_dim_divisors = fetcher.get_default_dim_divisors(ship_date)
        log_mcp_result("get_default_dim_divisors", True, f"count: {len(default_dim_divisors)}")
    else:
        logger.warning("⚠️ No ship date found, skipping default DIM divisors fetch")
    
    result = {
        "rated_data": rated_data,
        "parcel_characteristics": parcel_characteristics,
        "agreements": agreements,
        "default_dim_divisors": default_dim_divisors,
        "enrichment_iterations": 0
    }
    
    log_node_end("fetch_initial_data", {"rated_data": "fetched", "parcel_characteristics": "fetched", "agreements": "fetched"})
    return result


def fetch_reference_data(state: AuditState) -> dict:
    """
    Node: Fetch reference data using get_full_tracking_analysis.
    
    This fetches:
    - invoiceDetails
    - upsTrackingDetails  
    - upsTrackingDetailsDump
    """
    from config import MCP_SSE_URL, USE_MOCK_DATA
    
    log_node_start("fetch_reference_data", audit_type=state.get("audit_type", ""))
    
    fetcher = MCPDataFetcher(MCP_SSE_URL)
    
    if USE_MOCK_DATA:
        fetcher.enable_mock_mode(True)
    
    tracking_number = state.get("tracking_number", "")
    
    # Use get_full_tracking_analysis for reference data
    log_mcp_call("get_full_tracking_analysis", {"trackingNumber": tracking_number})
    reference_data = fetcher.get_full_tracking_analysis(tracking_number)
    log_mcp_result("get_full_tracking_analysis", not reference_data.get("error") if isinstance(reference_data, dict) else True)
    
    log_node_end("fetch_reference_data", {"reference_data": "fetched"})
    return {
        "reference_data": reference_data
    }



def should_continue_reasoning(state: AuditState) -> Literal["summarize", "enrich", "end"]:
    """
    Router: Determine next step based on reasoning status.
    
    Returns:
        - "summarize" if data is sufficient → go to summary
        - "enrich" if data is insufficient and iterations remain → enrich data
        - "end" if max iterations reached → end with error
    """
    reasoning_status = state.get("reasoning_status", "insufficient")
    iterations = state.get("enrichment_iterations", 0)
    
    if reasoning_status == "sufficient":
        return "summarize"
    
    if iterations >= MAX_ENRICHMENT_ITERATIONS:
        return "end"
    
    return "enrich"


def create_audit_workflow() -> StateGraph:
    """
    Create and return the LangGraph workflow for audit analysis.
    
    Flow:
    1. fetch_initial_data → Initial MCP data retrieval
    2. classify_audit → Classify audit type
    3. fetch_reference_data → Get category-specific reference data
    4. reason_audit → Determine audit cause
    5. Router:
       - If sufficient → summarize_audit → END
       - If insufficient → enrich_data → reason_audit (loop)
       - If max iterations → END
    """
    # Create the graph
    workflow = StateGraph(AuditState)
    
    # Add nodes
    workflow.add_node("fetch_initial_data", fetch_initial_data)
    workflow.add_node("classify_audit", classify_audit)
    workflow.add_node("fetch_reference_data", fetch_reference_data)
    workflow.add_node("reason_audit", reason_audit)
    workflow.add_node("enrich_data", enrich_data)
    workflow.add_node("summarize_audit", summarize_audit)
    
    # Define edges
    workflow.set_entry_point("fetch_initial_data")
    
    # Linear flow: fetch → classify → fetch_reference → reason
    workflow.add_edge("fetch_initial_data", "classify_audit")
    workflow.add_edge("classify_audit", "fetch_reference_data")
    workflow.add_edge("fetch_reference_data", "reason_audit")
    
    # Conditional routing after reasoning
    workflow.add_conditional_edges(
        "reason_audit",
        should_continue_reasoning,
        {
            "summarize": "summarize_audit",
            "enrich": "enrich_data",
            "end": END
        }
    )
    
    # Enrichment loop back to reasoning
    workflow.add_edge("enrich_data", "reason_audit")
    
    # Summary to end
    workflow.add_edge("summarize_audit", END)
    
    return workflow


def compile_workflow():
    """Compile the workflow into a runnable graph."""
    workflow = create_audit_workflow()
    return workflow.compile()


# Create a pre-compiled instance for direct import
app = compile_workflow()
