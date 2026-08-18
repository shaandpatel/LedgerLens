# LedgerLens
### Deterministic Financial Analytics + Evidence-Grounded RAG

**LedgerLens** is an AI-powered financial investigation workstation. It detects unusual financial patterns from structured metrics, retrieves relevant disclosures from company filings, and uses a local LLM to investigate whether management adequately explains the quantitative anomaly.

## Core Architecture

* **Anomaly-Driven RAG:** Deterministic financial analytics first identify a company-specific anomaly, which then drives targeted query generation and retrieval from relevant SEC filing sections rather than treating the system as a generic "chat with documents" application.
* **Hybrid Retrieval + Reranking:** Evidence is retrieved using BM25 lexical search and dense vector retrieval, followed by cross-encoder reranking. This combines exact financial terminology matching with semantic retrieval for disclosures that describe the same issue using different language.
* **Evidence-Grounded LLM Investigation:** A local LLM receives the quantitative anomaly and a bounded set of retrieved evidence, then produces structured findings using Pydantic schemas. Every conclusion is linked to citation IDs and source metadata so the UI can trace claims back to the original SEC filing.
* **Sector-Aware Financial Reasoning:** SEC XBRL data is normalized into a canonical schema and all financial calculations are performed deterministically in Python. Screening signals adapt to the company's business model, such as inventory/revenue divergence for manufacturers or deferred-revenue and receivables signals for software companies.
* **LLM/RAG Evaluation:** Retrieval and generation are evaluated separately. Retrieval is benchmarked using Recall@K and MRR, while LLM outputs are evaluated for structured-output validity, citation coverage, evidence grounding, quantitative consistency, and unsupported claims.
* **Local-First LLM Infrastructure:** The default inference path uses Ollama with a locally hosted model, allowing the complete RAG pipeline to run without paid inference APIs or sending SEC documents to an external LLM provider. The LLM layer is model-agnostic through a provider abstraction.

## Getting Started
1. `pip install -r requirements.txt`
2. Install [Ollama](https://ollama.com/) and pull the local model: `ollama pull llama3.2`
3. Generate the frozen evaluation dataset: `python scripts/setup_fixtures.py`
4. Run the fully offline test suite: `pytest tests/`
5. Run the offline retrieval & generation benchmark: `python scripts/evaluate.py`
6. Spin up the backend API: `uvicorn src.ledger_lens.api:app --reload`
7. Launch the Workstation UI: `streamlit run app/streamlit_app.py`