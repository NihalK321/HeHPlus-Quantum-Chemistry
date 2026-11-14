"""Small, dependency-free HTTP client for documented scientific source APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
import time
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "PepperQ/0.1 (research peptide library; contact project maintainers)"


class SourceRequestError(RuntimeError):
    """A source request failed after the bounded retry policy was exhausted."""

    def __init__(self, source: str, url: str, message: str, *, status_code: int | None = None) -> None:
        self.source = source
        self.url = url
        self.status_code = status_code
        super().__init__(f"{source} request failed for {url}: {message}")


@dataclass(frozen=True)
class JsonResponse:
    """A JSON payload and the response metadata needed for provenance/pagination."""

    url: str
    status_code: int
    headers: Mapping[str, str]
    payload: Any
    retrieved_at: str

    def header(self, name: str) -> str | None:
        lowered = name.casefold()
        for key, value in self.headers.items():
            if key.casefold() == lowered:
                return value
        return None


class JsonHttpClient:
    """GET-only JSON client with conservative retry behavior for public APIs.

    The client intentionally has no generic proxy endpoint or URL input from the
    PepperQ API. Connectors own their documented source base URLs.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 30,
        max_retries: int = 3,
        backoff_seconds: float = 0.75,
        user_agent: str = DEFAULT_USER_AGENT,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")

        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.user_agent = user_agent
        self._opener = opener
        self._sleeper = sleeper

    def get_json(self, url: str, *, source: str, headers: Mapping[str, str] | None = None) -> JsonResponse:
        request_headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if headers:
            request_headers.update(headers)

        last_error: SourceRequestError | None = None
        for attempt in range(self.max_retries + 1):
            request = Request(url, headers=request_headers, method="GET")
            try:
                response = self._opener(request, timeout=self.timeout_seconds)
                try:
                    raw_status = getattr(response, "status", None)
                    if raw_status is None:
                        raw_status = response.getcode()
                    status_code = int(raw_status)
                    raw_body = response.read()
                    response_headers = _headers_to_dict(getattr(response, "headers", {}))
                finally:
                    close = getattr(response, "close", None)
                    if callable(close):
                        close()

                if status_code >= 400:
                    raise SourceRequestError(source, url, f"HTTP {status_code}", status_code=status_code)

                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise SourceRequestError(source, url, "response was not valid UTF-8 JSON") from error

                return JsonResponse(
                    url=url,
                    status_code=status_code,
                    headers=response_headers,
                    payload=payload,
                    retrieved_at=datetime.now(UTC).isoformat(),
                )
            except HTTPError as error:
                error_headers = _headers_to_dict(error.headers or {})
                body_detail = _http_error_detail(error)
                last_error = SourceRequestError(
                    source,
                    url,
                    body_detail or f"HTTP {error.code}",
                    status_code=error.code,
                )
                retry_after = _retry_after_seconds(error_headers.get("Retry-After"))
                retryable = error.code == 429 or 500 <= error.code < 600
            except (URLError, TimeoutError, OSError) as error:
                last_error = SourceRequestError(source, url, str(error.reason if isinstance(error, URLError) else error))
                retry_after = None
                retryable = True
            except SourceRequestError as error:
                last_error = error
                retry_after = None
                retryable = error.status_code == 429 or (error.status_code is not None and error.status_code >= 500)

            if not retryable or attempt >= self.max_retries:
                assert last_error is not None
                raise last_error

            self._sleeper(self._delay_for(attempt, retry_after))

        assert last_error is not None
        raise last_error

    def _delay_for(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(max(retry_after, 0), 60)
        return min(self.backoff_seconds * (2**attempt), 30)


def _headers_to_dict(headers: Any) -> dict[str, str]:
    if hasattr(headers, "items"):
        return {str(key): str(value) for key, value in headers.items()}
    return {}


def _http_error_detail(error: HTTPError) -> str | None:
    try:
        body = error.read(512).decode("utf-8", errors="replace").strip()
    except OSError:
        return None
    return body or None


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return (retry_at - datetime.now(UTC)).total_seconds()
