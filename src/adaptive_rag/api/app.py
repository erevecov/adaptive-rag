from fastapi import FastAPI

from adaptive_rag.api.routes.health import router as health_router
from adaptive_rag.api.routes.retrieval import router as retrieval_router
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Adaptive RAG", version="0.1.0")
    app.include_router(health_router)
    app.include_router(retrieval_router)
    return app


app = create_app()
