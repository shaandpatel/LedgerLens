import json
from src.retrieval.engine import DynamicClusterRetrievalPipeline
from src.llm.provider import LocalLLMProvider
from src.schemas import DocumentChunk, AnomalyTrigger

def main():
    print("Loading Offline Retrieval & Generative Evaluator...\n")
    
    with open("data/corpus/tsla_chunks.json", "r") as f:
        docs = [DocumentChunk(**c) for c in json.load(f)]
        
    retriever = DynamicClusterRetrievalPipeline(use_mock=True) # Swap to False to run locally
    retriever.index_chunks(docs)
    llm = LocalLLMProvider()
    
    with open("data/evaluation/investigation_cases.jsonl", "r") as f:
        cases = [json.loads(line) for line in f]
        
    for case in cases:
        print(f"Evaluating Case: {case['id']} | Target Silver Label: {case['target_silver_label']}")
        
        # 1. Retrieval
        trigger = AnomalyTrigger(ticker=case['ticker'], fiscal_year=2025, severity="HIGH", divergence_value=0.25, **case['trigger'])
        results = retriever.retrieve_for_anomaly(trigger, top_k_rerank=2)
        retrieved_ids = [r.chunk_id for r in results]
        recall_hit = any(g in retrieved_ids for g in case['gold_evidence_chunks'])
        
        # 2. Generation vs Silver Label
        context = " ".join([r.content for r in results])
        prompt = f"Target Anomaly: {trigger.description}\nEvidence:\n{context}\nEvaluate disclosure explicitly."
        prediction = llm.generate(prompt=prompt)
        
        llm_match = prediction.disclosure_status == case['target_silver_label']
        
        print(f"Recall@2: {'PASS' if recall_hit else 'FAIL'}")
        print(f"LLM Accuracy (vs Silver Label): {'PASS' if llm_match else 'FAIL'} (Predicted: {prediction.disclosure_status})\n")

if __name__ == "__main__":
    main()