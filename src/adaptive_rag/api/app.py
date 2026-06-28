from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adaptive_rag.api.routes.authoring import router as authoring_router
from adaptive_rag.api.routes.chat import router as chat_router
from adaptive_rag.api.routes.health import router as health_router
from adaptive_rag.api.routes.ingestion_ops import router as ingestion_ops_router
from adaptive_rag.api.routes.provider_connections import (
    router as provider_connections_router,
)
from adaptive_rag.api.routes.retrieval import router as retrieval_router
from adaptive_rag.api.routes.runtime_settings import (
    project_router as project_runtime_settings_router,
)
from adaptive_rag.api.routes.runtime_settings import router as runtime_settings_router
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Adaptive RAG", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(authoring_router)
    app.include_router(ingestion_ops_router)
    app.include_router(retrieval_router)
    app.include_router(chat_router)
    app.include_router(provider_connections_router)
    app.include_router(runtime_settings_router)
    app.include_router(project_runtime_settings_router)
    return app


app = create_app()
