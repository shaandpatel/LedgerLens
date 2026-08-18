import os, json

os.makedirs("data/evaluation", exist_ok=True)
os.makedirs("data/corpus", exist_ok=True)

def derive_silver_label(criteria: dict) -> str:
    """Deterministically maps boolean facts to a weak-supervision classification label."""
    if not criteria.get("metric_matched", False): return "no_relevant_explanation_found"
    if criteria.get("driver_identified") and criteria.get("quantified_impact"): return "explicitly_explained"
    if criteria.get("driver_identified") and not criteria.get("quantified_impact"): return "partially_explained"
    return "no_relevant_explanation_found"

cases = [
    {
        "id": "tsla_2025_inv",
        "ticker": "TSLA",
        "trigger": {
            "trigger_type": "INVENTORY_SALES_DIVERGENCE",
            "description": "Inventory grew 34.1% YoY vs Revenue 8.3% YoY.",
            "sub_queries": ["raw material cost", "supply chain"]
        },
        "gold_evidence_chunks": ["TSLA_2025_ITEM7_0042"],
        "silver_label_criteria": {
            "metric_matched": True, "driver_identified": True, "quantified_impact": True
        }
    }
]

for c in cases:
    c["target_silver_label"] = derive_silver_label(c["silver_label_criteria"])

with open("data/evaluation/investigation_cases.jsonl", "w") as f:
    for c in cases: f.write(json.dumps(c) + "\n")

chunks = [
    {"chunk_id": "TSLA_2025_ITEM7_0042", "ticker": "TSLA", "section": "MD&A", "content": "Inventories increased by $2.1 billion, primarily due to raw material cost inflation."}
]
with open("data/corpus/tsla_chunks.json", "w") as f: json.dump(chunks, f)

print("✅ Frozen fixtures generated with Deterministic Silver Labels.")