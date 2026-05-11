# Method Overview

This repository releases the recommendation-generation component of an HVAC energy-saving recommendation system.

## Core idea

The module separates **action decision** from **language generation**.

- The action itself is assumed to be fixed before LLM generation.
- The LLM does not decide the HVAC control action.
- Instead, the LLM integrates retrieved evidence and realizes the final recommendation text.

## Pipeline

1. **Action Construction**
   - Accepts a structured candidate action plan
   - Includes temperature setting, AC state, window action, reason type, and risk flags

2. **Evidence Retrieval**
   - Retrieves relevant information from:
     - rule knowledge base
     - historical optimization cases
     - user feedback memory

3. **Evidence Selection**
   - Prioritizes safety-related rules
   - Keeps representative history evidence
   - Builds a compact user preference profile

4. **Two-Stage LLM Generation**
   - Stage 1: planning LLM produces JSON clauses
   - Stage 2: realization module composes natural-language recommendation text

5. **Validation and Repair**
   - Checks whether the output is complete and consistent
   - Repairs lightweight problems automatically

## Why this design

Compared with pure rule-based text templates, this design allows:
- better integration of multiple evidence sources
- more natural and less repetitive recommendation text
- more flexible personalization
- preserved safety through rule-based constraints and validation
