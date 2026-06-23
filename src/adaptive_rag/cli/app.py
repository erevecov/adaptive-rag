import typer
from rich.console import Console

from adaptive_rag import __version__
from adaptive_rag.cli.chat import app as chat_app
from adaptive_rag.cli.evals import app as evals_app
from adaptive_rag.cli.first_run import app as first_run_app
from adaptive_rag.cli.graph import app as graph_app
from adaptive_rag.cli.jobs import app as jobs_app
from adaptive_rag.cli.projects import app as projects_app
from adaptive_rag.cli.providers import app as providers_app
from adaptive_rag.cli.retrieval import app as retrieval_app
from adaptive_rag.cli.sources import app as sources_app
from adaptive_rag.cli.sparse import app as sparse_app
from adaptive_rag.cli.v1 import app as v1_app
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings

app = typer.Typer(no_args_is_help=True)
app.add_typer(chat_app, name="chat")
app.add_typer(evals_app, name="evals")
app.add_typer(first_run_app, name="first-run")
app.add_typer(graph_app, name="graph")
app.add_typer(jobs_app, name="jobs")
app.add_typer(providers_app, name="providers")
app.add_typer(projects_app, name="projects")
app.add_typer(retrieval_app, name="retrieval")
app.add_typer(sources_app, name="sources")
app.add_typer(sparse_app, name="sparse")
app.add_typer(v1_app, name="v1")
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
