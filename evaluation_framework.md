# Evaluation Framework: Deterministic Silver Labels

Evaluating Large Language Models on complex financial text is inherently subjective. To prevent human bias in our evaluation benchmark, LedgerLens uses **Deterministic Silver Labels** (weak supervision) rather than subjective human "Gold Labels."

We decompose the qualitative assessment of "management explanation" into three objective, binary facts:
1. `driver_identified` (Boolean): Does the text name a specific operational cause? (e.g., "raw material costs")
2. `quantified_impact` (Boolean): Does the text assign a dollar amount or percentage to that driver?
3. `metric_matched` (Boolean): Does the text explicitly discuss the anomalous metric?

### Silver Label Heuristic Matrix
The evaluation harness deterministically maps these binary facts to the target classification:

| `metric_matched` | `driver_identified` | `quantified_impact` | **Derived Silver Label** |
| :---: | :---: | :---: | :--- |
| True | True | True | `explicitly_explained` |
| True | True | False | `partially_explained` |
| True | False | False | `no_relevant_explanation_found` |
| False | *Any* | *Any* | `no_relevant_explanation_found` |