import typer
from rich.console import Console

from adaptive_rag import __version__
from adaptive_rag.cli.chat import app as chat_app
from adaptive_rag.cli.retrieval import app as retrieval_app
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings

app = typer.Typer(no_args_is_help=True)
app.add_typer(chat_app, name="chat")
app.add_typer(retrieval_app, name="retrieval")
console = Console()


@app.callback()
def callback() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def version() -> None:
    console.print(f"adaptive-rag {__version__}")


@app.command()
def health() -> None:
    console.print("ok")


def main() -> None:
    app()
