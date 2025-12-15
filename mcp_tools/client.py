# MCP Client
# Connects to the tossx MCP server via SSE at http://localhost:8099/aitossx/sse

import json
import asyncio
from typing import Dict, Any, Optional, List
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """
    MCP Client to connect to tossx MCP server.
    Provides access to Rate Audit Analysis tools.
    """
    
    def __init__(self, base_url: str = "http://localhost:8099/aitossx/sse", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session: Optional[ClientSession] = None
        self._tools: Dict[str, Any] = {}
        
        # Build headers with API key
        self.headers = {}
        if api_key:
            self.headers["api_key"] = api_key
    
    async def connect(self):
        """Establish connection to MCP server."""
        async with sse_client(self.base_url, headers=self.headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                self._tools = {tool.name: tool for tool in tools_result.tools}
                print(f"Connected to MCP server. Available tools: {list(self._tools.keys())}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool with given arguments."""
        async with sse_client(self.base_url, headers=self.headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return self._parse_result(result)
    
    def _parse_result(self, result) -> Any:
        """Parse the MCP tool result."""
        if hasattr(result, 'content') and result.content:
            content = result.content[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return content.text
        return result
    
    # Convenience methods for each tool
    
    async def get_parcel_characteristic(self, tracking_number: str) -> Dict[str, Any]:
        """Get parcel characteristic by tracking number."""
        return await self.call_tool("get_parcel_characteristic", {
            "trackingNumber": tracking_number
        })
    
    async def get_rated_data(self, tracking_number: str) -> Dict[str, Any]:
        """Get rated data by tracking number."""
        return await self.call_tool("get_rated_data", {
            "trackingNumber": tracking_number
        })
    
    async def get_rated_data_additional_services(self, rated_data_id: str) -> List[Dict[str, Any]]:
        """Get rated data additional services by rated data ID."""
        return await self.call_tool("get_rated_data_additional_services", {
            "ratedDataId": rated_data_id
        })
    
    async def get_agreement_details_json(self, client_id: str, carrier_id: str) -> Dict[str, Any]:
        """Get agreement details JSON for client and carrier."""
        return await self.call_tool("get_agreement_details_json", {
            "clientId": client_id,
            "carrierId": carrier_id
        })
    
    async def get_full_tracking_analysis(self, tracking_number: str) -> Dict[str, Any]:
        """Get full tracking analysis including invoice and UPS details."""
        return await self.call_tool("get_full_tracking_analysis", {
            "trackingNumber": tracking_number
        })
    
    async def get_default_dim_divisors(self, ship_date: str) -> List[Dict[str, Any]]:
        """Retrieve Default Dimension Divisors for a given ship date."""
        return await self.call_tool("get_default_dim_divisors", {
            "shipDate": ship_date
        })


# Synchronous wrapper for use in LangGraph nodes
class MCPClientSync:
    """
    Synchronous wrapper for MCPClient.
    Use this in LangGraph workflow nodes.
    """
    
    def __init__(self, base_url: str = "http://localhost:8099/aitossx/sse", api_key: str = None):
        self.client = MCPClient(base_url, api_key)
    
    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # If already in async context, create new event loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)
    
    def get_parcel_characteristic(self, tracking_number: str) -> Dict[str, Any]:
        """Get parcel characteristic by tracking number."""
        return self._run_async(self.client.get_parcel_characteristic(tracking_number))
    
    def get_rated_data(self, tracking_number: str) -> Dict[str, Any]:
        """Get rated data by tracking number."""
        return self._run_async(self.client.get_rated_data(tracking_number))
    
    def get_rated_data_additional_services(self, rated_data_id: str) -> List[Dict[str, Any]]:
        """Get rated data additional services by rated data ID."""
        return self._run_async(self.client.get_rated_data_additional_services(rated_data_id))
    
    def get_agreement_details_json(self, client_id: str, carrier_id: str) -> Dict[str, Any]:
        """Get agreement details JSON for client and carrier."""
        return self._run_async(self.client.get_agreement_details_json(client_id, carrier_id))
    
    def get_full_tracking_analysis(self, tracking_number: str) -> Dict[str, Any]:
        """Get full tracking analysis including invoice and UPS details."""
        return self._run_async(self.client.get_full_tracking_analysis(tracking_number))
    
    def get_default_dim_divisors(self, ship_date: str) -> List[Dict[str, Any]]:
        """Retrieve Default Dimension Divisors for a given ship date."""
        return self._run_async(self.client.get_default_dim_divisors(ship_date))


def create_mcp_client(base_url: str = "http://localhost:8099/aitossx/sse", api_key: str = None) -> MCPClientSync:
    """Create and return an MCP client instance."""
    return MCPClientSync(base_url, api_key)
