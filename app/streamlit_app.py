import streamlit as st
import requests

st.set_page_config(page_title="LedgerLens", layout="wide")
st.title("LedgerLens: Deterministic Analytics & Evidence-Grounded RAG")

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    ticker = st.selectbox("Company Ticker", ["TSLA", "MSFT", "AAPL", "NVDA", "AMZN", "GOOGL", "CRM"])
with col2:
    year = st.selectbox("Fiscal Year", [2025, 2024, 2023])
with col3:
    SECTOR_LOOKUP = {
        "TSLA": "Manufacturing",
        "AAPL": "Manufacturing",
        "NVDA": "Manufacturing",
        "AMZN": "Manufacturing", 
        "MSFT": "Software & Services",
        "GOOGL": "Software & Services",
        "CRM": "Software & Services"
    }
    
    default_sector = SECTOR_LOOKUP.get(ticker, "Manufacturing")
    
    # Allow the user to see the auto-detected sector, but override it if needed
    sector = st.selectbox(
        "Analytical Sector Model",
        ["Manufacturing", "Software & Services"],
        index=0 if default_sector == "Manufacturing" else 1
    )

st.markdown("---")

if st.button(f"Fetch Live SEC Data & Screen ({ticker} {year})"):
    payload = {
        "ticker": ticker,
        "fiscal_year": year,
        "sector": sector
    }
    
    with st.spinner("Fetching live XBRL facts from SEC EDGAR..."):
        try:
            resp = requests.post("http://localhost:8000/api/screen/live", json=payload).json()
            
            if "detail" in resp:
                st.error(f"API Error: {resp['detail']}")
            else:
                # Display the raw canonical data fetched from the SEC
                st.markdown("### Canonical Financial Facts (Normalized)")
                fin_cur = resp["canonical_financials"]["current"]
                fin_prev = resp["canonical_financials"]["previous"]
                
                # Create a clean metrics display
                m1, m2, m3 = st.columns(3)
                m1.metric("Revenue", f"${fin_cur.get('revenue', 0):,.0f}", f"{(fin_cur.get('revenue', 0) - fin_prev.get('revenue', 0)) / max(1, fin_prev.get('revenue', 1)) * 100:.1f}%")
                
                if sector == "Manufacturing":
                    m2.metric("Inventory", f"${fin_cur.get('inventory', 0):,.0f}", f"{(fin_cur.get('inventory', 0) - fin_prev.get('inventory', 0)) / max(1, fin_prev.get('inventory', 1)) * 100:.1f}%")
                else:
                    m2.metric("Deferred Revenue", f"${fin_cur.get('deferred_revenue', 0):,.0f}", f"{(fin_cur.get('deferred_revenue', 0) - fin_prev.get('deferred_revenue', 0)) / max(1, fin_prev.get('deferred_revenue', 1)) * 100:.1f}%")
                
                m3.metric("Accounts Receivable", f"${fin_cur.get('ar', 0):,.0f}", f"{(fin_cur.get('ar', 0) - fin_prev.get('ar', 0)) / max(1, fin_prev.get('ar', 1)) * 100:.1f}%")
                
                st.markdown("---")
                st.markdown("### Anomaly Scorecard")
                
                triggers = resp.get("triggers", [])
                if triggers:
                    # Store the first trigger in session state so the RAG button can access it
                    st.session_state['current_trigger'] = triggers[0]
                    
                    for t in triggers:
                        st.error(f"**{t['trigger_type']}** | Severity: {t['severity']}\n\n{t['description']}")
                        st.write(f"*Dynamic Sub-Queries generated for RAG:* {t['sub_queries']}")
                else:
                    st.success("No significant quantitative anomalies detected for this period based on sector rules.")
                    st.session_state['current_trigger'] = None

        except Exception as e:
            st.error(f"Connection Error: Make sure your FastAPI backend is running. Details: {e}")

# Only show the RAG button if we found a trigger
if st.session_state.get('current_trigger'):
    st.markdown("---")
    if st.button("Launch Targeted Local RAG Investigation"):
        trigger = st.session_state['current_trigger']
        
        with st.spinner("Downloading 10-K, chunking HTML, running Semantic Search & Calling LLM..."):
            try:
                # Removed mock text
                inv = requests.post(
                    "http://localhost:8000/api/investigate", 
                    json={"trigger": trigger}
                ).json()
                
                if "detail" in inv:
                    st.error(f"Backend Error: {inv['detail']}")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.success(f"**Classification:** {inv['disclosure_status'].upper()}")
                        st.write(f"**LLM Finding:** {inv['management_explanation_summary']}")
                        st.write("**Sources Cited:**", inv.get("cited_chunk_ids", []))
                    with col2:
                        st.write("**Chain of Thought Booleans:**")
                        st.json({
                            "metric_matched": inv.get("metric_matched"),
                            "driver_identified": inv.get("driver_identified"),
                            "quantified_impact": inv.get("quantified_impact")
                        })
            except Exception as e:
                st.error(f"Error connecting to backend for investigation: {e}")