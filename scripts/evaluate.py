import json
import requests
from sklearn.metrics import accuracy_score, classification_report

def run_end_to_end_evaluation(jsonl_path: str):
    print(f"Starting End-to-End Pipeline Evaluation using {jsonl_path}...")
    
    y_true_status = []
    y_pred_status = []
    
    boolean_matches = 0
    citation_success = 0
    total_cases = 0

    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip(): continue # Skip empty lines
            
            case = json.loads(line)
            total_cases += 1
            
            trigger_payload = case["trigger"]
            expected = case["expected_output"]
            
            print(f"\nTesting Case {total_cases}: {trigger_payload.get('ticker')} - {trigger_payload.get('trigger_type')}")
            
            try:
                # Hit your live local API
                resp = requests.post(
                    "http://localhost:8000/api/investigate", 
                    json={"trigger": trigger_payload}
                ).json()
                
                # CATCH API ERRORS GRACEFULLY
                if "detail" in resp:
                    print(f"API Error: {resp['detail']}")
                    y_true_status.append(expected["disclosure_status"].lower())
                    y_pred_status.append("api_error")
                    continue

                # Safely extract and normalize strings for scikit-learn
                actual_status = resp.get("disclosure_status", "unknown").lower()
                expected_status = expected["disclosure_status"].lower()
                
                y_true_status.append(expected_status)
                y_pred_status.append(actual_status)
                
                # Check Booleans
                actual_booleans = {
                    "metric_matched": resp.get("metric_matched"),
                    "driver_identified": resp.get("driver_identified"),
                    "quantified_impact": resp.get("quantified_impact")
                }
                if actual_booleans == expected["booleans"]:
                    boolean_matches += 1
                else:
                    print(f"Boolean mismatch. \n     Expected: {expected['booleans']} \n     Got: {actual_booleans}")
                    
                # Check Citations (Citation Hit Rate via Intersection)
                expected_citations = set(expected.get("expected_citations", []))
                actual_citations = set(resp.get("cited_chunk_ids", []))
                
                # If there is ANY overlap between expected and actual citations, it's a success
                intersection = expected_citations.intersection(actual_citations)
                if intersection:
                    citation_success += 1
                    print(f"Citation Hit! Overlap found: {intersection}")
                else:
                    print(f"Citation miss. Expected {expected_citations}, but got {actual_citations}")
                
                print(f"Status -> Expected: {expected_status} | Predicted: {actual_status}")

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
    print(f"Citation Precision: {(citation_success / total_cases) * 100:.1f}%")
    
    print("\nDetailed Classification Report:")
    print(classification_report(y_true_status, y_pred_status, zero_division=0))

if __name__ == "__main__":
    run_end_to_end_evaluation("data/evaluation/investigation_cases.jsonl")