# Logger Utility
# Provides consistent logging throughout the application

import logging
import sys
from datetime import datetime

# Create a custom logger
logger = logging.getLogger("RateAuditAnalyser")
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Create colored formatter
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Add emoji based on log type
        emoji = {
            'DEBUG': '🔍',
            'INFO': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🔥',
        }.get(record.levelname, '')
        
        formatted = f"{color}[{timestamp}] {emoji} {record.levelname}: {record.getMessage()}{self.RESET}"
        return formatted

# Apply formatter
console_handler.setFormatter(ColoredFormatter())

# Add handler to logger (avoid duplicates)
if not logger.handlers:
    logger.addHandler(console_handler)


def log_node_start(node_name: str, **kwargs):
    """Log when a workflow node starts."""
    logger.info(f"🚀 NODE START: {node_name}")
    for key, value in kwargs.items():
        logger.debug(f"   └─ {key}: {value}")


def log_node_end(node_name: str, result: dict = None):
    """Log when a workflow node ends."""
    logger.info(f"✅ NODE END: {node_name}")
    if result:
        for key, value in result.items():
            if value is not None:
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:100] + "..."
                logger.debug(f"   └─ {key}: {str_value}")


def log_mcp_call(tool_name: str, params: dict):
    """Log MCP tool calls."""
    logger.info(f"🔧 MCP CALL: {tool_name}")
    for key, value in params.items():
        logger.debug(f"   └─ {key}: {value}")


def log_mcp_result(tool_name: str, success: bool, data_summary: str = None):
    """Log MCP tool results."""
    if success:
        logger.info(f"📦 MCP RESULT: {tool_name} - Success")
    else:
        logger.error(f"📦 MCP RESULT: {tool_name} - Failed")
    if data_summary:
        logger.debug(f"   └─ {data_summary}")


def log_llm_call(agent_name: str, prompt_preview: str = None):
    """Log LLM calls."""
    logger.info(f"🤖 LLM CALL: {agent_name}")
    if prompt_preview:
        preview = prompt_preview[:200] + "..." if len(prompt_preview) > 200 else prompt_preview
        logger.debug(f"   └─ Prompt: {preview}")


def log_llm_result(agent_name: str, response_preview: str = None):
    """Log LLM results."""
    logger.info(f"💬 LLM RESULT: {agent_name}")
    if response_preview:
        preview = response_preview[:200] + "..." if len(response_preview) > 200 else response_preview
        logger.debug(f"   └─ Response: {preview}")


def log_error(message: str, error: Exception = None):
    """Log errors."""
    logger.error(f"❌ ERROR: {message}")
    if error:
        logger.error(f"   └─ {type(error).__name__}: {str(error)}")


def log_workflow_start(tracking_number: str, client_id: str, carrier_id: str):
    """Log when workflow starts."""
    logger.info("=" * 60)
    logger.info("🔍 RATE AUDIT WORKFLOW STARTED")
    logger.info("=" * 60)
    logger.info(f"   └─ Tracking: {tracking_number}")
    logger.info(f"   └─ Client: {client_id}")
    logger.info(f"   └─ Carrier: {carrier_id}")


def log_workflow_end(success: bool, summary: str = None):
    """Log when workflow ends."""
    logger.info("=" * 60)
    if success:
        logger.info("✅ RATE AUDIT WORKFLOW COMPLETED")
    else:
        logger.error("❌ RATE AUDIT WORKFLOW FAILED")
    logger.info("=" * 60)
