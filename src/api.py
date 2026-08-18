from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from src.analytics.engine import SectorAwareAnalyticsEngine
from src.llm.provider import LocalLLMProvider
from src.ingestion.sec_client import SECDataFetcher
from src.ingestion.html_parser import SECHTMLParser
from src.retrieval.engine import DynamicClusterRetrievalPipeline
from src.schemas import AnomalyTrigger


app = FastAPI(title="LedgerLens API")


# ============================================================
# INITIALIZE SERVICES
# ============================================================

engine = SectorAwareAnalyticsEngine()
llm = LocalLLMProvider(model="llama3.2")
sec_client = SECDataFetcher()
html_parser = SECHTMLParser()

print("Loading Local ML Models for Retrieval...")
retriever = DynamicClusterRetrievalPipeline(use_mock=False)
print("Models loaded successfully!")


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class LiveScreenRequest(BaseModel):
    ticker: str
    fiscal_year: int
    sector: str


class InvestigateRequest(BaseModel):
    triggers: List[AnomalyTrigger]


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "LedgerLens API is running!"
    }


# ============================================================
# SCREEN COMPANY
# ============================================================

@app.post("/api/screen/live")
async def screen_company_live(req: LiveScreenRequest):
    try:
        cur_data, prev_data = sec_client.fetch_financials(
            req.ticker,
            req.fiscal_year
        )

        triggers = engine.evaluate_triggers(
            ticker=req.ticker,
            fiscal_year=req.fiscal_year,
            sector=req.sector,
            cur=cur_data,
            prev=prev_data
        )

        return {
            "ticker": req.ticker,
            "fiscal_year": req.fiscal_year,
            "canonical_financials": {
                "current": cur_data,
                "previous": prev_data
            },
            "triggers": triggers
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# INVESTIGATE MULTIPLE ANOMALIES
# ============================================================

@app.post("/api/investigate")
async def investigate_anomalies(req: InvestigateRequest):

    if not req.triggers:
        raise HTTPException(
            status_code=400,
            detail="At least one anomaly trigger is required."
        )

    investigations = []

    try:

        # --------------------------------------------------------
        # 1. Fetch the filing ONCE
        # --------------------------------------------------------

        first_trigger = req.triggers[0]

        ticker = first_trigger.ticker
        fiscal_year = first_trigger.fiscal_year

        cik = sec_client.cik_map.get(ticker)

        if not cik:
            raise ValueError(
                f"CIK not found for {ticker}"
            )

        html_content = html_parser.fetch_10k_text_by_year(
            ticker,
            cik,
            fiscal_year
        )

        # --------------------------------------------------------
        # 2. Extract MD&A ONCE
        # --------------------------------------------------------

        mda_text = html_parser.extract_mda_section(
            html_content
        )

        chunks = html_parser.chunk_text(
            mda_text,
            ticker,
            "MD&A"
        )

        # --------------------------------------------------------
        # 3. Index the filing ONCE
        # --------------------------------------------------------

        retriever.index_chunks(chunks)

        # --------------------------------------------------------
        # 4. Investigate EACH anomaly independently
        # --------------------------------------------------------

        for trigger in req.triggers:

            try:

                # --------------------------------------------
                # Retrieval is driven by THIS anomaly
                # --------------------------------------------

                top_chunks = retriever.retrieve_for_anomaly(
                    trigger,
                    top_k_rerank=3
                )

                context_blocks = [
                    f"[Citation: {chunk.chunk_id}]\n"
                    f"{chunk.content}"
                    for chunk in top_chunks
                ]

                context_str = "\n\n".join(
                    context_blocks
                )

                # --------------------------------------------
                # LLM investigates only this anomaly
                # --------------------------------------------

                prompt = f"""
You are investigating a specific financial anomaly.

Target Anomaly:
{trigger.description}

Retrieved SEC Evidence:
{context_str}

Determine whether the retrieved evidence explains the
specific quantitative anomaly.

Return the required structured investigation output.

Important:
- Only use the retrieved evidence.
- Do not invent explanations.
- Cite the relevant evidence using the provided citation IDs.
- Distinguish between a causal explanation and generic discussion.
- Determine whether the impact is quantitatively supported.
"""

                result = llm.generate(
                    prompt=prompt
                )

                # --------------------------------------------
                # Deterministic classification
                # --------------------------------------------

                if (
                    result.metric_matched
                    and result.driver_identified
                    and result.quantified_impact
                ):
                    result.disclosure_status = (
                        "explicitly_explained"
                    )

                elif (
                    result.metric_matched
                    and result.driver_identified
                    and not result.quantified_impact
                ):
                    result.disclosure_status = (
                        "partially_explained"
                    )

                elif (
                    result.metric_matched
                    and not result.driver_identified
                    and not result.quantified_impact
                ):
                    result.disclosure_status = (
                        "no_relevant_explanation_found"
                    )

                else:
                    result.disclosure_status = (
                        "no_relevant_explanation_found"
                    )

                # --------------------------------------------
                # Store investigation
                # --------------------------------------------

                investigations.append({
                    "trigger": trigger,
                    "retrieved_citations": [
                        chunk.chunk_id
                        for chunk in top_chunks
                    ],
                    "investigation": result
                })

            except Exception as anomaly_error:

                # Don't let one failed anomaly kill the
                # investigation of all the others.

                investigations.append({
                    "trigger": trigger,
                    "error": str(anomaly_error)
                })

        # --------------------------------------------------------
        # 5. Return all investigations
        # --------------------------------------------------------

        return {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "anomaly_count": len(req.triggers),
            "investigations": investigations
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )