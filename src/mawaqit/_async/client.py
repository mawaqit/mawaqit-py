"""Async MAWAQIT client: transport, authentication, version namespaces.

This module is the source of truth for both the async and (unasync-generated)
sync clients, so it must stay free of async-only constructs that unasync cannot
rewrite mechanically.
"""

from __future__ import annotations

from asyncio import sleep
from types import TracebackType
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from .._transport import API_TOKEN_HEADER, raise_for_status
from ..config import MawaqitSettings
from ..constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    LOGIN_BACKOFF_CAP,
    LOGIN_PATH,
    MAX_LOGIN_RETRIES,
    RETRY_BACKOFF_CAP,
    RETRY_STATUSES,
)
from ..exceptions import MawaqitException, MissingCredentials
from .resources.v2 import AsyncV2
from .resources.v3 import AsyncV3

ModelT = TypeVar("ModelT", bound=BaseModel)


class AsyncMawaqitClient:
    """Async entrypoint to the MAWAQIT API.

    The client authenticates with a single API token, shared by every API
    version and reached through :attr:`v2` / :attr:`v3`. Pass ``token=`` (or set
    ``MAWAQIT_TOKEN``); if all you have is a username/password, exchange them for
    a token first with :func:`login`. The client never stores credentials — only
    the token it uses.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        api_base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        # Resolve configuration once (explicit arg > MAWAQIT_* env >
        # default). After this the client owns its resolved state; the settings
        # object is not kept around, so each value lives in exactly one place.
        config = MawaqitSettings.load(api_base_url=api_base_url, token=token)
        self._base_url = config.api_base_url
        self._token = config.token
        self._max_retries = max_retries

        # Absolute URLs are built from ``_base_url``, so an injected client is
        # used as-is (its own base_url, if any, is irrelevant). This is what lets
        # a consumer such as Home Assistant share one httpx client.
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._close_http = http_client is None

        self._v2: AsyncV2 | None = None
        self._v3: AsyncV3 | None = None

    @property
    def token(self) -> str | None:
        """The access token in plaintext, or ``None`` if none was configured."""
        return self._token.get_secret_value() if self._token is not None else None

    @property
    def v2(self) -> AsyncV2:
        """The v2 API namespace (lazily created, then cached)."""
        if self._v2 is None:
            self._v2 = AsyncV2(self)
        return self._v2

    @property
    def v3(self) -> AsyncV3:
        """The v3 API namespace (lazily created, then cached)."""
        if self._v3 is None:
            self._v3 = AsyncV3(self)
        return self._v3

    async def __aenter__(self) -> AsyncMawaqitClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client, but only if we created it."""
        if self._close_http:
            await self._http.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Send a request with retries, injecting auth and mapping errors."""
        headers: dict[str, str] = {}
        if authenticated:
            if self._token is None:
                raise MissingCredentials(
                    "No API token. Pass token=... (or set MAWAQIT_TOKEN); if you "
                    "only have a username/password, get a token with login()."
                )
            headers[API_TOKEN_HEADER] = self._token.get_secret_value()

        url = self._base_url + path
        for attempt in range(self._max_retries + 1):
            final = attempt == self._max_retries
            try:
                response = await self._http.request(
                    method, url, params=params, json=json, headers=headers
                )
            except httpx.TransportError as exc:
                if final:
                    raise MawaqitException(
                        f"Request to {path} failed after retries: {exc}"
                    ) from exc
            else:
                if not (response.status_code in RETRY_STATUSES and not final):
                    raise_for_status(response)
                    return response
            await sleep(min(RETRY_BACKOFF_CAP, 2**attempt))

        raise MawaqitException("unreachable")  # pragma: no cover

    # ----------------------------------------------------------------------- #
    # Typed request helpers — these make each resource method a one-liner.
    # ----------------------------------------------------------------------- #
    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        cast_to: type[ModelT],
    ) -> ModelT:
        """GET ``path`` and parse the JSON object into ``cast_to``."""
        response = await self._request("GET", path, params=params)
        return cast_to.model_validate(response.json())

    async def _get_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        cast_to: type[ModelT],
    ) -> list[ModelT]:
        """GET ``path`` and parse a JSON array into ``list[cast_to]``."""
        response = await self._request("GET", path, params=params)
        return [cast_to.model_validate(item) for item in response.json()]

    async def _get_json(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET ``path`` and return the raw JSON object (untyped endpoints)."""
        response = await self._request("GET", path, params=params)
        data: dict[str, Any] = response.json()
        return data

    async def _post(self, path: str, *, json: Any | None = None) -> None:
        """POST ``path`` (endpoints with no response body)."""
        await self._request("POST", path, json=json)

    async def _delete(self, path: str) -> None:
        """DELETE ``path`` (endpoints with no response body)."""
        await self._request("DELETE", path)


async def login(
    username: str | None = None,
    password: str | None = None,
    *,
    api_base_url: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Exchange a MAWAQIT username/password for an API token.

    A standalone primitive: the credentials live only for the duration of this
    call (nothing keeps them afterwards). Transient failures are retried with
    exponential backoff; bad credentials fail fast. Both arguments fall back to
    ``MAWAQIT_USERNAME`` / ``MAWAQIT_PASSWORD``, and the target to
    ``MAWAQIT_API_BASE_URL``. Pass ``http_client`` to reuse a shared session
    (it is left open); otherwise a temporary one is created and closed.
    """
    config = MawaqitSettings.load(
        api_base_url=api_base_url, username=username, password=password
    )
    if config.username is None or config.password is None:
        raise MissingCredentials("Please provide a MAWAQIT username and password.")

    http = http_client or httpx.AsyncClient(timeout=timeout)
    url = config.api_base_url + LOGIN_PATH
    auth = (config.username, config.password.get_secret_value())
    try:
        for attempt in range(MAX_LOGIN_RETRIES):
            final = attempt == MAX_LOGIN_RETRIES - 1
            try:
                response = await http.post(url, auth=auth)
            except httpx.TransportError as exc:
                if final:
                    raise MawaqitException(
                        f"Login failed after retries: {exc}"
                    ) from exc
            else:
                if not (response.status_code in RETRY_STATUSES and not final):
                    raise_for_status(response)
                    token = response.json().get("apiAccessToken")
                    if not isinstance(token, str):
                        raise MawaqitException(
                            "Login succeeded but the response had no API token."
                        )
                    return token
            await sleep(min(LOGIN_BACKOFF_CAP, 2**attempt))
    finally:
        if http_client is None:
            await http.aclose()

    raise MawaqitException("Could not obtain an API token.")  # pragma: no cover
