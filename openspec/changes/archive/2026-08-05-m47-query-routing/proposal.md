# Propuesta M47 — Query routing medible

## Why
Chat always used dense_sparse. Need measurable adaptive routing without hosted LLM.

## What Changes
- Rule-based QueryRouter (skip_retrieval / dense_sparse / graph)
- Wire ChatRetrievalTool; eval_routing CI-safe; decision record

## Fuera de alcance
LLM classifier default, HyDE, multi-query, SPLADE.
