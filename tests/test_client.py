"""The options, authentication and lifecycle of the clients."""

from __future__ import annotations

import base64
import uuid

import httpx
import pytest
import respx

from mawaqit import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    AsyncMawaqitClient,
    MawaqitClient,
    MawaqitError,
    __version__,
)

from .conftest import TOKEN, UUID, Client, resolve

ACCOUNT = {"id": 1, "apiAccessToken": TOKEN, "apiQuota": 300, "apiCallNumber": 12}


def test_defaults() -> None:
    client = MawaqitClient()

    assert client.token is None
    assert client.base_url == DEFAULT_BASE_URL
    assert client.timeout == DEFAULT_TIMEOUT
    assert client.max_retries == DEFAULT_MAX_RETRIES


def test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAWAQIT_TOKEN", TOKEN)
    monkeypatch.setenv("MAWAQIT_BASE_URL", "https://staging.example/api/")

    client = AsyncMawaqitClient()

    assert client.token == TOKEN
    assert client.base_url == "https://staging.example/api"


def test_arguments_override_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAWAQIT_TOKEN", "from-environment")
    monkeypatch.setenv("MAWAQIT_BASE_URL", "https://staging.example/api")

    client = MawaqitClient(token=TOKEN, base_url="https://local.test/api")

    assert client.token == TOKEN
    assert client.base_url == "https://local.test/api"


def test_negative_max_retries() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        MawaqitClient(max_retries=-1)


def test_repr_hides_token() -> None:
    assert repr(MawaqitClient(token=TOKEN)) == (
        "MawaqitClient(base_url='https://mawaqit.net/api')"
    )


async def test_with_options(client: Client) -> None:
    copy = client.with_options(token="other", timeout=5, max_retries=0)

    assert type(copy) is type(client)
    assert (copy.token, copy.timeout, copy.max_retries) == ("other", 5, 0)
    assert copy.base_url == client.base_url
    assert copy._http is client._http
    assert client.with_options().token == TOKEN


async def test_async_client_closes_its_http_client() -> None:
    async with AsyncMawaqitClient() as client:
        assert not client._http.is_closed
    assert client._http.is_closed


def test_sync_client_closes_its_http_client() -> None:
    with MawaqitClient() as client:
        assert not client._http.is_closed
    assert client._http.is_closed


async def test_given_http_clients_stay_open() -> None:
    async with httpx.AsyncClient() as async_http:
        async with AsyncMawaqitClient(http_client=async_http) as async_client:
            assert async_client._http is async_http
        await async_client.with_options(token=TOKEN).close()
        assert not async_http.is_closed
    with httpx.Client() as sync_http:
        with MawaqitClient(http_client=sync_http):
            pass
        assert not sync_http.is_closed


async def test_headers(api: respx.MockRouter, client: Client) -> None:
    route = api.get(f"/3.0/mosque/{UUID}/hijri-date").respond(
        json={"hijriAdjustment": 0, "hijriDateForceTo30": False}
    )

    await resolve(client.mosques.hijri_settings(UUID))

    headers = route.calls.last.request.headers
    assert headers["Api-Access-Token"] == TOKEN
    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"] == f"mawaqit-python/{__version__}"
    assert "Authorization" not in headers


async def test_public_operation_without_token(api: respx.MockRouter) -> None:
    route = api.get("/2.0/hadith/random").respond(json=[])

    async with AsyncMawaqitClient() as client:
        assert await client.hadiths.random() is None

    assert "Api-Access-Token" not in route.calls.last.request.headers


async def test_missing_token(api: respx.MockRouter) -> None:
    async with AsyncMawaqitClient() as async_client:
        with pytest.raises(MawaqitError, match="No API token"):
            await async_client.mosques.prayer_times(UUID)
    with MawaqitClient() as sync_client, pytest.raises(MawaqitError):
        sync_client.mosques.prayer_times(UUID)
    assert not api.calls


async def test_basic_auth(api: respx.MockRouter, client: Client) -> None:
    route = api.post("/2.0/me").respond(json=ACCOUNT)

    account = await resolve(
        client.auth.login(email="imam@example.com", password="s3cr:t")
    )

    credentials = base64.b64encode(b"imam@example.com:s3cr:t").decode()
    headers = route.calls.last.request.headers
    assert headers["Authorization"] == f"Basic {credentials}"
    assert "Api-Access-Token" not in headers
    assert account.api_access_token == TOKEN


async def test_path_parameters_are_quoted(
    api: respx.MockRouter, client: Client
) -> None:
    route = api.get(url__regex=r"/hijri-date$").respond(
        json={"hijriAdjustment": 0, "hijriDateForceTo30": False}
    )

    await resolve(client.mosques.hijri_settings("../../2.0/me"))

    assert route.calls.last.request.url.raw_path == (
        b"/api/3.0/mosque/..%2F..%2F2.0%2Fme/hijri-date"
    )


async def test_base_url_of_the_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAWAQIT_BASE_URL", "https://staging.example/api/")
    with respx.mock(assert_all_called=True) as router:
        staging = router.get("https://staging.example/api/2.0/mosque/search")
        local = router.get("https://mawaqit.test/api/2.0/mosque/search")
        staging.respond(json=[])
        local.respond(json=[])
        async with AsyncMawaqitClient(token=TOKEN) as client:
            await client.mosques.search(word="paris")
            other = client.with_options(base_url="https://mawaqit.test/api")
            await other.mosques.search(word="paris")


async def test_timeout_of_the_requests(api: respx.MockRouter, client: Client) -> None:
    route = api.get("/2.0/mosque/search").respond(json=[])

    await resolve(client.with_options(timeout=5).mosques.search(word="paris"))

    assert route.calls.last.request.extensions["timeout"] == {
        "connect": 5,
        "read": 5,
        "write": 5,
        "pool": 5,
    }


async def test_query_is_encoded(api: respx.MockRouter, client: Client) -> None:
    route = api.get("/2.0/mosque/search").respond(json=[])

    await resolve(client.mosques.search(word="mosquée & école", page=2))

    # The "&" of the word must not split it into two parameters.
    assert dict(route.calls.last.request.url.params) == {
        "word": "mosquée & école",
        "page": "2",
    }


async def test_uuid_objects(api: respx.MockRouter, client: Client) -> None:
    route = api.get(f"/3.0/mosque/{UUID}/hijri-date").respond(
        json={"hijriAdjustment": 0, "hijriDateForceTo30": False}
    )

    await resolve(client.mosques.hijri_settings(uuid.UUID(UUID)))  # type: ignore[arg-type]

    assert route.called


async def test_empty_uuid(api: respx.MockRouter, client: Client) -> None:
    with pytest.raises(ValueError, match="uuid cannot be empty"):
        await resolve(client.mosques.prayer_times(""))
    assert not api.calls
