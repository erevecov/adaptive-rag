"""Utilidades compartidas de salida para comandos CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn

import typer


def echo_json(payload: object) -> None:
    """Imprime `payload` como JSON compacto en stdout."""

    typer.echo(json.dumps(payload))


def write_or_echo_json(payload: object, output: Path | None) -> None:
    """Escribe `payload` JSON en `output` o lo imprime en stdout si es None."""

    serialized = json.dumps(payload)
    if output is None:
        typer.echo(serialized)
    else:
        output.write_text(f"{serialized}\n", encoding="utf-8")


def exit_error(message: str, *, cause: BaseException | None = None) -> NoReturn:
    """Imprime `message` en stderr y termina el comando con codigo 1."""

    typer.echo(message, err=True)
    raise typer.Exit(1) from cause
