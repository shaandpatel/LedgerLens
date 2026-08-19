import streamlit as st
import requests

# ============================================================
# PAGE CONFIG & PROFESSIONAL STYLING
# ============================================================

st.set_page_config(
    page_title="LedgerLens | Financial Investigation Workstation",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a clean, non-generic terminal/workstation aesthetic
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button[kind="primary"] {
        background-color: #2563eb;
        color: white;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #1d4ed8;
    }
    div.stMetric {
        background: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    .anomaly-card {
        background: #161b22;
        border-left: 4px solid #ef4444;
        padding: 16px;
        border-radius: 4px;
        margin-bottom: 12px;
    }
    .status-badge-explicit {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .status-badge-partial {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid rgba(234, 179, 8, 0.3);
    }
    .status-badge-none {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER SECTION
# ============================================================

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("### LedgerLens")
    st.caption("Deterministic Financial Analytics & Evidence-Grounded RAG Workstation")
with col_h2:
    st.markdown("<div style='text-align: right; padding-top: 10px;'><span style='background: #1f2937; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; color: #9ca3af; border: 1px solid #374151;'>v1.0-Enterprise</span></div>", unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# WORKSTATION CONTROLS (SIDEBAR / TOP PANEL)
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.selectbox(
        "Company Ticker",
        ["TSLA", "MSFT", "AAPL", "NVDA", "AMZN", "GOOGL", "CRM"]
    )

with col2:
    year = st.selectbox(
        "Fiscal Year",
        [2025, 2024, 2023]
    )

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

    sector = st.selectbox(
        "Analytical Sector Model",
        ["Manufacturing", "Software & Services"],
        index=(0 if default_sector == "Manufacturing" else 1)
    )

st.markdown("")

# Primary action button
fetch_clicked = st.button(
    f"Fetch SEC XBRL & Screen ({ticker} - FY{year})",
    type="primary"
)

st.markdown("---")

# ============================================================
# LIVE SCREENING LOGIC
# ============================================================

if fetch_clicked:
    payload = {
        "ticker": ticker,
        "fiscal_year": year,
        "sector": sector
    }

    with st.spinner("Querying SEC EDGAR API and running deterministic rules..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/screen/live",
                json=payload
            )
            resp = response.json()

            if "detail" in resp:
                st.error(f"API Error: {resp['detail']}")
                st.session_state["current_triggers"] = []
            else:
                triggers = resp.get("triggers", [])
                st.session_state["current_triggers"] = triggers

                # ------------------------------------------------
                # Canonical Financial Data Section
                # ------------------------------------------------
                st.markdown("#### Normalized Financial Facts")
                
                fin_cur = resp["canonical_financials"]["current"]
                fin_prev = resp["canonical_financials"]["previous"]

                def pct_change(current, previous):
                    if previous in (None, 0):
                        return 0.0
                    return ((current - previous) / abs(previous)) * 100

                revenue = fin_cur.get("revenue", 0)
                prev_revenue = fin_prev.get("revenue", 0)

                m1, m2, m3 = st.columns(3)

                m1.metric(
                    "Revenue",
                    f"${revenue:,.0f}",
                    f"{pct_change(revenue, prev_revenue):.1f}%"
                )

                if sector == "Manufacturing":
                    current_secondary = fin_cur.get("inventory", 0)
                    previous_secondary = fin_prev.get("inventory", 0)
                    m2.metric(
                        "Inventory",
                        f"${current_secondary:,.0f}",
                        f"{pct_change(current_secondary, previous_secondary):.1f}%"
                    )
                else:
                    current_secondary = fin_cur.get("deferred_revenue", 0)
                    previous_secondary = fin_prev.get("deferred_revenue", 0)
                    m2.metric(
                        "Deferred Revenue",
                        f"${current_secondary:,.0f}",
                        f"{pct_change(current_secondary, previous_secondary):.1f}%"
                    )

                current_ar = fin_cur.get("ar", 0)
                previous_ar = fin_prev.get("ar", 0)
                m3.metric(
                    "Accounts Receivable",
                    f"${current_ar:,.0f}",
                    f"{pct_change(current_ar, previous_ar):.1f}%"
                )

                # ------------------------------------------------
                # Anomaly Scorecard
                # ------------------------------------------------
                st.markdown("")
                st.markdown("#### Screening Anomaly Scorecard")

                if triggers:
                    st.info(f"Identified {len(triggers)} financial anomal{'y' if len(triggers) == 1 else 'ies'} requiring audit.")

                    for i, trigger in enumerate(triggers, start=1):
                        with st.container(border=True):
                            col_t1, col_t2 = st.columns([3, 1])
                            with col_t1:
                                st.markdown(f"**Anomaly {i}: {trigger['trigger_type']}**")
                            with col_t2:
                                st.markdown(f"<div style='text-align: right;'><span style='background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;'>SEVERITY: {trigger['severity']}</span></div>", unsafe_allow_html=True)

                            st.write(trigger["description"])

                            sub_queries = trigger.get("sub_queries", [])
                            if sub_queries:
                                with st.expander("Generated Dynamic RAG Sub-Queries"):
                                    for query in sub_queries:
                                        st.code(query, language=None)
                else:
                    st.success("No significant quantitative anomalies detected for this filing period under current sector rules.")

        except Exception as e:
            st.error(f"Connection Error: Ensure your FastAPI backend is running.\n\n{e}")


# ============================================================
# RAG INVESTIGATION SECTION
# ============================================================

current_triggers = st.session_state.get("current_triggers", [])

if current_triggers:
    st.markdown("---")
    st.markdown("#### Evidence-Grounded RAG Investigation")
    st.write(f"Execute targeted multi-step retrieval and local LLM verification across the {len(current_triggers)} screened anomal{'y' if len(current_triggers) == 1 else 'ies'}.")

    if st.button("Launch Targeted Local RAG Investigation", type="primary"):
        with st.spinner("Parsing 10-K filing, executing hybrid retrieval & cross-encoder reranking, and querying local LLM..."):
            try:
                response = requests.post(
                    "http://localhost:8000/api/investigate",
                    json={"triggers": current_triggers}
                )
                inv = response.json()

                if "detail" in inv:
                    st.error(f"Backend Error: {inv['detail']}")
                else:
                    investigations = inv.get("investigations", [])
                    st.success(f"Successfully completed {len(investigations)} audit investigations.")

                    for i, investigation in enumerate(investigations, start=1):
                        st.markdown("---")

                        trigger = investigation.get("trigger", {})
                        result = investigation.get("investigation")

                        st.markdown(f"##### Investigation #{i}: {trigger.get('trigger_type', 'Unknown Anomaly')}")
                        st.caption(trigger.get("description", ""))

                        if "error" in investigation:
                            st.error(f"Investigation failed: {investigation['error']}")
                            continue

                        if result is None:
                            st.warning("No investigation result returned.")
                            continue

                        # Status badge display
                        status = result.get("disclosure_status", "unknown").lower()
                        if status == "explicitly_explained":
                            badge_html = f"<span class='status-badge-explicit'>{status.upper()}</span>"
                        elif status == "partially_explained":
                            badge_html = f"<span class='status-badge-partial'>{status.upper()}</span>"
                        else:
                            badge_html = f"<span class='status-badge-none'>{status.upper()}</span>"

                        col_res1, col_res2 = st.columns([3, 1])
                        with col_res1:
                            st.markdown(f"**Classification Status:** {badge_html}", unsafe_allow_html=True)
                            st.markdown("")
                            st.markdown("**Management Explanation Summary**")
                            st.write(result.get("management_explanation_summary", "No summary returned."))
                        
                        with col_res2:
                            citations = investigation.get("retrieved_citations", [])
                            st.metric("Retrieved Evidence Chunks", len(citations))

                        # Structured signals
                        st.markdown("")
                        st.markdown("**Structured Evaluation Signals**")
                        sig1, sig2, sig3 = st.columns(3)
                        sig1.metric("Metric Matched", str(result.get("metric_matched", False)))
                        sig2.metric("Driver Identified", str(result.get("driver_identified", False)))
                        sig3.metric("Quantified Impact", str(result.get("quantified_impact", False)))

                        # Retrieved Evidence view
                        st.markdown("")
                        st.markdown("**Retrieved SEC Evidence Chunks**")
                        if citations:
                            for rank, citation in enumerate(citations, start=1):
                                st.code(f"[{rank}] ID: {citation}", language=None)
                        else:
                            st.caption("No citation IDs returned.")

                        # Expander views
                        if result.get("cited_chunk_ids"):
                            with st.expander("LLM Citation Trace"):
                                st.json(result["cited_chunk_ids"])

                        with st.expander("Raw Structured JSON Output"):
                            st.json(result)

            except Exception as e:
                st.error(f"Error connecting to backend for investigation: {e}")