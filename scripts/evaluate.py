import json
import requests
from sklearn.metrics import accuracy_score, classification_report

def parse_expected_citations(raw_citations):
    """Flattens and splits citation lists even if comma-separated in a single string."""
    if not raw_citations:
        return []
    flattened = []
    for item in raw_citations:
        if isinstance(item, str) and "," in item:
            flattened.extend([c.strip() for c in item.split(",")])
        else:
            flattened.append(str(item).strip())
    return flattened

def calculate_retrieval_metrics(raw_expected_citations, retrieved_chunk_ids, k=5):
    """Calculates Recall@K and Mean Reciprocal Rank (MRR) with robust parsing."""
    expected_citations = parse_expected_citations(raw_expected_citations)
    expected_set = set(expected_citations)
    
    # Recall@K: Did at least one expected citation appear in top K retrieved chunks?
    top_k_retrieved = retrieved_chunk_ids[:k]
    recall_at_k = 1 if any(chunk_id in expected_set for chunk_id in top_k_retrieved) else 0
    
    # MRR: 1 / rank of the first relevant chunk
    mrr = 0.0
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in expected_set:
            mrr = 1.0 / rank
            break
            
    return recall_at_k, mrr, expected_citations

def run_end_to_end_evaluation(jsonl_path: str):
    print(f"Starting End-to-End Pipeline Evaluation using {jsonl_path}...")
    
    y_true_status = []
    y_pred_status = []
    
    boolean_matches = 0
    citation_success = 0
    total_recall_at_5 = 0
    total_mrr = 0.0
    total_cases = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue # Skip empty lines
            
            case = json.loads(line)
            total_cases += 1
            
            # Robust parsing: Support both nested and flat JSONL fixture formats
            if "trigger" in case:
                trigger_payload = case["trigger"]
            else:
                trigger_payload = {
                    "ticker": case.get("ticker"),
                    "fiscal_year": case.get("fiscal_year"),
                    "sector": case.get("sector"),
                    "description": case.get("trigger_description") or case.get("description"),
                    "trigger_type": case.get("trigger_type", "INVENTORY_SALES_DIVERGENCE"),
                    "severity": case.get("severity", "HIGH"),
                    "divergence_value": case.get("divergence_value", 1.0),
                    "sub_queries": case.get("sub_queries", [])
                }
                
            if "expected_output" in case:
                expected = case["expected_output"]
            else:
                expected = {
                    "disclosure_status": case.get("expected_status", "explicitly_explained"),
                    "booleans": case.get("booleans", {
                        "metric_matched": True,
                        "driver_identified": True,
                        "quantified_impact": True
                    }),
                    "expected_citations": case.get("expected_citations", [])
                }
            
            print(f"\nTesting Case {total_cases}: {trigger_payload.get('ticker')} - {trigger_payload.get('trigger_type', 'ANOMALY')}")
            
            try:
                # Hit your live local API using the batch payload structure
                resp = requests.post(
                    "http://localhost:8000/api/investigate", 
                    json={"triggers": [trigger_payload]}
                ).json()
                
                # CATCH API ERRORS GRACEFULLY
                if "detail" in resp:
                    print(f"API Error: {resp['detail']}")
                    y_true_status.append(expected["disclosure_status"].lower())
                    y_pred_status.append("api_error")
                    continue

                # Unpack the nested investigation result from the batch response structure
                investigations = resp.get("investigations", [])
                if not investigations or "error" in investigations[0]:
                    err_msg = investigations[0].get("error", "Unknown error") if investigations else "No investigations returned"
                    print(f"Investigation Error: {err_msg}")
                    y_true_status.append(expected["disclosure_status"].lower())
                    y_pred_status.append("api_error")
                    continue
                    
                inv_data = investigations[0]
                actual_result = inv_data.get("investigation", {})
                retrieved_chunk_ids = inv_data.get("retrieved_citations", [])

                # Safely extract and normalize strings for scikit-learn
                actual_status = actual_result.get("disclosure_status", "unknown").lower()
                expected_status = expected["disclosure_status"].lower()
                
                y_true_status.append(expected_status)
                y_pred_status.append(actual_status)
                
                # Check Booleans (if present in expected schema)
                if "booleans" in expected:
                    actual_booleans = {
                        "metric_matched": actual_result.get("metric_matched"),
                        "driver_identified": actual_result.get("driver_identified"),
                        "quantified_impact": actual_result.get("quantified_impact")
                    }
                    if actual_booleans == expected["booleans"]:
                        boolean_matches += 1
                    else:
                        print(f"Boolean mismatch. \n     Expected: {expected['booleans']} \n     Got: {actual_booleans}")
                else:
                    boolean_matches += 1
                    
                # --- Retrieval Metrics: Recall@5 & MRR ---
                raw_expected_citations = expected.get("expected_citations", [])
                recall, mrr, parsed_expected_citations = calculate_retrieval_metrics(raw_expected_citations, retrieved_chunk_ids, k=5)
                total_recall_at_5 += recall
                total_mrr += mrr
                
                # Check Citations (Citation Hit Rate via Intersection of LLM cited chunks)
                actual_citations = set(actual_result.get("cited_chunk_ids", []))
                intersection = set(parsed_expected_citations).intersection(actual_citations)
                if intersection:
                    citation_success += 1
                    print(f"Citation Hit! Overlap found: {intersection}")
                else:
                    print(f"Citation miss. Expected {parsed_expected_citations}, but got {actual_citations}")
                
                print(f"Status -> Expected: {expected_status} | Predicted: {actual_status} | Recall@5: {recall} | MRR: {mrr:.2f}")

            except requests.exceptions.ConnectionError:
                print("Failed to connect! Is your FastAPI server running?")
                return
            except Exception as e:
                print(f"Script Error: {e}")
                
    if total_cases == 0:
        print("No test cases found in JSONL.")
        return

    # Calculate and Print Final Metrics
    print("\n" + "="*50)
    print("LEDGERLENS EVALUATION METRICS")
    print("="*50)
    
    print(f"End-to-End Classification Accuracy: {accuracy_score(y_true_status, y_pred_status) * 100:.1f}%")
    print(f"Chain-of-Thought (Boolean) Exact Match: {(boolean_matches / total_cases) * 100:.1f}%")
    print(f"Citation Precision (Hit Rate): {(citation_success / total_cases) * 100:.1f}%")
    print(f"Recall@5: {(total_recall_at_5 / total_cases) * 100:.1f}%")
    print(f"Mean Reciprocal Rank (MRR): {(total_mrr / total_cases):.3f}")
    
    print("\nDetailed Classification Report:")
    print(classification_report(y_true_status, y_pred_status, zero_division=0))

if __name__ == "__main__":
    run_end_to_end_evaluation("data/evaluation/investigation_cases.jsonl")