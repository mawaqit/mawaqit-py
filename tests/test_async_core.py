"""Unit tests for the core async client: transport, auth, config."""

from __future__ import annotations

import httpx
import pytest
import respx

from mawaqit._async.client import AsyncMawaqitClient, login
from mawaqit._transport import query_params
from mawaqit.config import DEFAULT_API_BASE_URL, MawaqitSettings
from mawaqit.exceptions import (
    BadCredentialsException,
    MawaqitException,
    MissingCredentials,
    NotFoundException,
)

BASE = "https://api.test/"


def make_client(**kwargs: object) -> AsyncMawaqitClient:
    kwargs.setdefault("api_base_url", BASE)
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
# retries
# --------------------------------------------------------------------------- #
@respx.mock
async def test_request_retries_transient_5xx_then_succeeds() -> None:
    route = respx.get("https://api.test/2.0/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": 1})]
    )
    client = make_client(token="t")
    response = await client._request("GET", "2.0/x")
    assert response.json() == {"ok": 1}
    assert route.call_count == 2
    await client.close()


@respx.mock
async def test_request_retries_network_error_then_succeeds() -> None:
    respx.get("https://api.test/2.0/x").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json={"ok": 1})]
    )
    client = make_client(token="t")
    response = await client._request("GET", "2.0/x")
    assert response.json() == {"ok": 1}
    await client.close()


@respx.mock
async def test_request_exhausts_retries_on_5xx() -> None:
    respx.get("https://api.test/2.0/x").mock(return_value=httpx.Response(503))
    client = make_client(token="t", max_retries=1)
    with pytest.raises(MawaqitException):
        await client._request("GET", "2.0/x")
    await client.close()


@respx.mock
async def test_request_exhausts_retries_on_network_error() -> None:
    respx.get("https://api.test/2.0/x").mock(side_effect=httpx.ConnectError("boom"))
    client = make_client(token="t", max_retries=1)
    with pytest.raises(MawaqitException):
        await client._request("GET", "2.0/x")
    await client.close()


# --------------------------------------------------------------------------- #
# authentication — standalone login() primitive
# --------------------------------------------------------------------------- #
@respx.mock
async def test_login_returns_token() -> None:
    route = respx.post("https://api.test/2.0/me").mock(
        return_value=httpx.Response(200, json={"apiAccessToken": "newtok"})
    )
    assert await login("u", "p", api_base_url=BASE) == "newtok"
    assert route.calls.last.request.headers["authorization"].startswith("Basic ")


async def test_login_missing_credentials() -> None:
    with pytest.raises(MissingCredentials):
        await login(api_base_url=BASE)


@respx.mock
async def test_login_bad_credentials_not_retried() -> None:
    route = respx.post("https://api.test/2.0/me").mock(return_value=httpx.Response(401))
    with pytest.raises(BadCredentialsException):
        await login("u", "bad", api_base_url=BASE)
    assert route.call_count == 1  # 401 fails fast, no retry


@respx.mock
async def test_login_retries_transient_then_succeeds(
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
    assert await login("u", "p", api_base_url=BASE) == "tok2"
    assert slept == [1]  # 2 ** 0


@respx.mock
async def test_login_exhausts_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mawaqit._async.client.sleep", lambda _delay: _noop())
    respx.post("https://api.test/2.0/me").mock(return_value=httpx.Response(503))
    with pytest.raises(MawaqitException):
        await login("u", "p", api_base_url=BASE)


@respx.mock
async def test_login_reuses_injected_client_without_closing() -> None:
    respx.post("https://api.test/2.0/me").mock(
        return_value=httpx.Response(200, json={"apiAccessToken": "t"})
    )
    injected = httpx.AsyncClient()
    assert await login("u", "p", api_base_url=BASE, http_client=injected) == "t"
    assert not injected.is_closed
    await injected.aclose()


@respx.mock
async def test_login_token_feeds_an_authenticated_client() -> None:
    respx.post("https://api.test/2.0/me").mock(
        return_value=httpx.Response(200, json={"apiAccessToken": "ctok"})
    )
    thing = respx.get("https://api.test/2.0/thing").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = make_client(token=await login("u", "p", api_base_url=BASE))
    assert client.token == "ctok"
    await client._request("GET", "2.0/thing")
    assert thing.calls.last.request.headers["Api-Access-Token"] == "ctok"
    await client.close()


async def test_request_without_token_raises_missing_credentials() -> None:
    client = make_client()  # no token configured
    with pytest.raises(MissingCredentials):
        await client._request("GET", "2.0/thing")
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
async def test_base_url_defaults_to_the_default() -> None:
    client = AsyncMawaqitClient(token="t")
    assert client._base_url == DEFAULT_API_BASE_URL
    await client.close()


async def test_api_base_url_trailing_slash_is_added() -> None:
    client = AsyncMawaqitClient(api_base_url="https://x/api", token="t")
    assert client._base_url == "https://x/api/"
    await client.close()


async def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAWAQIT_API_BASE_URL", "https://env/api/")
    monkeypatch.setenv("MAWAQIT_TOKEN", "envtok")
    client = AsyncMawaqitClient()  # no args -> everything from env
    assert client._base_url == "https://env/api/"
    assert client.token == "envtok"
    await client.close()


async def test_explicit_arg_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAWAQIT_TOKEN", "envtok")
    client = AsyncMawaqitClient(token="argtok")
    assert client.token == "argtok"
    await client.close()


async def test_token_is_none_without_credentials() -> None:
    client = make_client()
    assert client.token is None
    await client.close()


async def test_secrets_are_not_leaked_in_repr() -> None:
    settings = MawaqitSettings(password="hunter2", token="s3cret")  # type: ignore[arg-type]
    assert "hunter2" not in repr(settings) and "s3cret" not in repr(settings)
    client = make_client(token="s3cret")
    assert client._token is not None and "s3cret" not in repr(client._token)
    await client.close()
