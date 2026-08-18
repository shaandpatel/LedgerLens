import hashlib, json, os, ollama
from src.schemas import InvestigationResult

class LocalLLMProvider:
    def __init__(self, cache_dir: str = ".cache/llm", model: str = "llama3.2"):
        self.cache_dir = cache_dir
        self.model = model
        os.makedirs(cache_dir, exist_ok=True)

    def generate(self, prompt: str) -> InvestigationResult:
        cache_key = hashlib.sha256(f"{self.model}:{prompt}".encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return InvestigationResult.model_validate(json.load(f))
                
        # Inject the exact framework logic into the system prompt
        system_prompt = """You are a forensic financial investigator evaluating SEC disclosures. 
You must strictly follow this Heuristic Matrix to determine the final disclosure_status:

1. Evaluate three boolean facts based ONLY on the provided evidence:
   - metric_matched: Is the specific anomalous metric discussed?
   - driver_identified: Is a specific causal driver named?
   - quantified_impact: Is a dollar amount or percentage attached to that driver?

2. Map those facts to the disclosure_status:
   - If metric=True, driver=True, quantified=True -> 'explicitly_explained'
   - If metric=True, driver=True, quantified=False -> 'partially_explained'
   - If metric=True, driver=False, quantified=False -> 'no_relevant_explanation_found'
   - If metric=False -> 'no_relevant_explanation_found'

Do not predict fraud or infer intent. Stick strictly to the evidence."""

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            format=InvestigationResult.model_json_schema(),
            options={"temperature": 0.0}
        )
        
        parsed = InvestigationResult.model_validate_json(response.message.content)
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(parsed.model_dump_json(indent=2))
        return parsed