from fastapi import FastAPI
from pydantic import BaseModel
from src.analytics.engine import SectorAwareAnalyticsEngine
from src.llm.provider import LocalLLMProvider

app = FastAPI(title="LedgerLens API")
engine = SectorAwareAnalyticsEngine()
llm = LocalLLMProvider(model="llama3.2")

class ScreenRequest(BaseModel):
    ticker: str
    sector: str
    cur_data: dict
    prev_data: dict

@app.post("/api/screen")
async def screen_company(req: ScreenRequest):
    return engine.evaluate_triggers(req.ticker, 2025, req.sector, req.cur_data, req.prev_data)

@app.post("/api/investigate")
async def investigate_anomaly(trigger_type: str, context: str):
    prompt = f"Target Anomaly: {trigger_type}\n\nRetrieved Evidence context:\n{context}\n\nDoes management explicitly explain this quantitative divergence? Provide your structured classification."
    return llm.generate(prompt=prompt)