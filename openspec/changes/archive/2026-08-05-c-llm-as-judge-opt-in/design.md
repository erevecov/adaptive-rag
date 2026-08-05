# Design: LLM-as-judge opt-in

- Default OFF. Enabling without `--max-cost-usd > 0` is a config error.
- Offline: `FakeDeterministicJudge` derives scores from citation coverage /
  non-empty answer (cost 0, still budget-gated at CLI).
- Live: `PromptLlmJudge` asks a text completer for JSON
  `{faithfulness, response_relevancy}` in [0,1], records `eval_judge` usage.
- Post-process chat cases that expose `answer` + context snippets.
- Suite status remains citation/retrieval-driven; judge metrics are additive.
