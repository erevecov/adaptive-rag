# Prompts versionados

Este directorio contiene prompts versionados usados por Adaptive RAG.

Reglas:

- El identificador de versión es el nombre del archivo sin extensión.
- Los prompts se escriben en Markdown.
- Un prompt usado para datos persistidos no se edita en caliente.
- Un cambio semántico crea un archivo nuevo, por ejemplo
  `answer_with_citations_v2.md`.
- Cada flujo que use un prompt debe persistir la versión usada para poder
  reproducir resultados y comparar evals.

Prompts previstos para v1:

- `contextual_chunk_v1.md`
- `answer_with_citations_v1.md`
- `tool_selection_v1.md`
- `eval_judge_v1.md`

Los archivos concretos se crearán cuando se implemente el flujo que los usa.
