import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from adaptive_rag.api.routes.auth import router as auth_router
from adaptive_rag.api.routes.authoring import router as authoring_router
from adaptive_rag.api.routes.chat import router as chat_router
from adaptive_rag.api.routes.chat_attachments import router as chat_attachments_router
from adaptive_rag.api.routes.health import router as health_router
from adaptive_rag.api.routes.ingestion_ops import router as ingestion_ops_router
from adaptive_rag.api.routes.jobs import admin_router as jobs_admin_router
from adaptive_rag.api.routes.jobs import router as jobs_router
from adaptive_rag.api.routes.knowledge import router as knowledge_router
from adaptive_rag.api.routes.provider_connections import (
    router as provider_connections_router,
)
from adaptive_rag.api.routes.retrieval import router as retrieval_router
from adaptive_rag.api.routes.runtime_settings import router as runtime_settings_router
from adaptive_rag.api.routes.runtime_settings import (
    workspace_router as workspace_runtime_settings_router,
)
from adaptive_rag.api.routes.user_memory import router as user_memory_router
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.schema_readiness import assert_database_schema_current
from adaptive_rag.db.session import create_engine_from_url
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.security.headers import SecurityHeadersMiddleware

# Explicit CORS surface (no method/header wildcards).
CORS_ALLOW_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOW_HEADERS = (
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Request-Id",
    "X-Access-Token",
    "X-CSRF-Token",
    "X-Setup-Secret",
)

# Misconfigured / incomplete provider runtime: request may be valid, service cannot
# fulfill until runtime settings/secrets are fixed. Prefer 503 over opaque 500.
_PROVIDER_CONFIGURATION_STATUS = 503


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database_urls = {
        settings.database_url,
        settings.job_database_url or settings.database_url,
    }
    engines = [create_engine_from_url(url) for url in database_urls]
    try:
        for engine in engines:
            await asyncio.to_thread(assert_database_schema_current, engine)
        yield
    finally:
        for engine in engines:
            engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Adaptive RAG", version="0.1.0", lifespan=_lifespan)
    # Outer middleware runs last on response; headers middleware is outermost
    # so security headers apply to CORS responses too.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=list(CORS_ALLOW_METHODS),
        allow_headers=list(CORS_ALLOW_HEADERS),
    )

    @app.exception_handler(ProviderConfigurationError)
    async def provider_configuration_error_handler(
        _request: Request,
        exc: ProviderConfigurationError,
    ) -> JSONResponse:
        # Stable client-facing message only (no traceback / secret material).
        # Existing ProviderConfigurationError strings are operational codes, not keys.
        return JSONResponse(
            status_code=_PROVIDER_CONFIGURATION_STATUS,
            content={"detail": str(exc)},
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(authoring_router)
    app.include_router(ingestion_ops_router)
    app.include_router(jobs_router)
    app.include_router(jobs_admin_router)
    app.include_router(retrieval_router)
    app.include_router(chat_router)
    app.include_router(chat_attachments_router)
    app.include_router(knowledge_router)
    app.include_router(user_memory_router)
    app.include_router(provider_connections_router)
    app.include_router(runtime_settings_router)
    app.include_router(workspace_runtime_settings_router)
    return app


app = create_app()
