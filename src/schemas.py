from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

class AnomalyTrigger(BaseModel):
    ticker: str
    fiscal_year: int
    trigger_type: str = "ANOMALY"
    severity: str = "MEDIUM"
    divergence_value: float = 0.0
    description: str
    sub_queries: List[str] = []

class DocumentChunk(BaseModel):
    chunk_id: str
    ticker: str
    section: str
    content: str

class RetrievedEvidence(BaseModel):
    chunk_id: str
    content: str
    dense_score: float
    bm25_score: float
    rerank_score: float

class InvestigationResult(BaseModel):
    ticker: str
    trigger_type: str
    
    # --- New Chain-of-Thought Booleans from evaluation_framework.md ---
    metric_matched: bool = Field(..., description="Does the text explicitly discuss the anomalous metric?")
    driver_identified: bool = Field(..., description="Does the text name a specific operational cause/driver?")
    quantified_impact: bool = Field(..., description="Does the text assign a dollar amount or percentage to that driver?")
    # ------------------------------------------------------------------

    disclosure_status: Literal[
        "explicitly_explained",
        "partially_explained",
        "no_relevant_explanation_found",
        "conflicting_evidence",
        "unable_to_determine"
    ]
    management_explanation_summary: str
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    cited_chunk_ids: List[str]

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return round(v, 4)