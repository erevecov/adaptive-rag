"""Tests para URL fetch policy.

Usan resolver y stream factory fakes para validar policy sin red real.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType

import pytest

from adaptive_rag.ingestion import (
    DisallowedContentTypeError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsafeURLError,
    URLFetcher,
    URLFetchPolicy,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}
        self.url = "https://example.com"
        self.chunks = chunks or [b"hello"]
        self.body_was_read = False

    def iter_bytes(self) -> Iterator[bytes]:
        self.body_was_read = True
        yield from self.chunks

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeStream:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def __enter__(self) -> FakeResponse:
        return self.response

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeStreamFactory:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def __call__(self, url: str) -> FakeStream:
        self.requested_urls.append(url)
        return FakeStream(self.responses[url])


class FakeResolver:
    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self.mapping = mapping
        self.calls: list[tuple[str, int]] = []

    def __call__(self, hostname: str, port: int) -> list[str]:
        self.calls.append((hostname, port))
        return self.mapping[hostname]


def _fetcher(
    *,
    responses: dict[str, FakeResponse] | None = None,
    dns: dict[str, list[str]] | None = None,
    policy: URLFetchPolicy | None = None,
) -> tuple[URLFetcher, FakeStreamFactory, FakeResolver]:
    stream_factory = FakeStreamFactory(responses or {})
    resolver = FakeResolver(dns or {"example.com": ["93.184.216.34"]})
    return (
        URLFetcher(
            policy=policy or URLFetchPolicy(max_response_bytes=16),
            resolver=resolver,
            stream_factory=stream_factory,
        ),
        stream_factory,
        resolver,
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://user@example.com",
        "https://user:pass@example.com",
        "https:///missing-host",
    ],
)
def test_validate_url_rejects_unsafe_shapes(url: str) -> None:
    fetcher, _, _ = _fetcher()

    with pytest.raises(UnsafeURLError):
        fetcher.validate_url(url)


@pytest.mark.parametrize(
    "url,dns",
    [
        ("http://localhost", {"localhost": ["127.0.0.1"]}),
        ("http://metadata.local", {"metadata.local": ["169.254.169.254"]}),
        ("http://private.local", {"private.local": ["10.0.0.5"]}),
    ],
)
def test_validate_url_blocks_non_global_addresses(
    url: str, dns: dict[str, list[str]]
) -> None:
    fetcher, _, _ = _fetcher(dns=dns)

    with pytest.raises(UnsafeURLError):
        fetcher.validate_url(url)


def test_fetch_follows_safe_redirect_after_validating_target() -> None:
    fetcher, stream_factory, resolver = _fetcher(
        dns={
            "example.com": ["93.184.216.34"],
            "docs.example.com": ["93.184.216.35"],
        },
        responses={
            "https://example.com/start": FakeResponse(
                status_code=302,
                headers={"location": "https://docs.example.com/final"},
            ),
            "https://docs.example.com/final": FakeResponse(
                headers={"content-type": "text/html; charset=utf-8"},
                chunks=[b"<h1>ok</h1>"],
            ),
        },
    )

    result = fetcher.fetch("https://example.com/start")

    assert result.final_url == "https://docs.example.com/final"
    assert result.content == b"<h1>ok</h1>"
    assert stream_factory.requested_urls == [
        "https://example.com/start",
        "https://docs.example.com/final",
    ]
    assert resolver.calls == [("example.com", 443), ("docs.example.com", 443)]


def test_fetch_blocks_redirect_to_private_address_before_requesting_target() -> None:
    fetcher, stream_factory, _ = _fetcher(
        dns={
            "example.com": ["93.184.216.34"],
            "internal.local": ["127.0.0.1"],
        },
        responses={
            "https://example.com/start": FakeResponse(
                status_code=302,
                headers={"location": "http://internal.local/admin"},
            ),
        },
    )

    with pytest.raises(UnsafeURLError):
        fetcher.fetch("https://example.com/start")

    assert stream_factory.requested_urls == ["https://example.com/start"]


def test_fetch_rejects_too_many_redirects() -> None:
    fetcher, _, _ = _fetcher(
        dns={"example.com": ["93.184.216.34"]},
        policy=URLFetchPolicy(max_redirects=1),
        responses={
            "https://example.com/1": FakeResponse(
                status_code=302, headers={"location": "/2"}
            ),
            "https://example.com/2": FakeResponse(
                status_code=302, headers={"location": "/3"}
            ),
        },
    )

    with pytest.raises(TooManyRedirectsError):
        fetcher.fetch("https://example.com/1")


def test_fetch_rejects_disallowed_content_type_before_reading_body() -> None:
    response = FakeResponse(
        headers={"content-type": "application/octet-stream"},
        chunks=[b"binary"],
    )
    fetcher, _, _ = _fetcher(
        responses={"https://example.com/file": response},
    )

    with pytest.raises(DisallowedContentTypeError):
        fetcher.fetch("https://example.com/file")

    assert response.body_was_read is False


def test_fetch_rejects_declared_content_length_before_reading_body() -> None:
    response = FakeResponse(
        headers={"content-type": "text/plain", "content-length": "17"},
        chunks=[b"0123456789abcdefg"],
    )
    fetcher, _, _ = _fetcher(
        responses={"https://example.com/large": response},
        policy=URLFetchPolicy(max_response_bytes=16),
    )

    with pytest.raises(ResponseTooLargeError):
        fetcher.fetch("https://example.com/large")

    assert response.body_was_read is False


def test_fetch_stops_stream_that_exceeds_max_response_bytes() -> None:
    fetcher, _, _ = _fetcher(
        responses={
            "https://example.com/stream": FakeResponse(
                headers={"content-type": "text/plain"},
                chunks=[b"0123456789", b"abcdefg"],
            )
        },
        policy=URLFetchPolicy(max_response_bytes=16),
    )

    with pytest.raises(ResponseTooLargeError):
        fetcher.fetch("https://example.com/stream")


def test_fetch_returns_allowed_response_at_size_limit() -> None:
    fetcher, _, _ = _fetcher(
        responses={
            "https://example.com/ok": FakeResponse(
                headers={"content-type": "application/pdf"},
                chunks=[b"0123456789abcdef"],
            )
        },
        policy=URLFetchPolicy(max_response_bytes=16),
    )

    result = fetcher.fetch("https://example.com/ok")

    assert result.content == b"0123456789abcdef"
    assert result.content_type == "application/pdf"
    assert result.status_code == 200


def test_validate_url_returns_global_addresses() -> None:
    fetcher, _, _ = _fetcher(dns={"example.com": ["93.184.216.34", "93.184.216.35"]})

    addresses = fetcher.validate_url("https://example.com/doc")

    assert addresses == ["93.184.216.34", "93.184.216.35"]


def test_build_pinned_request_uses_validated_ip_and_original_host() -> None:
    from adaptive_rag.ingestion.url_fetch_policy import build_pinned_request

    pinned = build_pinned_request(
        "https://example.com/doc?q=1",
        pinned_ip="93.184.216.34",
        request_headers={"User-Agent": "adaptive-rag/0.1.0"},
    )

    assert pinned.url == "https://93.184.216.34/doc?q=1"
    assert pinned.headers["Host"] == "example.com"
    assert pinned.headers["User-Agent"] == "adaptive-rag/0.1.0"
    assert pinned.extensions == {"sni_hostname": "example.com"}


def test_build_pinned_request_http_omits_sni_and_keeps_nondefault_port() -> None:
    from adaptive_rag.ingestion.url_fetch_policy import build_pinned_request

    pinned = build_pinned_request(
        "http://docs.example.com:8080/a",
        pinned_ip="8.8.8.8",
        request_headers={},
    )

    assert pinned.url == "http://8.8.8.8:8080/a"
    assert pinned.headers["Host"] == "docs.example.com:8080"
    assert pinned.extensions == {}


def test_build_pinned_request_formats_ipv6_literal() -> None:
    from adaptive_rag.ingestion.url_fetch_policy import build_pinned_request

    pinned = build_pinned_request(
        "https://example.com/x",
        pinned_ip="2001:db8::1",
        request_headers={},
    )

    assert pinned.url == "https://[2001:db8::1]/x"
    assert pinned.headers["Host"] == "example.com"
    assert pinned.extensions == {"sni_hostname": "example.com"}


def test_httpx_stream_connects_to_pinned_ip_not_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default transport must not let httpx re-resolve the hostname."""
    from adaptive_rag.ingestion import url_fetch_policy as policy_mod

    captured: dict[str, object] = {}

    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "text/plain"}
        url = "https://93.184.216.34/doc"

        def iter_bytes(self):
            yield b"pinned-ok"

        def raise_for_status(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _StreamCM:
        def __enter__(self) -> _FakeResponse:
            return _FakeResponse()

        def __exit__(self, *args: object) -> None:
            return None

    class _FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str, **kwargs: object) -> _StreamCM:
            captured["method"] = method
            captured["url"] = url
            captured["stream_kwargs"] = kwargs
            return _StreamCM()

    monkeypatch.setattr(policy_mod.httpx, "Client", _FakeClient)

    fetcher = URLFetcher(
        policy=URLFetchPolicy(max_response_bytes=64),
        resolver=lambda hostname, port: ["93.184.216.34"],
    )
    result = fetcher.fetch("https://example.com/doc")

    assert result.content == b"pinned-ok"
    assert captured["method"] == "GET"
    assert captured["url"] == "https://93.184.216.34/doc"
    stream_kwargs = captured["stream_kwargs"]
    assert isinstance(stream_kwargs, dict)
    assert stream_kwargs["headers"]["Host"] == "example.com"
    assert stream_kwargs["extensions"] == {"sni_hostname": "example.com"}
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs.get("trust_env") is False
    assert client_kwargs.get("follow_redirects") is False


def test_fetch_revalidates_each_redirect_hop_before_pinning() -> None:
    """Each hop resolves+validates independently (DNS rebinding on redirect)."""
    resolve_sequence = {
        "evil.example": [
            ["93.184.216.34"],  # first lookup: public (passes)
        ],
        "safe.example": [["8.8.4.4"]],
    }
    call_counts: dict[str, int] = {}

    def resolver(hostname: str, port: int) -> list[str]:
        call_counts[hostname] = call_counts.get(hostname, 0) + 1
        seq = resolve_sequence[hostname]
        # Always return last known mapping after consuming sequence
        idx = min(call_counts[hostname] - 1, len(seq) - 1)
        return seq[idx]

    stream_factory = FakeStreamFactory(
        {
            "https://evil.example/start": FakeResponse(
                status_code=302,
                headers={"location": "https://safe.example/final"},
            ),
            "https://safe.example/final": FakeResponse(
                headers={"content-type": "text/plain"},
                chunks=[b"done"],
            ),
        }
    )
    fetcher = URLFetcher(
        policy=URLFetchPolicy(max_response_bytes=16),
        resolver=resolver,
        stream_factory=stream_factory,
    )

    result = fetcher.fetch("https://evil.example/start")

    assert result.content == b"done"
    assert call_counts == {"evil.example": 1, "safe.example": 1}
    assert stream_factory.requested_urls == [
        "https://evil.example/start",
        "https://safe.example/final",
    ]
