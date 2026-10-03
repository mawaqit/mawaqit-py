"""The retries of the requests that failed temporarily."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import time_machine

from mawaqit import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    NotFoundError,
)

from .conftest import Client, resolve

if TYPE_CHECKING:
    import respx

SEARCH = "/2.0/mosque/search"


async def search(client: Client) -> object:
    return await resolve(client.mosques.search(word="paris"))


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
async def test_retries_temporary_errors(
    api: respx.MockRouter, client: Client, sleeps: list[float], status: int
) -> None:
    route = api.get(SEARCH)
    route.side_effect = [
        httpx.Response(status),
        httpx.Response(status),
        httpx.Response(200, json=[]),
    ]

    assert await search(client) == []

    assert route.call_count == 3
    # Exponential backoff with up to 25 % of jitter.
    assert 0.375 <= sleeps[0] <= 0.5
    assert 0.75 <= sleeps[1] <= 1


async def test_gives_up_after_max_retries(
    api: respx.MockRouter, client: Client, sleeps: list[float]
) -> None:
    route = api.get(SEARCH).respond(503)

    with pytest.raises(InternalServerError):
        await search(client)

    assert route.call_count == 3
    assert len(sleeps) == 2


async def test_does_not_retry_other_errors(
    api: respx.MockRouter, client: Client, sleeps: list[float]
) -> None:
    route = api.get(SEARCH).respond(404)

    with pytest.raises(NotFoundError):
        await search(client)

    assert route.call_count == 1
    assert not sleeps


async def test_without_retries(
    api: respx.MockRouter, client: Client, sleeps: list[float]
) -> None:
    route = api.get(SEARCH).respond(503)

    with pytest.raises(InternalServerError):
        await search(client.with_options(max_retries=0))

    assert route.call_count == 1
    assert not sleeps


@pytest.mark.parametrize(
    ("retry_after", "delay"),
    [
        ("2", 2),
        ("0.5", 0.5),
        ("Sat, 03 Oct 2026 12:00:30 GMT", 30),
    ],
)
@time_machine.travel("2026-10-03 12:00:00Z", tick=False)
async def test_honors_retry_after(
    api: respx.MockRouter,
    client: Client,
    sleeps: list[float],
    retry_after: str,
    delay: float,
) -> None:
    api.get(SEARCH).side_effect = [
        httpx.Response(429, headers={"Retry-After": retry_after}),
        httpx.Response(200, json=[]),
    ]

    await search(client)

    assert sleeps == [delay]


@pytest.mark.parametrize("retry_after", ["", "soon", "3600", "-1"])
async def test_ignores_unusable_retry_after(
    api: respx.MockRouter, client: Client, sleeps: list[float], retry_after: str
) -> None:
    api.get(SEARCH).side_effect = [
        httpx.Response(503, headers={"Retry-After": retry_after}),
        httpx.Response(200, json=[]),
    ]

    await search(client)

    assert 0.375 <= sleeps[0] <= 0.5


async def test_retries_network_errors(
    api: respx.MockRouter, client: Client, sleeps: list[float]
) -> None:
    api.get(SEARCH).side_effect = [httpx.ConnectError, httpx.Response(200, json=[])]

    assert await search(client) == []
    assert len(sleeps) == 1


@pytest.mark.parametrize(
    ("network_error", "error"),
    [
        (httpx.ConnectError, APIConnectionError),
        (httpx.RemoteProtocolError, APIConnectionError),
        (httpx.ReadTimeout, APITimeoutError),
    ],
)
async def test_network_errors(
    api: respx.MockRouter,
    client: Client,
    sleeps: list[float],
    network_error: type[httpx.TransportError],
    error: type[APIConnectionError],
) -> None:
    route = api.get(SEARCH).mock(side_effect=network_error)

    with pytest.raises(error) as caught:
        await search(client)

    assert type(caught.value) is error
    assert caught.value.body is None
    assert isinstance(caught.value.__cause__, network_error)
    assert route.call_count == 3
    assert len(sleeps) == 2
