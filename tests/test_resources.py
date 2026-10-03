"""The operations of the API, on real responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mawaqit.types import HijriSettings, Mosque, PrayerTimes

from .conftest import UUID, Client, example, resolve

if TYPE_CHECKING:
    import respx


async def test_search_around_a_position(api: respx.MockRouter, client: Client) -> None:
    route = api.get("/2.0/mosque/search").respond(
        json=example("mosquesSearch", "around-a-position")
    )

    mosques = await resolve(
        client.mosques.search(lat=48.8414, lon=2.3557, items_per_page=2)
    )

    assert dict(route.calls.last.request.url.params) == {
        "lat": "48.8414",
        "lon": "2.3557",
        "itemsPerPage": "2",
    }
    assert all(isinstance(mosque, Mosque) for mosque in mosques)
    mosque = mosques[0]
    assert mosque.uuid == UUID
    assert mosque.proximity == 126
    assert mosque.women_space is True
    assert mosque.jumua_2 == "14:30"
    assert mosque.jumua_3 is None


async def test_search_by_words(api: respx.MockRouter, client: Client) -> None:
    route = api.get("/2.0/mosque/search").respond(
        json=example("mosquesSearch", "by-words")
    )

    mosques = await resolve(client.mosques.search(word="grande mosquee de paris"))

    assert dict(route.calls.last.request.url.params) == {
        "word": "grande mosquee de paris"
    }
    assert mosques[0].label == "GRANDE MOSQUÉE DE PARIS"
    assert mosques[0].proximity is None


async def test_search_finding_nothing(api: respx.MockRouter, client: Client) -> None:
    api.get("/2.0/mosque/search").respond(
        json=example("mosquesSearch", "nothing-found")
    )

    assert await resolve(client.mosques.search(word="x")) == []


async def test_prayer_times(api: respx.MockRouter, client: Client) -> None:
    api.get(f"/2.0/mosque/{UUID}/prayer-times").respond(
        json=example("mosquesPrayerTimes", "grande-mosquee-de-paris")
    )

    prayer_times = await resolve(client.mosques.prayer_times(UUID))

    assert isinstance(prayer_times, PrayerTimes)
    assert prayer_times.uuid == UUID
    assert prayer_times.timezone == "Europe/Paris"
    assert len(prayer_times.calendar) == 12
    assert len(prayer_times.calendar[0]["1"]) == 6
    assert len(prayer_times.iqama_calendar[11]["31"]) == 5
    assert prayer_times.jumua_2 == "14:30"
    assert prayer_times.hijri_adjustment == -1


async def test_hijri_settings(api: respx.MockRouter, client: Client) -> None:
    api.get(f"/3.0/mosque/{UUID}/hijri-date").respond(
        json=example("mosquesHijriSettings", "grande-mosquee-de-paris")
    )

    settings = await resolve(client.mosques.hijri_settings(UUID))

    assert settings == HijriSettings(hijri_adjustment=-1, hijri_date_force_to_30=False)
