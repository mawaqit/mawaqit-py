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
from ..config import ENVIRONMENT_BASE_URLS, Environment, MawaqitSettings
from ..exceptions import BadCredentialsException, MawaqitException, MissingCredentials
from .v2 import AsyncV2
from .v3 import AsyncV3

#: Basic-auth login endpoint (relative to the base URL). Login always uses v2.
LOGIN_PATH = "2.0/me"

#: How many times ``get_api_token`` retries a *transient* login failure before
#: giving up, with exponential backoff capped at 16s.
MAX_LOGIN_RETRIES = 20

#: Response statuses worth retrying (transient server/rate-limit errors).
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

ModelT = TypeVar("ModelT", bound=BaseModel)


class AsyncMawaqitClient:
    """Async entrypoint to the MAWAQIT API.

    Authentication is centralised here: a single token (supplied directly or
    obtained via basic-auth login) is shared by every API version. Reach the
    versioned resources through :attr:`v2` and :attr:`v3`.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
        environment: Environment | None = None,
        settings: MawaqitSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self._settings = settings or MawaqitSettings()
        self._max_retries = max_retries

        if base_url is None:
            if environment is not None:
                base_url = ENVIRONMENT_BASE_URLS[environment]
            else:
                base_url = self._settings.resolve_base_url()
        self._base_url = base_url if base_url.endswith("/") else base_url + "/"

        self.token = token or self._settings.token
        self.username = username or self._settings.username
        self.password = password or self._settings.password

        # Absolute URLs are built from ``_base_url``, so an injected client is
        # used as-is (its own base_url, if any, is irrelevant). This is what lets
        # a consumer such as Home Assistant share one httpx client.
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._close_http = http_client is None

        self._v2: AsyncV2 | None = None
        self._v3: AsyncV3 | None = None

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

    async def get_api_token(self) -> str:
        """Return a valid API token, logging in (with retries) if needed."""
        if self.token is not None:
            return self.token

        for attempt in range(MAX_LOGIN_RETRIES):
            try:
                await self.login()
            except (BadCredentialsException, MissingCredentials):
                raise
            except MawaqitException:
                if attempt == MAX_LOGIN_RETRIES - 1:
                    raise
                await sleep(min(16, 2**attempt))
            else:
                if self.token is not None:
                    return self.token

        raise MawaqitException("Could not obtain an API token.")  # pragma: no cover

    async def login(self) -> None:
        """Obtain and cache an API token via HTTP basic auth."""
        if self.username is None or self.password is None:
            raise MissingCredentials("Please provide a MAWAQIT username and password.")

        response = await self._http.post(
            self._base_url + LOGIN_PATH, auth=(self.username, self.password)
        )
        raise_for_status(response)
        self.token = response.json()["apiAccessToken"]

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
            headers[API_TOKEN_HEADER] = await self.get_api_token()

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
            await sleep(min(8, 2**attempt))

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
