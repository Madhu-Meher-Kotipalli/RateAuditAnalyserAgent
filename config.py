# Configuration
# API keys, model settings, MCP endpoints

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

# Model Settings
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0.1

# MCP Endpoints
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8080")
MCP_SSE_URL = os.getenv("MCP_SSE_URL", "http://localhost:8099/aitossx/sse")

# Use mock data when MCP server is not available
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

# Audit Types
AUDIT_TYPES = [
    "BILL_WEIGHT",
    "DIM_WEIGHT", 
    "SERVICE_TYPE",
    "ZONE_MISMATCH",
    "SURCHARGE",
    "ACCESSORIAL",
    "DUPLICATE_CHARGE",
    "RATE_DISCOUNT",
    "FUEL_SURCHARGE",
    "RESIDENTIAL_SURCHARGE"
]

# Maximum enrichment iterations to prevent infinite loops
MAX_ENRICHMENT_ITERATIONS = 3

# LangSmith Configuration (Optional - for monitoring and tracing)
# LangSmith will automatically trace LLM calls if these environment variables are set
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "RateAuditAnalyser")
