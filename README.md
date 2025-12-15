# Rate Audit Analyser

A LangGraph-based multi-agent system for analyzing parcel shipping rate audits.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AuditOrchestrator                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌───────────────────┐                     │
│  │ MCPDataFetcher│───►│ AuditClassifierAgent │                   │
│  └──────────────┘    └─────────┬─────────┘                     │
│                                │                                │
│                                ▼                                │
│                    ┌───────────────────┐                       │
│                    │ AuditReasoningAgent │◄─────────┐           │
│                    └─────────┬─────────┘          │           │
│                              │                     │           │
│              ┌───────────────┴───────────────┐    │           │
│              │                               │    │           │
│              ▼                               ▼    │           │
│  ┌───────────────────┐           ┌─────────────────┐          │
│  │ AuditSummaryAgent │           │DataEnrichmentAgent│─────────┘ │
│  └───────────────────┘           └─────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Process Flow

1. **Initial Data Retrieval** - MCPDataFetcher gets rated data, parcel characteristics, agreements
2. **Audit Classification** - AuditClassifierAgent classifies the audit type
3. **Audit Reasoning** - AuditReasoningAgent determines the cause
   - `sufficient` → proceed to summary
   - `insufficient` → list missing fields
4. **Context Enrichment Loop** - DataEnrichmentAgent fetches missing data (loops until sufficient)
5. **Final Summary** - AuditSummaryAgent produces bullet-based explanation

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
MCP_API_KEY=your_mcp_api_key_here
```

## Usage

### Command Line

```bash
python run.py
```

### Streamlit UI

```bash
streamlit run app.py
```

### Programmatic

```python
from orchestrator.audit_orchestrator import run_audit_analysis

result = run_audit_analysis(
    tracking_number="1Z999AA10123456784",
    client_id="CLIENT001",
    carrier_id="UPS"
)

print(result["summary"])
```

## Project Structure

```
RateAuditAnalyser/
├── agents/
│   ├── audit_classifier_agent.py   # Classifies audit type
│   ├── audit_reasoning_agent.py    # Determines audit cause
│   ├── audit_summary_agent.py      # Generates summary
│   └── data_enrichment_agent.py    # Fetches missing data
├── graph/
│   ├── state.py                    # TypedDict for graph state
│   └── workflow.py                 # LangGraph workflow definition
├── mcp/
│   └── mcp_data_fetcher.py         # MCP data fetching
├── orchestrator/
│   └── audit_orchestrator.py       # Main orchestration logic
├── prompts/
│   └── prompts.py                  # Agent prompts
├── app.py                          # Streamlit UI
├── config.py                       # Configuration
├── run.py                          # CLI entry point
└── requirements.txt                # Dependencies
```

## Audit Types Supported

- BILL_WEIGHT - Weight discrepancies
- DIM_WEIGHT - Dimensional weight issues
- SERVICE_TYPE - Wrong service applied
- ZONE_MISMATCH - Incorrect zone calculation
- SURCHARGE - Surcharge discrepancies
- ACCESSORIAL - Accessorial charge issues
- DUPLICATE_CHARGE - Duplicate billing
- RATE_DISCOUNT - Discount not applied
- FUEL_SURCHARGE - Fuel calculation errors
- RESIDENTIAL_SURCHARGE - Residential delivery issues

## License

MIT
