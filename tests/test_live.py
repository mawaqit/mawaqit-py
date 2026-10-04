"""Tests against the real API, run with `pytest -m live`.

The operations that need a token run when `MAWAQIT_TOKEN` is set.
"""

from __future__ import annotations

import os

import pytest

from mawaqit import AsyncMawaqitClient, MawaqitClient, hijri

from .conftest import UUID

# Read before the fixtures clear the environment.
LIVE_TOKEN = os.environ.get("MAWAQIT_TOKEN")

pytestmark = pytest.mark.live
needs_token = pytest.mark.skipif(not LIVE_TOKEN, reason="MAWAQIT_TOKEN is not set")


async def test_search() -> None:
    async with AsyncMawaqitClient() as client:
        around = await client.mosques.search(lat=48.8414, lon=2.3557)
        by_words = await client.mosques.search(word="grande mosquee de paris")

    assert around[0].uuid == UUID
    assert around[0].proximity is not None
    assert UUID in {mosque.uuid for mosque in by_words}


@needs_token
async def test_mosque() -> None:
    async with AsyncMawaqitClient(token=LIVE_TOKEN) as client:
        prayer_times = await client.mosques.prayer_times(UUID)
        settings = await client.mosques.hijri_settings(UUID)
        config = await client.mosques.config(UUID)
        flash = await client.mosques.flash_message(UUID)
        mosque = await client.mosques.get(prayer_times.id)

    assert prayer_times.uuid == UUID
    assert len(prayer_times.calendar) == 12
    assert -2 <= settings.hijri_adjustment <= 2
    assert hijri.today(settings, prayer_times.timezone).year >= 1448
    assert len(config.adhan_enabled_by_prayer) == 5
    assert not prayer_times.model_extra
    assert not config.model_extra
    assert flash is None or not flash.model_extra
    assert mosque.uuid == UUID
    assert not mosque.model_extra


@needs_token
def test_sync_client() -> None:
    with MawaqitClient(token=LIVE_TOKEN) as client:
        assert client.mosques.hijri_settings(UUID).model_extra == {}
