"""The transport of the clients: requests, authentication, retries and errors."""

from __future__ import annotations

import base64
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from urllib.parse import quote

import anyio
import httpx
import pydantic

from ._exceptions import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    MawaqitError,
    status_error,
)
from ._version import __version__

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "AsyncAPIClient",
    "SyncAPIClient",
]

T = TypeVar("T")
HttpClientT = TypeVar("HttpClientT", httpx.Client, httpx.AsyncClient)

DEFAULT_BASE_URL = "https://mawaqit.net/api"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_MAX_RETRIES = 2
_INITIAL_RETRY_DELAY = 0.5
_MAX_RETRY_DELAY = 8.0
_MAX_RETRY_AFTER = 60.0
_RETRY_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
_TOKEN_HEADER = "Api-Access-Token"  # noqa: S105  # A header name.
_USER_AGENT = f"mawaqit-python/{__version__}"

_LOGGER = logging.getLogger("mawaqit")


class BaseClient(ABC, Generic[HttpClientT]):
    """What the sync and async clients share: everything but the I/O."""

    _http: HttpClientT

    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: HttpClientT | None = None,
    ) -> None:
        """Create a client.

        Args:
            token: API token of a MAWAQIT account. Defaults to the
                `MAWAQIT_TOKEN` environment variable. Only searching mosques
                works without it.
            base_url: URL of the API. Defaults to the `MAWAQIT_BASE_URL`
                environment variable, then to `https://mawaqit.net/api`.
            timeout: Timeout of each request, in seconds.
            max_retries: How many times a request is retried after a network
                error, a timeout or a temporary error of the API.
            http_client: HTTPX client to send the requests with, to share a
                connection pool. It is left open when this client is closed.

        Raises:
            ValueError: `max_retries` is negative.
        """
        if max_retries < 0:
            msg = "max_retries cannot be negative."
            raise ValueError(msg)
        self._token = token or os.environ.get("MAWAQIT_TOKEN") or None
        self._base_url = (
            base_url or os.environ.get("MAWAQIT_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._owns_http = http_client is None
        self._http = http_client or self._new_http_client()

    @abstractmethod
    def _new_http_client(self) -> HttpClientT:
        """Return the HTTPX client to use when none is given."""

    @property
    def token(self) -> str | None:
        """The API token sent with the requests."""
        return self._token

    @property
    def base_url(self) -> str:
        """The URL of the API."""
        return self._base_url

    @property
    def timeout(self) -> float | httpx.Timeout:
        """The timeout of each request, in seconds."""
        return self._timeout

    @property
    def max_retries(self) -> int:
        """How many times a failed request is retried."""
        return self._max_retries

    def with_options(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout | None = None,
        max_retries: int | None = None,
    ) -> Self:
        """Return a copy of this client with other options.

        The copy shares the connection pool of this client, so it stops working
        once this client is closed. Options left out keep their current value.

        Args:
            token: API token of a MAWAQIT account.
            base_url: URL of the API.
            timeout: Timeout of each request, in seconds.
            max_retries: How many times a failed request is retried.

        Returns:
            The new client.
        """
        return type(self)(
            token=token or self._token,
            base_url=base_url or self._base_url,
            timeout=self._timeout if timeout is None else timeout,
            max_retries=self._max_retries if max_retries is None else max_retries,
            http_client=self._http,
        )

    def __repr__(self) -> str:
        """Show the URL of the API, never the token."""
        return f"{type(self).__name__}(base_url={self._base_url!r})"

    def _build_request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        basic_auth: tuple[str, str] | None = None,
        authenticated: bool = True,
    ) -> httpx.Request:
        """Build the request of an operation, with its authentication."""
        headers = {"Accept": "application/json", "User-Agent": _USER_AGENT}
        if authenticated:
            if not self._token:
                msg = "No API token: pass token= or set MAWAQIT_TOKEN."
                raise MawaqitError(msg)
            headers[_TOKEN_HEADER] = self._token
        if basic_auth:
            credentials = base64.b64encode(":".join(basic_auth).encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        # Path parameters are quoted so that a value cannot change the path.
        quoted = {k: quote(v, safe="") for k, v in (path_params or {}).items()}
        return self._http.build_request(
            method,
            self._base_url + path.format_map(quoted),
            params={k: v for k, v in (params or {}).items() if v is not None},
            headers=headers,
            timeout=self._timeout,
        )

    def _should_retry(self, retries_taken: int, response: httpx.Response) -> bool:
        return (
            retries_taken < self._max_retries
            and response.status_code in _RETRY_STATUSES
        )

    def _retry_delay(
        self,
        request: httpx.Request,
        retries_taken: int,
        response: httpx.Response | None,
    ) -> float:
        """Return how long to wait before retrying, honoring `Retry-After`."""
        delay = _retry_after(response) if response is not None else None
        if delay is None:
            delay = min(_INITIAL_RETRY_DELAY * 2**retries_taken, _MAX_RETRY_DELAY)
            delay *= 1 - 0.25 * random.random()  # noqa: S311  # Jitter, not security.
        reason = (
            "a network error" if response is None else f"HTTP {response.status_code}"
        )
        _LOGGER.info(
            "Retrying %s %s in %.1f s after %s",
            request.method,
            request.url.path,
            delay,
            reason,
        )
        return delay

    @staticmethod
    def _process_response(
        response: httpx.Response, response_type: pydantic.TypeAdapter[T]
    ) -> T:
        """Return the response parsed, or raise its error."""
        if not response.is_success:
            raise status_error(response)
        try:
            data = response.json()
        except ValueError as err:
            msg = "MAWAQIT did not answer with JSON."
            raise APIResponseValidationError(msg, response, body=response.text) from err
        try:
            return response_type.validate_python(data)
        except pydantic.ValidationError as err:
            msg = f"MAWAQIT answered with unexpected data: {err}"
            raise APIResponseValidationError(msg, response, body=data) from err


def _retry_after(response: httpx.Response) -> float | None:
    """Return the delay asked by a `Retry-After` header, if reasonable."""
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        delay = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        delay = date.timestamp() - time.time()
    return delay if 0 <= delay <= _MAX_RETRY_AFTER else None


def _connection_error(request: httpx.Request, error: httpx.TransportError) -> Exception:
    if isinstance(error, httpx.TimeoutException):
        return APITimeoutError(request)
    return APIConnectionError(request)


class AsyncAPIClient(BaseClient[httpx.AsyncClient]):
    """The transport of the async client."""

    def _new_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient()

    async def close(self) -> None:
        """Close the connections, unless the HTTPX client was given."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        """Return the client, closed on exit."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client."""
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        response_type: pydantic.TypeAdapter[T],
        path_params: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        basic_auth: tuple[str, str] | None = None,
        authenticated: bool = True,
    ) -> T:
        """Send a request, retrying temporary failures, and parse its response."""
        request = self._build_request(
            method,
            path,
            path_params=path_params,
            params=params,
            basic_auth=basic_auth,
            authenticated=authenticated,
        )
        retries_taken = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = await self._http.send(request)
            except httpx.TransportError as err:
                if retries_taken >= self._max_retries:
                    raise _connection_error(request, err) from err
            else:
                if not self._should_retry(retries_taken, response):
                    return self._process_response(response, response_type)
            await anyio.sleep(self._retry_delay(request, retries_taken, response))
            retries_taken += 1


class SyncAPIClient(BaseClient[httpx.Client]):
    """The transport of the sync client."""

    def _new_http_client(self) -> httpx.Client:
        return httpx.Client()

    def close(self) -> None:
        """Close the connections, unless the HTTPX client was given."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        """Return the client, closed on exit."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client."""
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        response_type: pydantic.TypeAdapter[T],
        path_params: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        basic_auth: tuple[str, str] | None = None,
        authenticated: bool = True,
    ) -> T:
        """Send a request, retrying temporary failures, and parse its response."""
        request = self._build_request(
            method,
            path,
            path_params=path_params,
            params=params,
            basic_auth=basic_auth,
            authenticated=authenticated,
        )
        retries_taken = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = self._http.send(request)
            except httpx.TransportError as err:
                if retries_taken >= self._max_retries:
                    raise _connection_error(request, err) from err
            else:
                if not self._should_retry(retries_taken, response):
                    return self._process_response(response, response_type)
            time.sleep(self._retry_delay(request, retries_taken, response))
            retries_taken += 1
