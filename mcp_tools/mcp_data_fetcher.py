# MCPDataFetcher
# Fetches required MCP data: rated data, parcel characteristics, agreements
# Connects to tossx MCP server at http://localhost:8099/aitossx/sse

from typing import Dict, Any, Optional, List

from mcp_tools.client import MCPClientSync, create_mcp_client


# Default API Key for MCP authentication
DEFAULT_API_KEY = "eyJhbGci"


class MCPDataFetcher:
    """
    Fetches data from MCP server for audit analysis.
    Connects to tossx MCP tools via SSE.
    
    Available MCP Tools:
    - get_parcel_characteristic(trackingNumber)
    - get_rated_data(trackingNumber)
    - get_rated_data_additional_services(ratedDataId)
    - get_agreement_details_json(clientId, carrierId)
    - get_full_tracking_analysis(trackingNumber)
    """
    
    def __init__(self, base_url: str = "http://localhost:8099/aitossx/sse", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key or DEFAULT_API_KEY
        self.client = create_mcp_client(base_url, self.api_key)
        self._use_mock = False  # Set to True to use mock data for testing
    
    def get_rated_data(self, tracking_number: str, client_id: str = None, carrier_id: str = None) -> Dict[str, Any]:
        """
        Fetch rated data for a shipment by tracking number.
        
        Args:
            tracking_number: The shipment tracking number
            client_id: Optional client ID (not used, kept for compatibility)
            carrier_id: Optional carrier ID (not used, kept for compatibility)
            
        Returns:
            RatedData object as dictionary
        """
        if self._use_mock:
            return self._get_mock_rated_data(tracking_number)
        
        try:
            result = self.client.get_rated_data(tracking_number)
            if isinstance(result, dict):
                # Check if MCP returned an error in the response
                if result.get("error"):
                    print(f"❌ MCP get_rated_data error: {result.get('error')}")
                return result
            # Handle non-dict responses (like string error messages)
            print(f"⚠️ get_rated_data unexpected response type: {type(result)}")
            print(f"⚠️ Raw response: {str(result)[:500]}")  # First 500 chars
            return {"error": f"Invalid data format: {result}", "raw_response": str(result)}
        except Exception as e:
            import traceback
            print(f"❌ Error fetching rated data: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return {"error": str(e), "exception_type": type(e).__name__}
    
    def get_parcel_characteristics(self, tracking_number: str) -> Dict[str, Any]:
        """
        Fetch parcel characteristics for a shipment.
        
        Args:
            tracking_number: The shipment tracking number
            
        Returns:
            ParcelCharacteristic object as dictionary
        """
        if self._use_mock:
            return self._get_mock_parcel_characteristics(tracking_number)
        
        try:
            result = self.client.get_parcel_characteristic(tracking_number)
            if isinstance(result, dict):
                return result
            return {"error": f"Invalid data format: {result}", "raw_response": str(result)}
        except Exception as e:
            print(f"Error fetching parcel characteristics: {e}")
            return {"error": str(e)}
    
    def get_rated_data_additional_services(self, rated_data_id: str) -> List[Dict[str, Any]]:
        """
        Fetch additional services for a rated data record.
        
        Args:
            rated_data_id: The rated data ID
            
        Returns:
            List of RatedDataAdditionalService objects
        """
        if self._use_mock:
            return []
        
        try:
            result = self.client.get_rated_data_additional_services(rated_data_id)
            return result if result else []
        except Exception as e:
            print(f"Error fetching additional services: {e}")
            return []
    
    def get_agreements(self, client_id: str, carrier_id: str) -> Dict[str, Any]:
        """
        Fetch agreement details for a client-carrier pair.
        
        Args:
            client_id: Client identifier
            carrier_id: Carrier identifier
            
        Returns:
            AgreementDetailsJson object as dictionary
        """
        if self._use_mock:
            return self._get_mock_agreements(client_id, carrier_id)
        
        try:
            result = self.client.get_agreement_details_json(client_id, carrier_id)
            if isinstance(result, dict):
                return result
            return {"error": f"Invalid data format: {result}", "raw_response": str(result)}
        except Exception as e:
            print(f"Error fetching agreements: {e}")
            return {"error": str(e)}
    
    def get_full_tracking_analysis(self, tracking_number: str) -> Dict[str, Any]:
        """
        Fetch complete tracking analysis including invoice and UPS details.
        
        Args:
            tracking_number: The shipment tracking number
            
        Returns:
            Dictionary with invoiceDetails, upsTrackingDetails, upsTrackingDetailsDump
        """
        if self._use_mock:
            return self._get_mock_full_analysis(tracking_number)
        
        try:
            result = self.client.get_full_tracking_analysis(tracking_number)
            return result if result else {}
        except Exception as e:
            print(f"Error fetching full tracking analysis: {e}")
            return {"error": str(e)}
    
    def get_default_dim_divisors(self, ship_date: str) -> List[Dict[str, Any]]:
        """
        Fetch default DIM divisors for a given ship date.
        
        Args:
            ship_date: The ship date (e.g., '2023-10-15')
            
        Returns:
            List of default DIM divisor objects
        """
        if self._use_mock:
            return []
        
        try:
            result = self.client.get_default_dim_divisors(ship_date)
            return result if result else []
        except Exception as e:
            print(f"Error fetching default DIM divisors: {e}")
            return []
    
    def get_reference_data(self, audit_type: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch category-specific reference data based on audit type.
        This may require additional MCP calls or local calculations.
        """
        reference_data = {}
        
        if audit_type in ["BILL_WEIGHT_AUDIT"]:
            reference_data = {
                "dim_divisor_standard": 139,
                "weight_rounding_rule": "UP_TO_NEXT_POUND",
                "minimum_billable_weight": 1.0,
            }
        
        elif audit_type in ["LIST_RATE_AUDIT", "LIST_RATE_NULL_AUDIT", "MWT_LIST_RATE_AUDIT"]:
            reference_data = {
                "rate_type": "LIST",
                "rate_source": "CARRIER_TARIFF",
            }
        
        elif audit_type in ["SURCHARGE_AUDIT", "SURCHARGE_APPLICABILITY_AUDIT", "FUEL_SURCHARGE_AUDIT"]:
            reference_data = {
                "surcharge_types": ["FUEL", "RESIDENTIAL", "DELIVERY_AREA", "EXTENDED_AREA"],
            }
        
        elif audit_type in ["BASE_DISCOUNTS_PERCENTAGE_AUDIT", "DISCOUNTS_PERCENTAGE_AUDIT", "EARNED_DISCOUNTS_PERCENTAGE_AUDIT"]:
            reference_data = {
                "discount_types": ["BASE", "EARNED", "OTHER"],
            }
        
        return reference_data
    
    def fetch_missing_data(self, missing_fields: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch specific missing data fields.
        
        Args:
            missing_fields: List of field names that are missing
            context: Context with tracking_number, client_id, carrier_id
            
        Returns:
            Dictionary with the fetched data
        """
        enriched_data = {}
        tracking_number = context.get("tracking_number", "")
        
        # If we need invoice/tracking details, fetch full analysis
        if any(f in missing_fields for f in ["invoice_details", "tracking_details", "upsTrackingDetails"]):
            if tracking_number:
                full_analysis = self.get_full_tracking_analysis(tracking_number)
                enriched_data["full_tracking_analysis"] = full_analysis
        
        # If we need additional services
        rated_data_id = context.get("rated_data_id")
        if "additional_services" in missing_fields and rated_data_id:
            enriched_data["additional_services"] = self.get_rated_data_additional_services(str(rated_data_id))
        
        return enriched_data
    
    # Mock data methods for testing without MCP server
    
    def enable_mock_mode(self, enabled: bool = True):
        """Enable or disable mock mode for testing."""
        self._use_mock = enabled
    
    def _get_mock_rated_data(self, tracking_number: str) -> Dict[str, Any]:
        """Return mock rated data for testing."""
        return {
            "id": 12345,
            "tracking_number": tracking_number,
            "category": "BILL_WEIGHT_AUDIT",
            "carrier_bill_weight": 15.00,
            "calc_bill_weight": 10.00,
            "actual_weight": 10.00,
            "carrier_total_net_charge": 25.82,
            "calc_total_net_charge": 21.53,
            "over_rated": 1,
            "message": "Weight discrepancy detected",
        }
    
    def _get_mock_parcel_characteristics(self, tracking_number: str) -> Dict[str, Any]:
        """Return mock parcel characteristics for testing."""
        return {
            "id": 12345,
            "tracking_number": tracking_number,
            "actual_weight": 10.00,
            "length": 12.00,
            "width": 10.00,
            "height": 8.00,
            "sender_postal": "90210",
            "receiver_postal": "10001",
            "status": "SUCCESS",
        }
    
    def _get_mock_agreements(self, client_id: str, carrier_id: str) -> Dict[str, Any]:
        """Return mock agreements for testing."""
        return {
            "client_id": client_id,
            "carrier_id": carrier_id,
            "dim_divisor": 139,
            "base_discount_percent": 45.0,
        }
    
    def _get_mock_full_analysis(self, tracking_number: str) -> Dict[str, Any]:
        """Return mock full tracking analysis for testing."""
        return {
            "invoiceDetails": [{"tracking_number": tracking_number, "total_charges": 25.82}],
            "upsTrackingDetails": [{"tracking_number": tracking_number}],
            "upsTrackingDetailsDump": [],
        }


# Convenience function for creating fetcher instance
def create_mcp_fetcher(base_url: str = "http://localhost:8099/aitossx/sse") -> MCPDataFetcher:
    """Create and return an MCPDataFetcher instance."""
    return MCPDataFetcher(base_url)
