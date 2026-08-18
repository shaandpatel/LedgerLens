from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

class AnomalyTrigger(BaseModel):
    ticker: str
    fiscal_year: int
    trigger_type: str
    severity: Literal["NORMAL", "MEDIUM", "HIGH", "CRITICAL"]
    divergence_value: float
    description: str
    sub_queries: List[str] = Field(..., description="Targeted queries for evidence clustering")

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
    disclosure_status: Literal[
        "explicitly_explained",
        "partially_explained",
        "no_relevant_explanation_found",
        "conflicting_evidence",
        "unable_to_determine"
    ]
    management_explanation_summary: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    cited_chunk_ids: List[str]

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return round(v, 4)