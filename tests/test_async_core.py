"""Unit tests for the core async client: transport, auth, config."""

from __future__ import annotations

import httpx
import pytest
import respx

from mawaqit._async.client import AsyncMawaqitClient
from mawaqit._transport import query_params
from mawaqit.config import ENVIRONMENT_BASE_URLS, Environment, MawaqitSettings
from mawaqit.exceptions import (
    BadCredentialsException,
    MawaqitException,
    MissingCredentials,
    NotFoundException,
)

BASE = "https://api.test/"


def make_client(**kwargs: object) -> AsyncMawaqitClient:
    kwargs.setdefault("base_url", BASE)
    return AsyncMawaqitClient(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# transport helpers
# --------------------------------------------------------------------------- #
def test_query_params_drops_none() -> None:
    assert query_params(a=1, b=None, c="x") == {"a": 1, "c": "x"}


@respx.mock
async def test_request_injects_token_and_returns_response() -> None:
    route = respx.get("https://api.test/2.0/thing").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = make_client(token="tok")
    response = await client._request("GET", "2.0/thing")
    assert response.json() == {"ok": True}
    assert route.calls.last.request.headers["Api-Access-Token"] == "tok"
    await client.close()


@respx.mock
async def test_unauthenticated_request_omits_token_header() -> None:
    route = respx.get("https://api.test/2.0/public").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = make_client()  # no token
    await client._request("GET", "2.0/public", authenticated=False)
    assert "Api-Access-Token" not in route.calls.last.request.headers
    await client.close()


@respx.mock
@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, BadCredentialsException),
        (404, NotFoundException),
        (500, MawaqitException),
    ],
)
async def test_status_mapping(status: int, exception: type[Exception]) -> None:
    respx.get(f"https://api.test/2.0/s{status}").mock(
        return_value=httpx.Response(status)
    )
    client = make_client(token="t")
    with pytest.raises(exception):
        await client._request("GET", f"2.0/s{status}")
    await client.close()


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #
async def test_get_api_token_returns_existing() -> None:
    client = make_client(token="abc")
    assert await client.get_api_token() == "abc"
    await client.close()


@respx.mock
async def test_login_success_caches_token() -> None:
    route = respx.post("https://api.test/2.0/me").mock(
        return_value=httpx.Response(200, json={"apiAccessToken": "newtok"})
    )
    client = make_client(username="u", password="p")
    assert await client.get_api_token() == "newtok"
    assert client.token == "newtok"
    assert route.calls.last.request.headers["authorization"].startswith("Basic ")
    await client.close()


async def test_login_missing_credentials() -> None:
    client = make_client()
    with pytest.raises(MissingCredentials):
        await client.login()
    # get_api_token re-raises MissingCredentials without retrying.
    with pytest.raises(MissingCredentials):
        await client.get_api_token()
    await client.close()


@respx.mock
async def test_login_bad_credentials_not_retried() -> None:
    respx.post("https://api.test/2.0/me").mock(return_value=httpx.Response(401))
    client = make_client(username="u", password="bad")
    with pytest.raises(BadCredentialsException):
        await client.get_api_token()
    await client.close()


@respx.mock
async def test_get_api_token_retries_transient_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slept: list[float] = []

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr("mawaqit._async.client.sleep", fake_sleep)
    respx.post("https://api.test/2.0/me").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"apiAccessToken": "tok2"}),
        ]
    )
    client = make_client(username="u", password="p")
    assert await client.get_api_token() == "tok2"
    assert slept == [1]  # 2 ** 0
    await client.close()


@respx.mock
async def test_get_api_token_exhausts_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mawaqit._async.client.sleep", lambda _delay: _noop())
    respx.post("https://api.test/2.0/me").mock(return_value=httpx.Response(503))
    client = make_client(username="u", password="p")
    with pytest.raises(MawaqitException):
        await client.get_api_token()
    await client.close()


async def _noop() -> None:
    return None


# --------------------------------------------------------------------------- #
# session ownership & lifecycle
# --------------------------------------------------------------------------- #
async def test_injected_client_is_not_closed() -> None:
    injected = httpx.AsyncClient()
    client = make_client(http_client=injected)
    await client.close()
    assert not injected.is_closed
    await injected.aclose()


async def test_owned_client_is_closed() -> None:
    client = make_client()
    await client.close()
    assert client._http.is_closed


async def test_context_manager_closes_owned_client() -> None:
    async with make_client() as client:
        http = client._http
    assert http.is_closed


# --------------------------------------------------------------------------- #
# base URL resolution
# --------------------------------------------------------------------------- #
async def test_base_url_from_environment() -> None:
    client = AsyncMawaqitClient(environment=Environment.PRODUCTION, token="t")
    assert client._base_url == ENVIRONMENT_BASE_URLS[Environment.PRODUCTION]
    await client.close()


async def test_base_url_defaults_to_production() -> None:
    client = AsyncMawaqitClient(token="t")
    assert client._base_url == ENVIRONMENT_BASE_URLS[Environment.PRODUCTION]
    await client.close()


async def test_base_url_from_settings() -> None:
    settings = MawaqitSettings(base_url="https://s/api/")
    client = AsyncMawaqitClient(settings=settings)
    assert client._base_url == "https://s/api/"
    await client.close()


async def test_base_url_trailing_slash_is_added() -> None:
    client = AsyncMawaqitClient(base_url="https://x/api", token="t")
    assert client._base_url == "https://x/api/"
    await client.close()
