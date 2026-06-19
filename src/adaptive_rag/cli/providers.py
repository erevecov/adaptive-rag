"""Comandos CLI de providers live/fake."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from adaptive_rag.cli.dependencies import get_cli_dense_embedding_provider
from adaptive_rag.embeddings import QwenEmbeddingProviderError
from adaptive_rag.provider_runtime import ProviderConfigurationError

app = typer.Typer(no_args_is_help=True)


@app.command("embedding-smoke")
def embedding_smoke(
    text: Annotated[str, typer.Option("--text")] = "Adaptive RAG smoke",
) -> None:
    provider = get_cli_dense_embedding_provider()
    try:
        embeddings = provider.embed_texts([text])
    except (ProviderConfigurationError, QwenEmbeddingProviderError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(
            {
                "provider": provider.provider_name,
                "model": provider.model_name,
                "dimensions": provider.dimensions,
                "input_count": 1,
                "embedding_count": len(embeddings),
            }
        )
    )
