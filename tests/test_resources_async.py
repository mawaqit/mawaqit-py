"""Unit tests for the async v2/v3 resource wrappers (respx, no network)."""

from __future__ import annotations

import httpx
import respx
from _samples import build_sample

from mawaqit._async.client import AsyncMawaqitClient
from mawaqit._generated import v2 as m2
from mawaqit._generated import v3 as m3
from mawaqit.responses import AnnouncementsAndEvents

BASE = "https://api.test/"


def client() -> AsyncMawaqitClient:
    return AsyncMawaqitClient(base_url=BASE, token="t")


# --------------------------------------------------------------------------- #
# v2
# --------------------------------------------------------------------------- #
@respx.mock
async def test_v2_search_sends_params_and_parses_list() -> None:
    route = respx.get(BASE + "2.0/mosque/search").mock(
        return_value=httpx.Response(200, json=[build_sample(m2.Mosque)])
    )
    c = client()
    result = await c.v2.mosque.search(word="paris", lat=48.8, lon=2.3, radius=5)
    assert isinstance(result[0], m2.Mosque)
    request = route.calls.last.request
    assert request.url.params["word"] == "paris"
    assert request.url.params["lat"] == "48.8"
    assert "page" not in request.url.params  # None params are dropped
    await c.close()


@respx.mock
async def test_v2_list_uuid_parses_str_list() -> None:
    respx.get(BASE + "2.0/mosque/list-uuid").mock(
        return_value=httpx.Response(200, json=["a", "b"])
    )
    c = client()
    assert await c.v2.mosque.list_uuid(page=2) == ["a", "b"]
    await c.close()


@respx.mock
async def test_v2_prayer_times() -> None:
    route = respx.get(BASE + "2.0/mosque/u1/prayer-times").mock(
        return_value=httpx.Response(200, json=build_sample(m2.PrayerTimes))
    )
    c = client()
    result = await c.v2.mosque.prayer_times("u1", calendar=True, updated_at=123)
    assert isinstance(result, m2.PrayerTimes)
    assert route.calls.last.request.url.params["updatedAt"] == "123"
    await c.close()


@respx.mock
async def test_v2_weather() -> None:
    respx.get(BASE + "2.0/mosque/u1/weather").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Weather))
    )
    c = client()
    assert isinstance(await c.v2.mosque.weather("u1"), m2.Weather)
    await c.close()


@respx.mock
async def test_v2_data_returns_dict() -> None:
    respx.get(BASE + "2.0/mosque/42/data").mock(
        return_value=httpx.Response(200, json={"anything": 1})
    )
    c = client()
    assert await c.v2.mosque.data("42") == {"anything": 1}
    await c.close()


@respx.mock
async def test_v2_map() -> None:
    respx.get(BASE + "2.0/mosque/map/FR").mock(
        return_value=httpx.Response(200, json=build_sample(m2.MosqueForMap))
    )
    c = client()
    assert isinstance(await c.v2.mosque.map("FR"), m2.MosqueForMap)
    await c.close()


@respx.mock
async def test_v2_list() -> None:
    respx.get(BASE + "2.0/mosque").mock(
        return_value=httpx.Response(200, json=[build_sample(m2.Mosque)])
    )
    c = client()
    result = await c.v2.mosque.list(order="asc", page=1)
    assert isinstance(result[0], m2.Mosque)
    await c.close()


@respx.mock
async def test_v2_hadith_random() -> None:
    respx.get(BASE + "2.0/hadith/random").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Hadith))
    )
    c = client()
    assert isinstance(await c.v2.hadith.random(lang="fr", max_length=200), m2.Hadith)
    await c.close()


@respx.mock
async def test_v2_statistic_favorite_and_unfavorite() -> None:
    fav = respx.post(BASE + "2.0/statistic/mosque/u1/favorite").mock(
        return_value=httpx.Response(204)
    )
    unfav = respx.delete(BASE + "2.0/statistic/mosque/u1/favorite").mock(
        return_value=httpx.Response(204)
    )
    c = client()
    assert await c.v2.statistic.favorite("u1") is None
    assert await c.v2.statistic.unfavorite("u1") is None
    assert fav.called and unfav.called
    await c.close()


@respx.mock
async def test_v2_mosque_favorite_aliases() -> None:
    fav = respx.post(BASE + "2.0/statistic/mosque/u1/favorite").mock(
        return_value=httpx.Response(204)
    )
    unfav = respx.delete(BASE + "2.0/statistic/mosque/u1/favorite").mock(
        return_value=httpx.Response(204)
    )
    c = client()
    assert await c.v2.mosque.favorite("u1") is None
    assert await c.v2.mosque.unfavorite("u1") is None
    assert fav.called and unfav.called
    await c.close()


@respx.mock
async def test_v2_support() -> None:
    respx.get(BASE + "2.0/support").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Support))
    )
    c = client()
    assert isinstance(await c.v2.support.get(country="FR"), m2.Support)
    await c.close()


@respx.mock
async def test_v2_me() -> None:
    respx.get(BASE + "2.0/me").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Me))
    )
    c = client()
    assert isinstance(await c.v2.me.get(), m2.Me)
    await c.close()


# --------------------------------------------------------------------------- #
# v3
# --------------------------------------------------------------------------- #
@respx.mock
async def test_v3_times() -> None:
    respx.get(BASE + "3.0/mosque/u1/times").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Times))
    )
    c = client()
    assert isinstance(await c.v3.mosque.times("u1"), m3.Times)
    await c.close()


@respx.mock
async def test_v3_info() -> None:
    respx.get(BASE + "3.0/mosque/u1/info").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Info))
    )
    c = client()
    assert isinstance(await c.v3.mosque.info("u1"), m3.Info)
    await c.close()


@respx.mock
async def test_v3_by_id_and_by_slug() -> None:
    respx.get(BASE + "3.0/mosque/42").mock(
        return_value=httpx.Response(200, json=build_sample(m3.InfoById))
    )
    respx.get(BASE + "3.0/mosque/slug/grande-mosquee").mock(
        return_value=httpx.Response(200, json=build_sample(m3.InfoById))
    )
    c = client()
    assert isinstance(await c.v3.mosque.by_id("42"), m3.InfoById)
    assert isinstance(await c.v3.mosque.by_slug("grande-mosquee"), m3.InfoById)
    await c.close()


@respx.mock
async def test_v3_config() -> None:
    respx.get(BASE + "3.0/mosque/u1/config").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Config))
    )
    c = client()
    assert isinstance(await c.v3.mosque.config("u1"), m3.Config)
    await c.close()


@respx.mock
async def test_v3_announcements() -> None:
    payload = {
        "announcements": [build_sample(m3.Announcement)],
        "events": [build_sample(m3.Event)],
    }
    respx.get(BASE + "3.0/mosque/u1/announcements").mock(
        return_value=httpx.Response(200, json=payload)
    )
    c = client()
    result = await c.v3.mosque.announcements("u1")
    assert isinstance(result, AnnouncementsAndEvents)
    assert isinstance(result.announcements[0], m3.Announcement)
    assert isinstance(result.events[0], m3.Event)
    await c.close()


@respx.mock
async def test_v3_flash_message() -> None:
    respx.get(BASE + "3.0/mosque/u1/flash-message").mock(
        return_value=httpx.Response(200, json=[build_sample(m3.FlashMessage)])
    )
    c = client()
    result = await c.v3.mosque.flash_message("u1")
    assert isinstance(result[0], m3.FlashMessage)
    await c.close()


@respx.mock
async def test_v3_hijri_date() -> None:
    respx.get(BASE + "3.0/mosque/u1/hijri-date").mock(
        return_value=httpx.Response(200, json=build_sample(m3.HijriDate))
    )
    c = client()
    assert isinstance(await c.v3.mosque.hijri_date("u1"), m3.HijriDate)
    await c.close()


@respx.mock
async def test_v3_messages() -> None:
    respx.get(BASE + "3.0/mosque/u1/messages").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Messages))
    )
    c = client()
    assert isinstance(await c.v3.mosque.messages("u1"), m3.Messages)
    await c.close()


@respx.mock
async def test_v3_androidtv_life_status_sends_body() -> None:
    route = respx.post(BASE + "3.0/mosque/u1/androidtv-life-status").mock(
        return_value=httpx.Response(201)
    )
    c = client()
    assert (
        await c.v3.mosque.androidtv_life_status("u1", device_id="d1", brand="x") is None
    )
    body = route.calls.last.request.content
    assert b"device-id" in body and b"d1" in body
    assert b"model" not in body  # None fields dropped from the body
    await c.close()


@respx.mock
async def test_v3_installations_returns_dict() -> None:
    respx.get(BASE + "3.0/statistic/installations").mock(
        return_value=httpx.Response(200, json={"FR": 100, "DZ": 50})
    )
    c = client()
    assert await c.v3.statistic.installations() == {"FR": 100, "DZ": 50}
    await c.close()


# --------------------------------------------------------------------------- #
# namespace behaviour
# --------------------------------------------------------------------------- #
async def test_version_namespaces_are_cached() -> None:
    c = client()
    assert c.v2 is c.v2
    assert c.v3 is c.v3
    await c.close()


@respx.mock
async def test_both_versions_share_the_same_token() -> None:
    v2_route = respx.get(BASE + "2.0/mosque/u1/weather").mock(
        return_value=httpx.Response(200, json=build_sample(m2.Weather))
    )
    v3_route = respx.get(BASE + "3.0/mosque/u1/times").mock(
        return_value=httpx.Response(200, json=build_sample(m3.Times))
    )
    c = client()
    await c.v2.mosque.weather("u1")
    await c.v3.mosque.times("u1")
    assert v2_route.calls.last.request.headers["Api-Access-Token"] == "t"
    assert v3_route.calls.last.request.headers["Api-Access-Token"] == "t"
    await c.close()
