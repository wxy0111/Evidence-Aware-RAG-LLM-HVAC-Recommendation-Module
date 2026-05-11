# Reproducibility Notes

## Environment

Recommended Python version: 3.10+

Install dependencies:

```bash
pip install -r requirements.txt
```

## Required API Key

This module requires an OpenAI API key for LLM generation.

Set environment variable before running:

```bash
export OPENAI_API_KEY=your_key_here
```

## Demo Run

Run from repository root:

```bash
PYTHONPATH=src python src/demo_runner.py
```

## Data Paths

This public release uses the following default data paths:

- `data/knowledge/recommendation_knowledge_base.json`
- `data/feedback/user_feedback_examples.csv`
- `data/history/optimization_results_sample.csv`

These paths are defined in:

- `src/recommendation/paths.py`

## Notes

- This release is intended to reproduce the recommendation generation module only.
- It does not include the full energy prediction and optimization training pipeline.
