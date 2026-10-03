"""Fixtures shared by the tests: mocked API, both clients and examples."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import pytest
import respx

from mawaqit import AsyncMawaqitClient, MawaqitClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Iterator

T = TypeVar("T")

BASE_URL = "https://mawaqit.net/api"
TOKEN = "00000000-0000-4000-8000-000000000000"
UUID = "05b4d393-fb76-4d9b-b2a4-f98ab4c4b64f"
EXAMPLES = Path(__file__).parent / "examples"

Client = AsyncMawaqitClient | MawaqitClient


def example(operation: str, name: str) -> Any:
    """Return a real API response, copied from the spec by the generator."""
    return json.loads((EXAMPLES / operation / f"{name}.json").read_text())


async def resolve(value: Awaitable[T] | T) -> T:
    """Return the result of a call to either client."""
    if inspect.isawaitable(value):
        return cast("T", await value)
    return value


@pytest.fixture(autouse=True)
def _no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAWAQIT_TOKEN", raising=False)
    monkeypatch.delenv("MAWAQIT_BASE_URL", raising=False)


@pytest.fixture
def api() -> Iterator[respx.MockRouter]:
    """Mock the API: a request without a route fails the test."""
    with respx.mock(base_url=BASE_URL) as router:
        yield router


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record the waits between retries instead of waiting."""
    delays: list[float] = []

    async def async_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("mawaqit._base_client.anyio.sleep", async_sleep)
    monkeypatch.setattr("mawaqit._base_client.time.sleep", delays.append)
    return delays


@pytest.fixture(params=["async", "sync"])
async def client(request: pytest.FixtureRequest) -> AsyncIterator[Client]:
    """Each client in turn, with a token."""
    if request.param == "async":
        async with AsyncMawaqitClient(token=TOKEN) as async_client:
            yield async_client
    else:
        with MawaqitClient(token=TOKEN) as sync_client:
            yield sync_client
