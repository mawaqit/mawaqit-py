"""Smoke tests for the unasync-generated sync client.

The async suite is the exhaustive, 100%-covered source of truth; these tests
verify that the mechanical async->sync transform yields a working, equivalent
client (auth, a v2 and a v3 call, error mapping, session ownership, lifecycle).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from _samples import build_sample

from mawaqit import MawaqitClient
from mawaqit import login_sync as login
from mawaqit._generated import v2 as m2
from mawaqit._generated import v3 as m3
from mawaqit.exceptions import NotFoundException

BASE = "https://api.test/"


def test_sync_client_is_distinct_from_async() -> None:
    # The generated client carries the renamed public symbol.
    assert MawaqitClient.__name__ == "MawaqitClient"


@respx.mock
def test_sync_login_then_v2_and_v3_calls_share_token() -> None:
    login_route = respx.post(BASE + "2.0/me").mock(
        return_value=httpx.Response(200, json={"apiAccessToken": "tok"})
    )
    weather = respx.get(BASE + "2.0/mosque/u1/weather").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Weather))
    )
    times = respx.get(BASE + "3.0/mosque/u1/times").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Times))
    )

    token = login("u", "p", api_base_url=BASE)  # sync login primitive
    with MawaqitClient(api_base_url=BASE, token=token) as client:
        assert isinstance(client.v2.mosque.weather("u1"), m2.Weather)
        assert isinstance(client.v3.mosque.times("u1"), m3.Times)
        assert client.v2 is client.v2  # cached namespace

    assert login_route.called
    assert token == "tok"
    assert weather.calls.last.request.headers["Api-Access-Token"] == "tok"
    assert times.calls.last.request.headers["Api-Access-Token"] == "tok"


@respx.mock
def test_sync_error_mapping() -> None:
    respx.get(BASE + "3.0/mosque/missing/info").mock(return_value=httpx.Response(404))
    client = MawaqitClient(api_base_url=BASE, token="t")
    with pytest.raises(NotFoundException):
        client.v3.mosque.info("missing")
    client.close()


def test_sync_injected_client_is_not_closed() -> None:
    injected = httpx.Client()
    client = MawaqitClient(api_base_url=BASE, token="t", http_client=injected)
    client.close()
    assert not injected.is_closed
    injected.close()
