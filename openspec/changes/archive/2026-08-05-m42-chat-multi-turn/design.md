# Diseno M42

1. **session_id opcional:** si viene, reutilizar sesion auditada del mismo
   project (+ user cuando aplica); si no, crear nueva.
2. **Historial acotado:** ultimos `DEFAULT_CHAT_HISTORY_MESSAGES` (8) roles
   user/assistant al runner.
3. **Condenser:** `QueryCondenser.condense(history, message) -> query`.
   `DeterministicQueryCondenser` une el ultimo user turn relevante + mensaje
   actual (sin LLM). Retrieval usa la query condensada.
4. **UI:** `askChat`/`askChatStream` incluyen `session_id` cuando hay sesion
   seleccionada; no forzar `setSelectedSessionId(null)` al enviar follow-up.
