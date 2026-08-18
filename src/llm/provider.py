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
                
        # Enforce strict schema logic natively via Ollama
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a financial investigator classifying anomaly disclosures. Do not predict fraud. Classify disclosure completeness based ONLY on the evidence provided."},
                {"role": "user", "content": prompt}
            ],
            format=InvestigationResult.model_json_schema(),
            options={"temperature": 0.0}
        )
        
        parsed = InvestigationResult.model_validate_json(response.message.content)
        with open(cache_file, "w") as f:
            f.write(parsed.model_dump_json(indent=2))
        return parsed