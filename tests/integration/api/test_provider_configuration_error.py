"""ProviderConfigurationError must map to a controlled HTTP response (not 500)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from adaptive_rag.api.app import create_app
from adaptive_rag.provider_runtime import ProviderConfigurationError


def test_provider_configuration_error_handler_is_registered() -> None:
    app = create_app()
    assert ProviderConfigurationError in app.exception_handlers


def test_provider_configuration_error_returns_503_with_detail() -> None:
    app = create_app()
    message = "missing_provider_secret: conn-test api_key is required"

    @app.get("/__test__/provider-configuration-error")
    def _raise_provider_configuration_error() -> None:
        raise ProviderConfigurationError(message)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/__test__/provider-configuration-error")

    assert response.status_code == 503
    body = response.json()
    assert body == {"detail": message}
    # No stack trace / debug body leakage
    text = response.text.lower()
    assert "traceback" not in text
    assert "providerconfigurationerror" not in text
