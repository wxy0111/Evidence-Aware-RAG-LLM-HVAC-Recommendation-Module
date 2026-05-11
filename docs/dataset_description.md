# Dataset Description

This repository includes only the datasets required by the public recommendation generation module.

## 1. Rule Knowledge Base

**File:** `data/knowledge/recommendation_knowledge_base.json`

This JSON file stores structured recommendation-support rules.
Each entry typically contains:
- `id`
- `category`
- `title`
- `conditions`
- `guidance`

These rules are used during retrieval and evidence construction.

## 2. Historical Case Dataset

**File:** `data/history/optimization_results_sample.csv`

This CSV file contains sample historical optimization cases used for retrieval.
Typical fields include:
- `timestamp`
- `current_temp`
- `indoor_temp`
- `outdoor_temp`
- `optimal_temp`
- `original_predicted_energy`
- `optimized_energy`
- `optimization_type`

These cases provide experience-based evidence for recommendation generation.

## 3. User Feedback Dataset

**File:** `data/feedback/user_feedback_examples.csv`

This CSV file contains sample user feedback records.
It supports:
- user preference retrieval
- preference profile construction
- recommendation personalization

Typical fields include:
- `feedback_category`
- `feedback_type`
- `preference_tag`
- `accepted`
- `temp_setpoint_c`
- `window_action`
- `ac_switch`
- `prefers_brief_message`
- `prefers_reasoning`
- `prefers_soft_tone`
- `prefers_gradual_adjustment`

## 4. Example Recommendation Output

**File:** `data/examples/recommendation_evidence_aware_rag_llm_sample.csv`

This file contains example generated recommendations and metadata fields, such as:
- evidence counts
- evidence trace
- personalization profile
- planning JSON
- validation results

It is included to help users understand the output format of the module.
