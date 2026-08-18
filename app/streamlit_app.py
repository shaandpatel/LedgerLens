import streamlit as st
import requests


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="LedgerLens",
    layout="wide"
)

st.title("LedgerLens: Deterministic Analytics & Evidence-Grounded RAG")

st.markdown("---")


# ============================================================
# COMPANY / YEAR / SECTOR SELECTION
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

    default_sector = SECTOR_LOOKUP.get(
        ticker,
        "Manufacturing"
    )

    sector = st.selectbox(
        "Analytical Sector Model",
        [
            "Manufacturing",
            "Software & Services"
        ],
        index=(
            0
            if default_sector == "Manufacturing"
            else 1
        )
    )


st.markdown("---")


# ============================================================
# LIVE SCREENING
# ============================================================

if st.button(
    f"Fetch Live SEC Data & Screen ({ticker} {year})"
):

    payload = {
        "ticker": ticker,
        "fiscal_year": year,
        "sector": sector
    }

    with st.spinner(
        "Fetching live XBRL facts from SEC EDGAR..."
    ):

        try:

            response = requests.post(
                "http://localhost:8000/api/screen/live",
                json=payload
            )

            resp = response.json()

            if "detail" in resp:

                st.error(
                    f"API Error: {resp['detail']}"
                )

                st.session_state["current_triggers"] = []

            else:

                # ------------------------------------------------
                # Store ALL triggers
                # ------------------------------------------------

                triggers = resp.get(
                    "triggers",
                    []
                )

                st.session_state[
                    "current_triggers"
                ] = triggers

                # ------------------------------------------------
                # Canonical Financial Data
                # ------------------------------------------------

                st.markdown(
                    "### Canonical Financial Facts (Normalized)"
                )

                fin_cur = resp[
                    "canonical_financials"
                ]["current"]

                fin_prev = resp[
                    "canonical_financials"
                ]["previous"]

                # ------------------------------------------------
                # Helper for percentage changes
                # ------------------------------------------------

                def pct_change(
                    current,
                    previous
                ):

                    if previous in (None, 0):
                        return 0.0

                    return (
                        (current - previous)
                        / abs(previous)
                        * 100
                    )

                # ------------------------------------------------
                # Financial metrics
                # ------------------------------------------------

                revenue = fin_cur.get(
                    "revenue",
                    0
                )

                prev_revenue = fin_prev.get(
                    "revenue",
                    0
                )

                m1, m2, m3 = st.columns(3)

                m1.metric(
                    "Revenue",
                    f"${revenue:,.0f}",
                    f"{pct_change(revenue, prev_revenue):.1f}%"
                )

                if sector == "Manufacturing":

                    current_secondary = fin_cur.get(
                        "inventory",
                        0
                    )

                    previous_secondary = fin_prev.get(
                        "inventory",
                        0
                    )

                    m2.metric(
                        "Inventory",
                        f"${current_secondary:,.0f}",
                        f"{pct_change(current_secondary, previous_secondary):.1f}%"
                    )

                else:

                    current_secondary = fin_cur.get(
                        "deferred_revenue",
                        0
                    )

                    previous_secondary = fin_prev.get(
                        "deferred_revenue",
                        0
                    )

                    m2.metric(
                        "Deferred Revenue",
                        f"${current_secondary:,.0f}",
                        f"{pct_change(current_secondary, previous_secondary):.1f}%"
                    )

                current_ar = fin_cur.get(
                    "ar",
                    0
                )

                previous_ar = fin_prev.get(
                    "ar",
                    0
                )

                m3.metric(
                    "Accounts Receivable",
                    f"${current_ar:,.0f}",
                    f"{pct_change(current_ar, previous_ar):.1f}%"
                )

                # ------------------------------------------------
                # Anomaly Scorecard
                # ------------------------------------------------

                st.markdown("---")

                st.markdown(
                    "### Anomaly Scorecard"
                )

                if triggers:

                    st.warning(
                        f"{len(triggers)} quantitative "
                        f"anomal{'y' if len(triggers) == 1 else 'ies'} "
                        f"detected."
                    )

                    for i, trigger in enumerate(
                        triggers,
                        start=1
                    ):

                        with st.container(
                            border=True
                        ):

                            st.markdown(
                                f"#### Anomaly {i}: "
                                f"{trigger['trigger_type']}"
                            )

                            st.error(
                                f"**Severity:** "
                                f"{trigger['severity']}"
                            )

                            st.write(
                                trigger["description"]
                            )

                            sub_queries = trigger.get(
                                "sub_queries",
                                []
                            )

                            if sub_queries:

                                st.caption(
                                    "Dynamic RAG Sub-Queries"
                                )

                                for query in sub_queries:
                                    st.code(
                                        query,
                                        language=None
                                    )

                else:

                    st.success(
                        "No significant quantitative "
                        "anomalies detected for this period "
                        "based on sector rules."
                    )

        except Exception as e:

            st.error(
                "Connection Error: Make sure your "
                f"FastAPI backend is running.\n\n{e}"
            )


# ============================================================
# RAG INVESTIGATION
# ============================================================

current_triggers = st.session_state.get(
    "current_triggers",
    []
)


if current_triggers:

    st.markdown("---")

    st.markdown(
        "### Evidence-Grounded RAG Investigation"
    )

    st.write(
        f"Run an independent retrieval and LLM investigation "
        f"for each of the {len(current_triggers)} detected "
        f"anomal{'y' if len(current_triggers) == 1 else 'ies'}."
    )

    if st.button(
        "Launch Targeted Local RAG Investigation",
        type="primary"
    ):

        with st.spinner(
            "Downloading 10-K, extracting MD&A, "
            "running anomaly-specific retrieval, "
            "and calling local LLM..."
        ):

            try:

                # ------------------------------------------------
                # Send ALL anomalies to backend
                # ------------------------------------------------

                response = requests.post(
                    "http://localhost:8000/api/investigate",
                    json={
                        "triggers": current_triggers
                    }
                )

                inv = response.json()

                if "detail" in inv:

                    st.error(
                        f"Backend Error: {inv['detail']}"
                    )

                else:

                    investigations = inv.get(
                        "investigations",
                        []
                    )

                    st.success(
                        f"Completed {len(investigations)} "
                        f"independent anomaly investigations."
                    )

                    # ====================================================
                    # DISPLAY EACH INVESTIGATION
                    # ====================================================

                    for i, investigation in enumerate(
                        investigations,
                        start=1
                    ):

                        st.markdown("---")

                        trigger = investigation.get(
                            "trigger",
                            {}
                        )

                        result = investigation.get(
                            "investigation"
                        )

                        st.markdown(
                            f"## Investigation {i}"
                        )

                        st.markdown(
                            f"**{trigger.get('trigger_type', 'Unknown Anomaly')}**"
                        )

                        st.write(
                            trigger.get(
                                "description",
                                ""
                            )
                        )

                        # ------------------------------------------------
                        # Handle individual failure
                        # ------------------------------------------------

                        if "error" in investigation:

                            st.error(
                                "Investigation failed: "
                                + investigation["error"]
                            )

                            continue

                        if result is None:

                            st.warning(
                                "No investigation result returned."
                            )

                            continue

                        # ------------------------------------------------
                        # Classification + Finding
                        # ------------------------------------------------

                        col1, col2 = st.columns(
                            [2, 1]
                        )

                        with col1:

                            status = result.get(
                                "disclosure_status",
                                "unknown"
                            )

                            if status == "explicitly_explained":

                                st.success(
                                    f"**Classification:** "
                                    f"{status.upper()}"
                                )

                            elif status == "partially_explained":

                                st.warning(
                                    f"**Classification:** "
                                    f"{status.upper()}"
                                )

                            else:

                                st.error(
                                    f"**Classification:** "
                                    f"{status.upper()}"
                                )

                            st.markdown(
                                "**LLM Finding**"
                            )

                            st.write(
                                result.get(
                                    "management_explanation_summary",
                                    "No summary returned."
                                )
                            )

                        with col2:
                            citations = investigation.get(
                                "retrieved_citations",
                                []
                            )

                            st.metric(
                                "Evidence Chunks",
                                len(citations)
                            )

                        # ------------------------------------------------
                        # Structured investigation signals
                        # ------------------------------------------------

                        st.markdown(
                            "**Structured Investigation Signals**"
                        )

                        signal_col1, signal_col2, signal_col3 = (
                            st.columns(3)
                        )

                        with signal_col1:

                            st.metric(
                                "Metric Matched",
                                str(
                                    result.get(
                                        "metric_matched",
                                        False
                                    )
                                )
                            )

                        with signal_col2:

                            st.metric(
                                "Driver Identified",
                                str(
                                    result.get(
                                        "driver_identified",
                                        False
                                    )
                                )
                            )

                        with signal_col3:

                            st.metric(
                                "Quantified Impact",
                                str(
                                    result.get(
                                        "quantified_impact",
                                        False
                                    )
                                )
                            )

                        # ------------------------------------------------
                        # Retrieved evidence
                        # ------------------------------------------------

                        citations = investigation.get(
                            "retrieved_citations",
                            []
                        )

                        st.markdown(
                            "**Retrieved SEC Evidence**"
                        )

                        if citations:

                            for rank, citation in enumerate(
                                citations,
                                start=1
                            ):

                                st.code(
                                    f"{rank}. {citation}",
                                    language=None
                                )

                        else:

                            st.caption(
                                "No citation IDs returned."
                            )

                        # ------------------------------------------------
                        # Optional additional fields
                        # ------------------------------------------------

                        if result.get(
                            "cited_chunk_ids"
                        ):

                            with st.expander(
                                "LLM Citation Output"
                            ):

                                st.json(
                                    result[
                                        "cited_chunk_ids"
                                    ]
                                )

                        # ------------------------------------------------
                        # Raw structured result
                        # ------------------------------------------------

                        with st.expander(
                            "View Structured LLM Output"
                        ):

                            st.json(
                                result
                            )

            except Exception as e:

                st.error(
                    "Error connecting to backend "
                    f"for investigation: {e}"
                )