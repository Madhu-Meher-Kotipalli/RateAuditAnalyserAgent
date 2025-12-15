# Main Entry Point
# Run the Rate Audit Analyser

import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.audit_orchestrator import run_audit_analysis, AuditOrchestrator


def main():
    """Main function to run the audit analysis."""
    print("=" * 60)
    print("🔍 Rate Audit Analyser - LangGraph")
    print("=" * 60)
    
    # Example audit request
    tracking_number = "1Z999AA10123456784"
    client_id = "CLIENT001"
    carrier_id = "UPS"
    
    print(f"\n📦 Analyzing shipment: {tracking_number}")
    print(f"   Client: {client_id}")
    print(f"   Carrier: {carrier_id}")
    print("-" * 60)
    
    # Run with streaming to see progress
    orchestrator = AuditOrchestrator()
    
    print("\n🔄 Running audit workflow...\n")
    
    for step_output in orchestrator.run_audit_stream(tracking_number, client_id, carrier_id):
        # step_output is a dict with node name as key
        for node_name, state_update in step_output.items():
            print(f"✅ Completed: {node_name}")
            
            # Show key updates
            if node_name == "classify_audit":
                print(f"   → Audit Type: {state_update.get('audit_type')}")
                print(f"   → Confidence: {state_update.get('classification_confidence', 0):.2%}")
            
            elif node_name == "reason_audit":
                status = state_update.get('reasoning_status')
                print(f"   → Status: {status}")
                if status == "insufficient":
                    print(f"   → Missing: {state_update.get('missing_fields')}")
            
            elif node_name == "enrich_data":
                print(f"   → Enrichment iteration: {state_update.get('enrichment_iterations')}")
            
            elif node_name == "summarize_audit":
                print(f"   → Summary generated")
        
        print()
    
    # Get final result
    print("-" * 60)
    print("\n📋 FINAL AUDIT RESULT:\n")
    
    # Run once more to get complete state (or we could track it from stream)
    result = run_audit_analysis(tracking_number, client_id, carrier_id)
    
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(result.get("summary", "No summary available"))
    
    print("\n" + "=" * 60)


def run_single_audit(tracking_number: str, client_id: str, carrier_id: str):
    """Run a single audit and return results."""
    return run_audit_analysis(tracking_number, client_id, carrier_id)


if __name__ == "__main__":
    main()
