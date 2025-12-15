# Streamlit Application
# UI for the Rate Audit Analyser

import streamlit as st
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.audit_orchestrator import AuditOrchestrator

# Page configuration
st.set_page_config(
    page_title="Rate Audit Analyser",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .step-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .result-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .success-badge {
        background: #4CAF50;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
    }
    .warning-badge {
        background: #FF9800;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Header
    st.markdown('<p class="main-header">🔍 Rate Audit Analyser</p>', unsafe_allow_html=True)
    st.markdown("Analyze parcel shipping invoices for billing discrepancies using AI-powered audit agents.")
    
    st.divider()
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("📦 Shipment Details")
        
        tracking_number = st.text_input(
            "Tracking Number",
            value="1Z999AA10123456784",
            help="Enter the shipment tracking number"
        )
        
        client_id = st.text_input(
            "Client ID",
            value="CLIENT001",
            help="Your client identifier"
        )
        
        carrier_id = st.text_input(
            "Carrier ID",
            value="1",
            help="Enter the carrier ID (e.g., 1 for UPS)"
        )
        
        st.divider()
        
        run_audit = st.button("🚀 Run Audit Analysis", type="primary", use_container_width=True)
        
        st.divider()
        
        # Info section
        st.info("""
        **Audit Types Detected:**
        - Bill Weight
        - DIM Weight
        - Zone Mismatch
        - Service Type
        - Surcharges
        - And more...
        """)
    
    # Main content area
    if run_audit:
        # Progress section
        progress_container = st.container()
        
        with progress_container:
            st.subheader("🔄 Audit Progress")
            
            # Create columns for steps
            col1, col2, col3, col4, col5 = st.columns(5)
            
            step_placeholders = {
                "fetch_initial_data": col1.empty(),
                "classify_audit": col2.empty(),
                "fetch_reference_data": col3.empty(),
                "reason_audit": col4.empty(),
                "summarize_audit": col5.empty()
            }
            
            step_names = {
                "fetch_initial_data": "📥 Fetch Data",
                "classify_audit": "🏷️ Classify",
                "fetch_reference_data": "📚 Reference",
                "reason_audit": "🧠 Reason",
                "summarize_audit": "📝 Summary"
            }
            
            # Initialize step displays
            for key, placeholder in step_placeholders.items():
                placeholder.markdown(f"""
                <div style="text-align: center; padding: 0.5rem; background: #e0e0e0; border-radius: 8px;">
                    <div style="font-size: 1.5rem;">⏳</div>
                    <div style="font-size: 0.75rem; color: #666;">{step_names[key]}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Run the audit with streaming
        orchestrator = AuditOrchestrator()
        final_state = {}  # Initialize as dict to merge updates
        
        try:
            for step_output in orchestrator.run_audit_stream(tracking_number, client_id, carrier_id):
                for node_name, state_update in step_output.items():
                    # Merge state updates instead of overwriting
                    if isinstance(state_update, dict):
                        final_state.update(state_update)
                    
                    # Update step display
                    if node_name in step_placeholders:
                        step_placeholders[node_name].markdown(f"""
                        <div style="text-align: center; padding: 0.5rem; background: linear-gradient(135deg, #4CAF50, #45a049); border-radius: 8px; color: white;">
                            <div style="font-size: 1.5rem;">✅</div>
                            <div style="font-size: 0.75rem;">{step_names.get(node_name, node_name)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Handle enrichment loop
                    if node_name == "enrich_data":
                        iterations = state_update.get("enrichment_iterations", 0)
                        st.info(f"🔄 Enrichment iteration {iterations}: Fetching additional data...")
            
            st.divider()
            
            # Results section
            if final_state:
                st.subheader("📋 Audit Results")
                
                # Metrics row
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                
                with metric_col1:
                    st.metric(
                        "Audit Type",
                        final_state.get("audit_type", "UNKNOWN")
                    )
                
                with metric_col2:
                    confidence = final_state.get("classification_confidence", 0)
                    st.metric(
                        "Confidence",
                        f"{confidence:.0%}" if confidence else "N/A"
                    )
                
                with metric_col3:
                    st.metric(
                        "Enrichment Iterations",
                        final_state.get("enrichment_iterations", 0)
                    )
                
                with metric_col4:
                    status = final_state.get("reasoning_status", "unknown")
                    st.metric(
                        "Status",
                        status.upper() if status else "N/A"
                    )
                
                st.divider()
                
                # Display Detected Error Case prominently
                error_case = final_state.get("error_case", "")
                if error_case:
                    # Determine color based on case
                    if "Case 4" in error_case or "No Error" in error_case:
                        case_color = "#28a745"  # Green
                        case_icon = "✅"
                    elif "Case 8" in error_case or "Underbilling" in error_case:
                        case_color = "#17a2b8"  # Blue
                        case_icon = "ℹ️"
                    else:
                        case_color = "#dc3545"  # Red
                        case_icon = "⚠️"
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {case_color}22, {case_color}11);
                        border-left: 4px solid {case_color};
                        padding: 1rem 1.5rem;
                        border-radius: 8px;
                        margin-bottom: 1rem;
                    ">
                        <h3 style="margin: 0 0 0.5rem 0; color: {case_color};">
                            {case_icon} Detected Error Case
                        </h3>
                        <p style="margin: 0; font-size: 1.1rem; font-weight: 500;">
                            {error_case}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.divider()
                
                # Summary section
                summary = final_state.get("audit_summary")
                if summary:
                    st.subheader("📝 Audit Summary")
                    st.markdown(summary)
                else:
                    st.warning("No summary generated. Check for errors.")
                
                # Error display
                if final_state.get("error"):
                    st.error(f"⚠️ Error: {final_state.get('error')}")
                
                # Expandable details
                with st.expander("🔍 View Detailed Data"):
                    tab1, tab2, tab3 = st.tabs(["Rated Data", "Parcel Info", "Agreements"])
                    
                    with tab1:
                        st.json(final_state.get("rated_data", {}))
                    
                    with tab2:
                        st.json(final_state.get("parcel_characteristics", {}))
                    
                    with tab3:
                        st.json(final_state.get("agreements", {}))
        
        except Exception as e:
            st.error(f"❌ Audit failed: {str(e)}")
            st.exception(e)
    
    else:
        # Welcome message when no audit is running
        st.markdown("""
        ### 👋 Welcome to the Rate Audit Analyser
        
        This tool uses a multi-agent AI system to analyze parcel shipping invoices and identify billing discrepancies.
        
        **How it works:**
        1. **Data Retrieval** - Fetches rated data, parcel characteristics, and agreements
        2. **Classification** - AI classifies the audit type (weight, zone, service, etc.)
        3. **Reasoning** - Determines the root cause with available data
        4. **Enrichment** - If needed, fetches additional context (loops until sufficient)
        5. **Summary** - Generates a professional audit report
        
        👈 **Enter shipment details in the sidebar and click "Run Audit Analysis" to begin.**
        """)
        
        # Sample results preview
        with st.expander("📊 See Sample Audit Result"):
            st.markdown("""
            **Audit Type**: BILL_WEIGHT
            
            **Finding Summary**: Carrier overbilled by 5 lbs on shipment weight.
            
            **Key Details**:
            • Billed Weight: 15 lbs
            • Actual Weight: 10 lbs
            • DIM Weight: 6.9 lbs (12" x 10" x 8" / 139)
            • Correct Billable Weight: 10 lbs
            • Overcharge Amount: $4.75
            
            **Recommendation**: File dispute with carrier for weight correction and refund.
            
            **Potential Recovery**: $4.75
            """)


if __name__ == "__main__":
    main()
