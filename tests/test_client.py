"""Tests for AsyncMawaqitClient HTTP methods, error handling and token flow.

Instead of mocking aiohttp at the transport level, these tests inject a fake
session into the client (a capability the client supports directly). This keeps
the tests independent of the installed aiohttp version.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mawaqit import AsyncMawaqitClient
from mawaqit.consts import MAX_LOGIN_RETRIES
from mawaqit.exceptions import (
    BadCredentialsException,
    MawaqitException,
    MissingCredentials,
    NoMosqueAround,
    NoMosqueFound,
    NotFoundException,
)

MOSQUE = {"uuid": "abc", "name": "Test Mosque"}


class FakeResponse:
    """Minimal stand-in for an aiohttp ClientResponse."""

    def __init__(self, status, json_data=None, text_data=None):
        self.status = status
        self._json = json_data
        self._text = text_data

    async def json(self):
        return self._json

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeRequestContext:
    """Awaitable and async-context-manager wrapper, like aiohttp request calls."""

    def __init__(self, response):
        self._response = response

    def __await__(self):
        async def _coro():
            return self._response

        return _coro().__await__()

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Returns queued responses in call order; records calls for assertions."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeRequestContext(self._responses.pop(0))

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        return FakeRequestContext(self._responses.pop(0))

    async def close(self):
        pass


def make_client(responses, **kwargs):
    """Build a client backed by a fake session with the given responses."""
    return AsyncMawaqitClient(session=FakeSession(responses), **kwargs)


# --- _raise_for_status, exercised through fetch_mosque_by_id ---


async def test_fetch_mosque_by_id_success():
    client = make_client([FakeResponse(200, json_data=MOSQUE)], token="t")
    assert await client.fetch_mosque_by_id("abc") == MOSQUE


async def test_fetch_mosque_by_id_without_uuid_raises():
    client = make_client([], token="t")
    with pytest.raises(ValueError):
        await client.fetch_mosque_by_id(None)


async def test_unauthorized_raises_bad_credentials():
    client = make_client([FakeResponse(401)], token="t")
    with pytest.raises(BadCredentialsException):
        await client.fetch_mosque_by_id("abc")


async def test_not_found_raises_not_found():
    client = make_client([FakeResponse(404)], token="t")
    with pytest.raises(NotFoundException):
        await client.fetch_mosque_by_id("abc")


async def test_unexpected_status_raises_mawaqit_exception():
    client = make_client([FakeResponse(500)], token="t")
    with pytest.raises(MawaqitException):
        await client.fetch_mosque_by_id("abc")


# --- all_mosques_neighborhood ---


async def test_neighborhood_without_coordinates_raises():
    client = make_client([], token="t")
    with pytest.raises(MissingCredentials):
        await client.all_mosques_neighborhood()


async def test_neighborhood_success():
    client = make_client(
        [FakeResponse(200, json_data=[MOSQUE])], latitude=48.8, longitude=2.3, token="t"
    )
    assert await client.all_mosques_neighborhood() == [MOSQUE]


async def test_neighborhood_empty_raises():
    client = make_client(
        [FakeResponse(200, json_data=[])], latitude=48.8, longitude=2.3, token="t"
    )
    with pytest.raises(NoMosqueAround):
        await client.all_mosques_neighborhood()


# --- fetch_mosques_by_keyword ---


async def test_keyword_without_keyword_raises():
    client = make_client([], token="t")
    with pytest.raises(MissingCredentials):
        await client.fetch_mosques_by_keyword(None)


async def test_keyword_success():
    client = make_client([FakeResponse(200, json_data=[MOSQUE])], token="t")
    assert await client.fetch_mosques_by_keyword("paris", page=2) == [MOSQUE]


async def test_keyword_empty_raises():
    client = make_client([FakeResponse(200, json_data=[])], token="t")
    with pytest.raises(NoMosqueFound):
        await client.fetch_mosques_by_keyword("zzz")


# --- fetch_prayer_times ---


async def test_prayer_times_with_explicit_mosque():
    client = make_client(
        [FakeResponse(200, json_data={"times": []})], mosque="abc", token="t"
    )
    assert await client.fetch_prayer_times() == {"times": []}


async def test_prayer_times_without_mosque_uses_neighborhood():
    client = make_client(
        [
            FakeResponse(200, json_data=[MOSQUE]),
            FakeResponse(200, json_data={"times": [1]}),
        ],
        latitude=48.8,
        longitude=2.3,
        token="t",
    )
    assert await client.fetch_prayer_times() == {"times": [1]}


# --- login and get_api_token ---


async def test_login_without_credentials_raises():
    client = make_client([])
    with pytest.raises(MissingCredentials):
        await client.login()


async def test_get_api_token_returns_existing_token():
    client = make_client([], token="existing")
    assert await client.get_api_token() == "existing"


async def test_get_api_token_logs_in():
    client = make_client(
        [FakeResponse(200, text_data='{"apiAccessToken": "NEW"}')],
        username="u",
        password="p",
    )
    assert await client.get_api_token() == "NEW"


async def test_get_api_token_bad_credentials_is_reraised():
    client = make_client([FakeResponse(401)], username="u", password="p")
    with pytest.raises(BadCredentialsException):
        await client.get_api_token()


async def test_get_api_token_retries_then_succeeds():
    client = make_client(
        [
            FakeResponse(500),
            FakeResponse(200, text_data='{"apiAccessToken": "AFTER_RETRY"}'),
        ],
        username="u",
        password="p",
    )
    with patch("mawaqit.mawaqit_async.sleep", new=AsyncMock()):
        assert await client.get_api_token() == "AFTER_RETRY"


async def test_get_api_token_exhausts_retries():
    client = make_client(
        [FakeResponse(500)] * MAX_LOGIN_RETRIES, username="u", password="p"
    )
    with patch("mawaqit.mawaqit_async.sleep", new=AsyncMock()):
        with pytest.raises(MawaqitException):
            await client.get_api_token()
