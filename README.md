# Evidence-Aware RAG-LLM HVAC Recommendation Module

A lightweight public release of the **LLM-based recommendation generation module** for HVAC energy-saving suggestions.

This repository focuses only on the **recommendation generation component** and excludes the full energy prediction and optimization training system.

---

## Highlights

- Rule-constrained action interpretation
- Multi-source evidence retrieval
- Historical case retrieval and user feedback retrieval
- User preference profiling
- Two-stage LLM generation
- Validation and auto-repair
- Lightweight public dataset examples

---

## What is included

This repository includes the public-facing recommendation generation pipeline:

1. **Action Construction**
2. **Evidence Retrieval**
3. **Evidence Selection and Summarization**
4. **Two-Stage LLM Generation**
5. **Validation and Repair**

This repository does **not** include:
- LSTM / RL training pipeline
- Full building energy prediction models
- Private deployment assets
- Full internal experimental environment

---

## Method Overview

The recommendation module follows a rule-constrained and evidence-aware pipeline:

- A fixed candidate action plan is first constructed
- Relevant evidence is retrieved from:
  - rule knowledge base
  - historical optimization cases
  - user feedback memory
- Retrieved evidence is filtered and summarized
- A compact user preference profile is built
- The LLM then generates the recommendation in **two stages**:
  - **Planning stage**: generate structured JSON clauses
  - **Realization stage**: compose final natural-language recommendation text
- The generated output is validated and automatically repaired when necessary

This design separates **action planning** from **language realization**.
The LLM does not directly decide the HVAC control action.

---

## Repository Structure

```bash
.
├── README.md
├── LICENSE
├── requirements.txt
├── src/
│   ├── demo_runner.py
│   └── recommendation/
│       ├── __init__.py
│       ├── paths.py
│       ├── action_constructor.py
│       ├── action_schema.py
│       ├── evaluate.py
│       ├── evidence.py
│       ├── evidence_pipeline.py
│       ├── feedback_retriever.py
│       ├── generator.py
│       ├── history_retriever.py
│       ├── policy.py
│       ├── rag_retriever.py
│       ├── retriever.py
│       ├── user_feedback_store.py
│       ├── user_profile.py
│       └── validator.py
├── data/
│   ├── knowledge/
│   │   └── recommendation_knowledge_base.json
│   ├── feedback/
│   │   └── user_feedback_examples.csv
│   ├── history/
│   │   └── optimization_results_sample.csv
│   └── examples/
│       └── recommendation_evidence_aware_rag_llm_sample.csv
├── docs/
│   ├── method_overview.md
│   ├── dataset_description.md
│   └── reproducibility.md
└── outputs/
```

---

## Datasets Included

### Rule Knowledge Base
`data/knowledge/recommendation_knowledge_base.json`

A structured knowledge base containing recommendation-support rules such as:
- ventilation rules
- window opening constraints
- comfort-energy tradeoff guidance
- gradual adjustment principles

### Historical Cases
`data/history/optimization_results_sample.csv`

Sample historical optimization cases used for retrieval-augmented recommendation generation.

### User Feedback Memory
`data/feedback/user_feedback_examples.csv`

Sample user feedback records used for preference retrieval and user profile construction.

### Example Output
`data/examples/recommendation_evidence_aware_rag_llm_sample.csv`

Example generated recommendations and metadata fields.

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Quick Start

Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your_key_here
```

Run the demo from the repository root:

```bash
PYTHONPATH=src python src/demo_runner.py
```

---

## Documentation

See:
- `docs/method_overview.md`
- `docs/dataset_description.md`
- `docs/reproducibility.md`

---

## Intended Use

This repository is designed for:
- paper reproducibility of the recommendation generation module
- method illustration for evidence-aware HVAC recommendation generation
- public release of the LLM-based recommendation component only

---

## Citation

If you use this repository in academic work, please cite the associated paper.
