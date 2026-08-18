from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.analytics.engine import SectorAwareAnalyticsEngine
from src.llm.provider import LocalLLMProvider
from src.ingestion.sec_client import SECDataFetcher
from src.ingestion.html_parser import SECHTMLParser
from src.retrieval.engine import DynamicClusterRetrievalPipeline
from src.schemas import AnomalyTrigger

app = FastAPI(title="LedgerLens API")

# Initialize Singletons
engine = SectorAwareAnalyticsEngine()
llm = LocalLLMProvider(model="llama3.2")
sec_client = SECDataFetcher()
html_parser = SECHTMLParser()

print("Loading Local ML Models for Retrieval... (This takes a few seconds)")
retriever = DynamicClusterRetrievalPipeline(use_mock=False)
print("Models Loaded successfully!")

class LiveScreenRequest(BaseModel):
    ticker: str
    fiscal_year: int
    sector: str

@app.get("/")
async def root():
    return {"status": "online", "message": "LedgerLens API is running!"}

@app.post("/api/screen/live")
async def screen_company_live(req: LiveScreenRequest):
    try:
        cur_data, prev_data = sec_client.fetch_financials(req.ticker, req.fiscal_year)
        triggers = engine.evaluate_triggers(
            ticker=req.ticker, 
            fiscal_year=req.fiscal_year, 
            sector=req.sector, 
            cur=cur_data, 
            prev=prev_data
        )
        return {
            "canonical_financials": {"current": cur_data, "previous": prev_data},
            "triggers": triggers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InvestigateRequest(BaseModel):
    trigger: AnomalyTrigger

@app.post("/api/investigate")
async def investigate_anomaly(req: InvestigateRequest):
    try:
        ticker = req.trigger.ticker
        cik = sec_client.cik_map.get(ticker)
        if not cik:
            raise ValueError(f"CIK not found for {ticker}")

        html_content = html_parser.fetch_latest_10k_text(ticker, cik)
        mda_text = html_parser.extract_mda_section(html_content)
        chunks = html_parser.chunk_text(mda_text, ticker, "MD&A")

        retriever.index_chunks(chunks)
        top_chunks = retriever.retrieve_for_anomaly(req.trigger, top_k_rerank=3)

        context_blocks = [f"[Citation: {c.chunk_id}]\n{c.content}" for c in top_chunks]
        context_str = "\n\n".join(context_blocks)
        
        prompt = f"Target Anomaly: {req.trigger.description}\n\nRetrieved Evidence context:\n{context_str}\n\nDoes management explicitly explain this quantitative divergence? Provide your structured classification."
        
        # 1. Generate the raw LLM response
        result = llm.generate(prompt=prompt)
        
        # 2. DETERMINISTIC OVERRIDE: Enforce the Heuristic Matrix in Python
        if result.metric_matched and result.driver_identified and result.quantified_impact:
            result.disclosure_status = "explicitly_explained"
        elif result.metric_matched and result.driver_identified and not result.quantified_impact:
            result.disclosure_status = "partially_explained"
        elif result.metric_matched and not result.driver_identified and not result.quantified_impact:
            result.disclosure_status = "no_relevant_explanation_found"
        else:
            result.disclosure_status = "no_relevant_explanation_found"
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))