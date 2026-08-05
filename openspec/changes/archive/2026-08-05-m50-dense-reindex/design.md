# Diseno M50

1. Dense reindex walks project document_versions ordered by created_at/version.
2. Force re-embed ignores existing embedding metadata match.
3. Report: project_id, version counts, embedded/reused, started/finished, watermark.
4. LLM contextualizer opt-in is a first-class Contextualizer implementation
   (`llm_opt_in`) with distinct summaries for A/B; live chat LLM can replace later.
5. ab-compare runs both contextualizers on same chunks (force) and reports
   differing_summary_count without requiring live providers.
