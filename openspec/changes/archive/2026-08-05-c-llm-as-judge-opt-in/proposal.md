# Propuesta Bloque C — LLM-as-judge opt-in

## Why

Hosted/offline chat evals measure citation coverage but not answer
faithfulness/relevancy. Design (`v1-design.md`) anticipates Ragas-style
judge metrics under an explicit budget.

## What Changes

- Opt-in `--llm-judge` on `adaptive-rag evals run`
- Requires `--max-cost-usd > 0` whenever judge is enabled
- Deterministic fake judge for offline/CI (no network)
- Optional live judge completer (operation `eval_judge`) when hosted
- Report metrics: mean faithfulness + response relevancy (informational;
  does not flip suite pass/fail by default)
- OpenSpec capability `llm-judge`

## Fuera de alcance

- Ragas dependency / full metric suite
- Langfuse or hosted observability
- Making judge default-on or required for quality-gate
- UI for judge results
