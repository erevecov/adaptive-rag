import typer
from rich.console import Console

from adaptive_rag import __version__
from adaptive_rag.cli.chat import app as chat_app
from adaptive_rag.cli.evals import app as evals_app
from adaptive_rag.cli.graph import app as graph_app
from adaptive_rag.cli.jobs import app as jobs_app
from adaptive_rag.cli.projects import app as projects_app
from adaptive_rag.cli.providers import app as providers_app
from adaptive_rag.cli.retrieval import app as retrieval_app
from adaptive_rag.cli.sources import app as sources_app
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings

app = typer.Typer(no_args_is_help=True)
app.add_typer(chat_app, name="chat")
app.add_typer(evals_app, name="evals")
app.add_typer(graph_app, name="graph")
app.add_typer(jobs_app, name="jobs")
app.add_typer(providers_app, name="providers")
app.add_typer(projects_app, name="projects")
app.add_typer(retrieval_app, name="retrieval")
app.add_typer(sources_app, name="sources")
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
