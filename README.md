# LedgerLens
### Deterministic Financial Analytics + Evidence-Grounded RAG

**LedgerLens** is an AI-powered financial investigation workstation. It detects unusual financial patterns from structured metrics, retrieves relevant disclosures from company filings, and uses a local LLM to investigate whether management adequately explains the quantitative anomaly.

---

## Core Architecture

* **Anomaly-Driven RAG:** Deterministic financial analytics first identify a company-specific anomaly, which then drives targeted query generation and retrieval from relevant SEC filing sections rather than treating the system as a generic "chat with documents" application.
* **Hybrid Retrieval + Reranking:** Evidence is retrieved using BM25 lexical search and dense vector retrieval, followed by cross-encoder reranking. This combines exact financial terminology matching with semantic retrieval for disclosures that describe the same issue using different language.
* **Evidence-Grounded LLM Investigation:** A local LLM receives the quantitative anomaly and a bounded set of retrieved evidence, then produces structured findings using Pydantic schemas. Every conclusion is linked to citation IDs and source metadata so the UI can trace claims back to the original SEC filing.
* **Sector-Aware Financial Reasoning:** SEC XBRL data is normalized into a canonical schema and all financial calculations are performed deterministically in Python. Screening signals adapt to the company's business model, such as inventory/revenue divergence for manufacturers or deferred-revenue and receivables signals for software companies.
* **Retrieval Evaluation:** Retrieval accuracy is rigorously benchmarked using Recall@5 and Mean Reciprocal Rank (MRR) against a verified historical Golden Dataset to ensure high-precision surfacing of complex SEC filing disclosures.
* **Local-First LLM Infrastructure:** The default inference path uses Ollama with a locally hosted model, allowing the complete RAG pipeline to run without paid inference APIs or sending SEC documents to an external LLM provider. The LLM layer is model-agnostic through a provider abstraction.

---

## Evaluation & Performance Benchmarks

LedgerLens features an enterprise-grade offline evaluation suite running against a verified **7-case historical Golden Dataset** of real-world SEC 10-K anomalies (covering Tesla, Apple, and NVIDIA across fiscal years 2023–2025).

| Evaluation Metric | Benchmark Score | Description |
| :--- | :---: | :--- |
| **Recall@5** | **71.4%** | Percentage of cases where the ground-truth evidence chunk appeared in the top 5 retrieved results. |
| **Mean Reciprocal Rank (MRR)** | **0.548** | Measures the ranking quality of the first relevant retrieved citation. |
---

## Engineering and Architectural Highlights

* **Ingestion & Retrieval Decoupling:** Heavy I/O and compute operations (SEC EDGAR API fetching, multi-megabyte HTML parsing, and semantic text chunking) are completely decoupled from runtime query execution. The pipeline downloads, parses, and indexes a company's 10-K *once* per batch session, allowing high-throughput, concurrent anomaly investigation without redundant parsing overhead.
* **Deterministic vs. Probabilistic Separation (Neuro-Symbolic Design):** Strict separation is maintained between symbolic analytics and generative AI. All financial ratio calculations, trend screening rules, trigger generation, and final disclosure classification overrides are handled via deterministic Python logic. The LLM is strictly bounded to semantic evidence interpretation and structured extraction, eliminating mathematical hallucinations and ensuring auditing reliability.
* **Temporal State Isolation:** To prevent data leakage and cross-contamination across historical periods, SEC 10-K fetching uses explicit fiscal-year targeting (`fetch_10k_text_by_year`). This guarantees absolute synchronization between quantitative XBRL metric datasets and qualitative MD&A text corpora.
* **Bounded Context & Hybrid Search Fusion:** Combines lexical BM25 keyword search with dense semantic embedding retrieval, followed by dynamic clustering. Retrieved chunks are strictly capped and formatted with explicit citation IDs before passing to the LLM, maintaining strict prompt grounding.
* **End-to-End Evaluation Framework:** Fully automated offline evaluation pipeline measuring discrete system layers independently—benchmarking hybrid search precision via **Recall@5** and **MRR**, alongside structured schema validation and citation hit-rate accuracy against frozen real-world enterprise fixtures.

---

## Getting Started

1. `pip install -r requirements.txt` 
2. Install [Ollama](https://ollama.com/) and pull the local model: `ollama pull llama3.2` 
3. Spin up the backend API: `uvicorn src.api:app --reload`  
4. Run the offline retrieval & generation benchmark: `python3 -m scripts.evaluate` 
5. Launch the Workstation UI: `streamlit run app/streamlit_app.py` 