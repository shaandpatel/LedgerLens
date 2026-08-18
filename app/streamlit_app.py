import streamlit as st
import requests

st.set_page_config(page_title="LedgerLens", layout="wide")
st.title("LedgerLens: Deterministic Analytics & Evidence-Grounded RAG")

col1, col2 = st.columns(2)
with col1:
    ticker = st.selectbox("Company", ["TSLA", "MSFT"])
with col2:
    sector = "Manufacturing" if ticker == "TSLA" else "SaaS"
    st.info(f"Detected Sector: **{sector}**")

if st.button(f"Run Sector-Aware Screening ({ticker} 2025)"):
    # Mock Canonical Data
    payload = {
        "ticker": ticker,
        "sector": sector,
        "cur_data": {"revenue": 108.3, "inventory": 134.1, "deferred_revenue": 110.0},
        "prev_data": {"revenue": 100.0, "inventory": 100.0, "deferred_revenue": 100.0}
    }
    
    with st.spinner("Calculating deterministic anomalies..."):
        resp = requests.post("http://localhost:8000/api/screen", json=payload).json()
    
    if resp:
        trigger = resp[0]
        st.error(f"**{trigger['trigger_type']}** | Severity: {trigger['severity']}\n\n{trigger['description']}")
        st.write(f"*Dynamic Sub-Queries for RAG:* {trigger['sub_queries']}")
        
        if st.button("Launch Targeted Local RAG Investigation"):
            with st.spinner("Retrieving via Dense/BM25/Cross-Encoder & Calling Local LLM..."):
                context = "Inventories increased by $2.1 billion, primarily due to raw material cost inflation."
                inv = requests.post(f"http://localhost:8000/api/investigate?trigger_type={trigger['trigger_type']}&context={context}").json()
            
            st.success(f"**Classification:** {inv['disclosure_status'].upper()}")
            st.write(f"**LLM Finding:** {inv['management_explanation_summary']}")
    else:
        st.success("No anomalies detected for this sector profile.")