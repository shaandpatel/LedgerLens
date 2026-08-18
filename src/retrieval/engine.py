import numpy as np
from typing import List
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from src.schemas import DocumentChunk, AnomalyTrigger

class DynamicClusterRetrievalPipeline:
    def __init__(self, use_mock: bool = False):
        self.chunks: List[DocumentChunk] = []
        self.use_mock = use_mock
        if not use_mock:
            self.dense_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def index_chunks(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([c.content.lower().split() for c in chunks])
        if not self.use_mock:
            self.dense_embeddings = self.dense_model.encode([c.content for c in chunks], convert_to_numpy=True, normalize_embeddings=True)

    def retrieve_for_anomaly(self, trigger: AnomalyTrigger, top_k_rerank: int = 3) -> List[DocumentChunk]:
        """Executes multi-faceted retrieval, clusters/deduplicates evidence, and reranks."""
        if not self.chunks or self.use_mock:
            return self.chunks[:top_k_rerank]

        candidate_indices = set()
        queries = [trigger.trigger_type.replace("_", " ")] + trigger.sub_queries
        
        for q in queries:
            bm25_scores = self.bm25.get_scores(q.lower().split())
            bm25_norm = (bm25_scores - np.min(bm25_scores)) / (np.max(bm25_scores) - np.min(bm25_scores) + 1e-6)
            
            query_emb = self.dense_model.encode(q, convert_to_numpy=True, normalize_embeddings=True)
            dense_scores = np.dot(self.dense_embeddings, query_emb)
            
            combined_scores = 0.4 * bm25_norm + 0.6 * dense_scores
            top_for_subquery = np.argsort(combined_scores)[::-1][:5]
            candidate_indices.update(top_for_subquery)

        unique_candidates = list(candidate_indices)
        candidate_pairs = [[trigger.description, self.chunks[i].content] for i in unique_candidates]
        rerank_scores = self.reranker.predict(candidate_pairs)
        
        best_local_indices = np.argsort(rerank_scores)[::-1][:top_k_rerank]
        return [self.chunks[unique_candidates[i]] for i in best_local_indices]