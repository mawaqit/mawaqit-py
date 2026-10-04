"""The Hijri date, against the algorithm of the MAWAQIT mosque screens."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import time_machine

from mawaqit import hijri
from mawaqit.hijri import HijriDate, HijriMonth
from mawaqit.types import HijriSettings, PrayerTimes

from .conftest import example

MONTH_STARTS = json.loads(
    (Path(__file__).parent / "data" / "kuwaiti_month_starts.json").read_text()
)["month_starts"]


def settings(adjustment: int = 0, *, force_30: bool = False) -> HijriSettings:
    return HijriSettings(hijri_adjustment=adjustment, hijri_date_force_to_30=force_30)


def test_kuwaiti_matches_mawaqit_every_day_from_1990_to_2060() -> None:
    """Check each day against the month starts computed by the MAWAQIT code."""
    for (start, year, month), (end, *_) in pairwise(MONTH_STARTS):
        first = date.fromisoformat(start)
        for offset in range((date.fromisoformat(end) - first).days):
            assert hijri.kuwaiti(first + timedelta(days=offset)) == HijriDate(
                year, HijriMonth(month), offset + 1
            )


def test_without_settings() -> None:
    assert hijri.from_gregorian(date(2026, 10, 3)) == HijriDate(
        1448, HijriMonth.RABI_AL_THANI, 21
    )


@pytest.mark.parametrize(
    ("adjustment", "expected"),
    [
        (-2, HijriDate(1447, HijriMonth.SHABAN, 28)),
        (-1, HijriDate(1447, HijriMonth.SHABAN, 29)),
        (0, HijriDate(1447, HijriMonth.RAMADAN, 1)),
        (1, HijriDate(1447, HijriMonth.RAMADAN, 2)),
    ],
)
def test_adjustment(adjustment: int, expected: HijriDate) -> None:
    assert hijri.from_gregorian(date(2026, 2, 17), settings(adjustment)) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        # 29 Ramadan 1447: the month lasts 30 days.
        (date(2026, 3, 17), HijriDate(1447, HijriMonth.RAMADAN, 30)),
        # 1 Shawwal 1447: the 30th of the previous month, unlike the apps.
        (date(2026, 3, 19), HijriDate(1447, HijriMonth.RAMADAN, 30)),
        # 1 Muharram 1448: the 30th of the last month of the previous year.
        (date(2026, 6, 16), HijriDate(1447, HijriMonth.DHU_AL_HIJJAH, 30)),
    ],
)
def test_forced_to_30(day: date, expected: HijriDate) -> None:
    assert hijri.from_gregorian(day, settings(force_30=True)) == expected


@pytest.mark.parametrize(
    ("now", "timezone", "expected"),
    [
        # In Paris it is already 29 March, so the adjusted day is 30 March.
        ("2026-03-28 23:30Z", "Europe/Paris", HijriDate(1447, HijriMonth.SHAWWAL, 12)),
        ("2026-03-28 23:30Z", "UTC", HijriDate(1447, HijriMonth.SHAWWAL, 11)),
        # 24 hours after 00:30 on 25 October would still be 25 October in Paris.
        (
            "2026-10-24 22:30Z",
            ZoneInfo("Europe/Paris"),
            HijriDate(1448, HijriMonth.JUMADA_AL_ULA, 15),
        ),
    ],
)
def test_today(now: str, timezone: str | ZoneInfo, expected: HijriDate) -> None:
    with time_machine.travel(now, tick=False):
        assert hijri.today(settings(1), timezone) == expected


def test_month() -> None:
    assert int(HijriMonth.RAMADAN) == 9
    assert HijriMonth.RAMADAN.label == "Ramadan"
    assert HijriMonth.DHU_AL_QIDAH.label == "Dhu al-Qi'dah"


def test_month_names() -> None:
    """The names of the MAWAQIT apps, which integrations use as states."""
    assert [month.name.lower() for month in HijriMonth] == [
        "muharram",
        "safar",
        "rabi_al_awwal",
        "rabi_al_thani",
        "jumada_al_ula",
        "jumada_al_akhirah",
        "rajab",
        "shaban",
        "ramadan",
        "shawwal",
        "dhu_al_qidah",
        "dhu_al_hijjah",
    ]


def test_date() -> None:
    assert str(HijriDate(1448, HijriMonth.RAMADAN, 9)) == "9 Ramadan 1448"
    assert HijriDate(1447, HijriMonth.DHU_AL_HIJJAH, 30) < HijriDate(
        1448, HijriMonth.MUHARRAM, 1
    )


def test_kuwaiti_invariants_from_1900_to_2200() -> None:
    """Each day follows the previous one, and months last 29 or 30 days."""
    day = date(1900, 1, 1)
    previous = hijri.kuwaiti(day)
    length = 0
    while day < date(2200, 1, 1):
        day += timedelta(days=1)
        current = hijri.kuwaiti(day)
        if current.day == 1:
            assert length in (0, 29, 30)
            assert current.month == previous.month % 12 + 1
            assert current.year == previous.year + (current.month == 1)
            length = 1
        else:
            assert current == replace(previous, day=previous.day + 1)
            length += 1 if length else 0
        previous = current


@pytest.mark.parametrize(
    ("adjustment", "expected"),
    [
        (-1, HijriDate(1447, HijriMonth.DHU_AL_HIJJAH, 30)),
        (1, HijriDate(1448, HijriMonth.MUHARRAM, 2)),
    ],
)
def test_adjustment_across_years(adjustment: int, expected: HijriDate) -> None:
    assert hijri.from_gregorian(date(2026, 6, 16), settings(adjustment)) == expected


def test_prayer_times_as_settings() -> None:
    prayer_times = PrayerTimes.model_validate(
        example("mosquesPrayerTimes", "grande-mosquee-de-paris")
    )

    assert hijri.from_gregorian(date(2026, 2, 18), prayer_times) == HijriDate(
        1447, HijriMonth.RAMADAN, 1
    )
