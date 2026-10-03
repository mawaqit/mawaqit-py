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


def prayer_times_payload() -> dict[str, Any]:
    """Return a prayer times response shaped like the API's."""
    days = {
        str(day): ["06:20", "07:53", "13:45", "16:46", "19:29", "20:56"]
        for day in range(1, 31)
    }
    iqama = {day: ["+8", "+8", "+8", "+0", "+8"] for day in days}
    return {
        "id": 1,
        "uuid": UUID,
        "name": "GRANDE MOSQUÉE DE PARIS - Paris",
        "label": "GRANDE MOSQUÉE DE PARIS - Paris",
        "type": "MOSQUE",
        "partner": True,
        "streamUrl": None,
        "paymentWebsite": None,
        "localisation": "Place du puits de l'hermite 75005 Paris France",
        "countryCode": "FR",
        "timezone": "Europe/Paris",
        "phone": None,
        "email": None,
        "site": None,
        "association": None,
        "image": None,
        "interiorPicture": None,
        "exteriorPicture": None,
        "logo": None,
        "url": "https://mawaqit.net/fr/grande-mosquee-de-paris",
        "latitude": 48.84,
        "longitude": 2.35,
        "womenSpace": True,
        "janazaPrayer": True,
        "aidPrayer": True,
        "childrenCourses": None,
        "adultCourses": None,
        "ramadanMeal": None,
        "handicapAccessibility": None,
        "ablutions": True,
        "parking": False,
        "otherInfo": None,
        "closed": None,
        "announcements": [],
        "events": [],
        "flash": {
            "content": "Iftar at the mosque",
            "uuid": UUID,
            "expire": 1791072000,
            "startDate": "2026-10-01",
            "endDate": "2026-10-04",
            "color": "#d9ad0f",
            "orientation": "ltr",
        },
        "aidPrayerTime": None,
        "aidPrayerTime2": None,
        "aidPrayerTime3": None,
        "jumua": "13:50",
        "jumua2": "14:30",
        "jumua3": None,
        "jumuaAsDuhr": False,
        "imsakNbMinBeforeFajr": 10,
        "hijriAdjustment": -1,
        "hijriDateForceTo30": False,
        "times": ["06:20", "13:45", "16:46", "19:29", "20:56"],
        "shuruq": "07:53",
        "iqamaEnabled": True,
        "calendar": [days] * 12,
        "iqamaCalendar": [iqama] * 12,
    }


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
