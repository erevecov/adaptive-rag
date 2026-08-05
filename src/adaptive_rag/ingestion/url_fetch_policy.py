"""Policy y fetch seguro de URLs para ingestion."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from types import TracebackType
from typing import Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx


class URLFetchPolicyError(ValueError):
    """Error base para violaciones de URL fetch policy."""


class UnsafeURLError(URLFetchPolicyError):
    """La URL o su resolucion DNS no cumple la policy."""


class DisallowedContentTypeError(URLFetchPolicyError):
    """La respuesta declara un content type fuera de allowlist."""


class ResponseTooLargeError(URLFetchPolicyError):
    """La respuesta excede el limite configurado."""


class TooManyRedirectsError(URLFetchPolicyError):
    """La cadena de redirects excede el limite configurado."""


class FetchResponse(Protocol):
    @property
    def status_code(self) -> int:
        """Codigo HTTP de la respuesta."""

    @property
    def headers(self) -> Mapping[str, str]:
        """Headers de respuesta normalizados como mapping."""

    @property
    def url(self) -> object:
        """URL final reportada por el cliente HTTP."""

    def iter_bytes(self) -> Iterator[bytes]:
        """Itera el cuerpo como bytes."""

    def raise_for_status(self) -> None:
        """Lanza si el status HTTP no es exitoso."""


ResponseContext = AbstractContextManager[FetchResponse]
Resolver = Callable[[str, int], list[str]]
StreamFactory = Callable[[str], ResponseContext]


@dataclass(frozen=True, slots=True)
class URLFetchPolicy:
    """Configuracion de seguridad para fetch remoto."""

    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_content_types: frozenset[str] = frozenset(
        {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/xhtml+xml",
            "text/html",
            "text/plain",
        }
    )
    max_response_bytes: int = 5 * 1024 * 1024
    max_redirects: int = 5
    timeout_seconds: float = 10.0
    request_headers: Mapping[str, str] = field(
        default_factory=lambda: {"User-Agent": "adaptive-rag/0.1.0"}
    )


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Resultado de un fetch seguro."""

    final_url: str
    status_code: int
    content_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class PinnedRequest:
    """URL/headers/extensions para conectar al IP validado sin re-resolver DNS."""

    url: str
    headers: dict[str, str]
    extensions: dict[str, str]


class _HTTPXFetchResponse:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    @property
    def url(self) -> object:
        return self._response.url

    def iter_bytes(self) -> Iterator[bytes]:
        return self._response.iter_bytes()

    def raise_for_status(self) -> None:
        self._response.raise_for_status()


class _HTTPXStreamContext(AbstractContextManager[FetchResponse]):
    def __init__(
        self, response_context: AbstractContextManager[httpx.Response]
    ) -> None:
        self._response_context = response_context

    def __enter__(self) -> FetchResponse:
        return _HTTPXFetchResponse(self._response_context.__enter__())

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self._response_context.__exit__(exc_type, exc_value, traceback)


class URLFetcher:
    """Valida y descarga URLs cumpliendo `URLFetchPolicy`."""

    def __init__(
        self,
        *,
        policy: URLFetchPolicy | None = None,
        resolver: Resolver | None = None,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        self.policy = policy or URLFetchPolicy()
        self._resolver = resolver or resolve_hostname
        # Custom factories (tests) keep the simple URL-only contract; the
        # default path pins the connect target to the validated IP.
        self._stream_factory = stream_factory

    def validate_url(self, url: str) -> list[str]:
        """Valida la URL y devuelve las IPs globales resueltas (orden estable)."""

        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in self.policy.allowed_schemes:
            raise UnsafeURLError(f"URL scheme is not allowed: {parts.scheme}")
        if not parts.hostname:
            raise UnsafeURLError("URL must include a hostname")
        if parts.username is not None or parts.password is not None:
            raise UnsafeURLError("URL must not include embedded credentials")

        port = parts.port or _default_port(scheme)
        addresses = self._resolver(parts.hostname, port)
        if not addresses:
            raise UnsafeURLError("Hostname did not resolve to any address")

        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise UnsafeURLError(
                    f"Hostname resolves to non-global address: {address}"
                )
        return addresses

    def fetch(self, url: str) -> FetchResult:
        current_url = url
        redirects_seen = 0

        while True:
            addresses = self.validate_url(current_url)
            with self._open_stream(current_url, pinned_ip=addresses[0]) as response:
                if _is_redirect(response.status_code):
                    if redirects_seen >= self.policy.max_redirects:
                        raise TooManyRedirectsError("Maximum redirects exceeded")
                    current_url = self._next_redirect_url(current_url, response.headers)
                    redirects_seen += 1
                    continue

                response.raise_for_status()
                content_type = self._validate_content_type(response.headers)
                self._validate_declared_length(response.headers)
                content = self._read_limited(response)
                return FetchResult(
                    final_url=current_url,
                    status_code=response.status_code,
                    content_type=content_type,
                    content=content,
                )

    def _open_stream(self, url: str, *, pinned_ip: str) -> ResponseContext:
        if self._stream_factory is not None:
            return self._stream_factory(url)
        return self._httpx_stream(url, pinned_ip=pinned_ip)

    def _httpx_stream(self, url: str, *, pinned_ip: str) -> ResponseContext:
        pinned = build_pinned_request(
            url,
            pinned_ip=pinned_ip,
            request_headers=self.policy.request_headers,
        )
        return _HTTPXStreamContext(
            _httpx_pinned_stream(
                pinned_url=pinned.url,
                headers=pinned.headers,
                timeout=self.policy.timeout_seconds,
                extensions=pinned.extensions,
            )
        )

    def _next_redirect_url(self, current_url: str, headers: Mapping[str, str]) -> str:
        location = _header_value(headers, "location")
        if location is None or not location.strip():
            raise UnsafeURLError("Redirect response must include Location header")
        return urljoin(current_url, location)

    def _validate_content_type(self, headers: Mapping[str, str]) -> str:
        raw_content_type = _header_value(headers, "content-type")
        if raw_content_type is None:
            raise DisallowedContentTypeError("Response is missing Content-Type")
        content_type = raw_content_type.split(";", 1)[0].strip().lower()
        if content_type not in self.policy.allowed_content_types:
            raise DisallowedContentTypeError(
                f"Content-Type is not allowed: {content_type}"
            )
        return content_type

    def _validate_declared_length(self, headers: Mapping[str, str]) -> None:
        raw_length = _header_value(headers, "content-length")
        if raw_length is None:
            return
        try:
            declared_length = int(raw_length)
        except ValueError as exc:
            raise ResponseTooLargeError("Content-Length must be an integer") from exc
        if declared_length > self.policy.max_response_bytes:
            raise ResponseTooLargeError("Content-Length exceeds configured limit")

    def _read_limited(self, response: FetchResponse) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            if not chunk:
                continue
            total += len(chunk)
            if total > self.policy.max_response_bytes:
                raise ResponseTooLargeError("Response body exceeds configured limit")
            chunks.append(chunk)
        return b"".join(chunks)


def build_pinned_request(
    url: str,
    *,
    pinned_ip: str,
    request_headers: Mapping[str, str],
) -> PinnedRequest:
    """Construye URL por IP + Host/SNI del hostname original (anti DNS-rebinding)."""

    parts = urlsplit(url)
    hostname = parts.hostname
    if not hostname:
        raise UnsafeURLError("URL must include a hostname")

    scheme = parts.scheme.lower()
    port = parts.port
    ip_literal = _format_ip_for_url(pinned_ip)
    netloc = ip_literal if port is None else f"{ip_literal}:{port}"
    pinned_url = urlunsplit(
        (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
    )

    headers = dict(request_headers)
    headers["Host"] = _host_header(hostname, port)

    extensions: dict[str, str] = {}
    if scheme == "https":
        # httpcore usa sni_hostname para SNI y verificacion del certificado.
        extensions["sni_hostname"] = hostname

    return PinnedRequest(url=pinned_url, headers=headers, extensions=extensions)


@contextmanager
def _httpx_pinned_stream(
    *,
    pinned_url: str,
    headers: Mapping[str, str],
    timeout: float,
    extensions: Mapping[str, str],
) -> Iterator[httpx.Response]:
    # trust_env=False evita que un proxy de entorno re-resuelva el hostname.
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        proxy=None,
    ) as client:
        with client.stream(
            "GET",
            pinned_url,
            headers=dict(headers),
            extensions=dict(extensions),
        ) as response:
            yield response


def resolve_hostname(hostname: str, port: int) -> list[str]:
    """Resuelve `hostname` a IPs usando `socket.getaddrinfo`."""

    infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    return sorted({str(info[4][0]) for info in infos})


def _format_ip_for_url(address: str) -> str:
    ip = ipaddress.ip_address(address)
    if ip.version == 6:
        return f"[{address}]"
    return address


def _host_header(hostname: str, port: int | None) -> str:
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        host = hostname
    else:
        host = f"[{hostname}]" if ip.version == 6 else hostname
    if port is not None:
        return f"{host}:{port}"
    return host


def _default_port(scheme: str) -> int:
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    raise UnsafeURLError(f"URL scheme is not allowed: {scheme}")


def _is_redirect(status_code: int) -> bool:
    return status_code in {301, 302, 303, 307, 308}


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return None
