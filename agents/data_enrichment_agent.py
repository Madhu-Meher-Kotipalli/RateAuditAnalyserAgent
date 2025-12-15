# DataEnrichmentAgent
# If data is insufficient, requests only the missing fields.
# Missing data is fetched from MCPDataFetcher.
# Routes back to AuditReasoningAgent until reasoning is complete.

from typing import Dict, Any, List

import sys
sys.path.append('..')

from mcp_tools.mcp_data_fetcher import MCPDataFetcher


class DataEnrichmentAgent:
    """
    Agent responsible for enriching data when reasoning is insufficient.
    No LLM needed - simply fetches missing fields from MCP.
    """
    
    # Mapping of field names to MCP data sources
    FIELD_TO_SOURCE = {
        # Weight fields
        "actual_weight": "parcel_characteristics",
        "carrier_bill_weight": "rated_data",
        "calc_bill_weight": "rated_data",
        
        # DIM fields
        "carrier_dim_divisor": "rated_data",
        "calc_dim_divisor": "rated_data",
        "length": "parcel_characteristics",
        "width": "parcel_characteristics",
        "height": "parcel_characteristics",
        
        # Zone fields
        "carrier_zone": "rated_data",
        "calc_zone": "rated_data",
        "sender_postal": "parcel_characteristics",
        "receiver_postal": "parcel_characteristics",
        "zone_chart": "reference_data",
        
        # Service fields
        "carrier_original_service": "rated_data",
        "calc_original_service": "rated_data",
        
        # Discount fields
        "carrier_total_discount_percentage": "rated_data",
        "calc_total_discount_percentage": "rated_data",
        "base_discount_percentage": "agreements",
        
        # Surcharge fields
        "carrier_total_surcharges": "rated_data",
        "calc_total_surcharges": "rated_data",
        "fuel_percentage": "rated_data",
        
        # Invoice/tracking details
        "invoice_details": "invoice_details",
        "tracking_details": "tracking_number_details",
    }
    
    def __init__(self):
        self.mcp_fetcher = MCPDataFetcher()
    
    def enrich(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch missing data fields from MCP.
        
        Args:
            state: Current graph state with missing_fields list
            
        Returns:
            Updated state with enriched_data and incremented enrichment_iterations
        """
        missing_fields = state.get("missing_fields", []) or []
        
        if not missing_fields:
            return {
                "enriched_data": state.get("enriched_data", {}),
                "enrichment_iterations": state.get("enrichment_iterations", 0)
            }
        
        # Prepare context for fetching
        rated_data = state.get("rated_data", {}) or {}
        parcel_data = state.get("parcel_characteristics", {}) or {}
        
        context = {
            "tracking_number": state.get("tracking_number", ""),
            "client_id": state.get("client_id", ""),
            "carrier_id": state.get("carrier_id", ""),
            "origin_zip": parcel_data.get("sender_postal") or rated_data.get("sender_postal", ""),
            "destination_zip": parcel_data.get("receiver_postal") or rated_data.get("receiver_postal", ""),
        }
        
        # Determine which data sources to fetch
        sources_needed = self._determine_data_sources(missing_fields)
        
        # Fetch data from required sources
        new_data = {}
        
        if "invoice_details" in sources_needed:
            new_data["invoice_details"] = self.mcp_fetcher.get_invoice_details(
                context.get("tracking_number", "")
            )
        
        if "tracking_number_details" in sources_needed:
            new_data["tracking_details"] = self.mcp_fetcher.get_tracking_number_details(
                context.get("tracking_number", "")
            )
        
        if "reference_data" in sources_needed:
            audit_type = state.get("audit_type", "UNKNOWN")
            new_data["reference_data"] = self.mcp_fetcher.get_reference_data(
                audit_type,
                origin_zip=context.get("origin_zip"),
                destination_zip=context.get("destination_zip")
            )
        
        # Also fetch specific missing fields
        fetched_fields = self.mcp_fetcher.fetch_missing_data(missing_fields, context)
        new_data.update(fetched_fields)
        
        # Merge with existing enriched data
        existing_enriched = state.get("enriched_data", {}) or {}
        merged_data = {**existing_enriched, **new_data}
        
        current_iterations = state.get("enrichment_iterations", 0)
        
        return {
            "enriched_data": merged_data,
            "enrichment_iterations": current_iterations + 1,
            "missing_fields": []  # Clear missing fields after enrichment
        }
    
    def _determine_data_sources(self, missing_fields: List[str]) -> set:
        """Determine which MCP data sources need to be queried."""
        sources = set()
        
        for field in missing_fields:
            source = self.FIELD_TO_SOURCE.get(field)
            if source:
                sources.add(source)
            else:
                # Default to trying invoice_details for unknown fields
                sources.add("invoice_details")
        
        return sources


def enrich_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node function for the LangGraph workflow.
    Enriches data by fetching missing fields.
    """
    from utils.logger import log_node_start, log_node_end, logger
    
    missing_fields = state.get("missing_fields", []) or []
    iterations = state.get("enrichment_iterations", 0)
    
    log_node_start("enrich_data", iteration=iterations + 1)
    logger.info(f"🔄 Enrichment iteration: {iterations + 1}")
    logger.info(f"📋 Missing fields to fetch: {missing_fields}")
    
    agent = DataEnrichmentAgent()
    result = agent.enrich(state)
    
    logger.info(f"✅ Enriched data keys: {list(result.get('enriched_data', {}).keys())}")
    
    log_node_end("enrich_data", {"iteration": result.get("enrichment_iterations")})
    return result

