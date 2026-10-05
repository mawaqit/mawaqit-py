"""The prayer times of a day, the next prayer and the night, like mawaqit-js."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
import time_machine

from mawaqit.prayer_times import next_prayer, night, prayer_day
from mawaqit.types import PrayerTimes

from .conftest import example

if TYPE_CHECKING:
    from mawaqit.prayer_times import Prayer

PARIS_TZ = ZoneInfo("Europe/Paris")
# Real times, of the Grande Mosquée de Paris.
PARIS = PrayerTimes.model_validate(
    example("mosquesPrayerTimes", "grande-mosquee-de-paris")
)
DEFAULT_ROW = ["06:00", "07:30", "13:00", "16:00", "19:00", "20:30"]
DEFAULT_IQAMA = ["+10", "+5", "+5", "+5", "+5"]


def months(fill: list[str], by_day: dict[str, list[str]]) -> list[dict[str, list[str]]]:
    """Return a calendar with these rows, by `MM-DD`, and `fill` every other day."""
    return [
        {str(day): by_day.get(f"{month:02}-{day:02}", fill) for day in range(1, 32)}
        for month in range(1, 13)
    ]


@dataclass(frozen=True)
class Times:
    """Prayer times with the fields the functions read."""

    rows: dict[str, list[str]] = field(default_factory=dict)
    iqama: dict[str, list[str]] = field(default_factory=dict)
    timezone: str = "Europe/Paris"
    iqama_enabled: bool = True
    jumua: str | None = "13:30"
    jumua_2: str | None = None
    jumua_3: str | None = None
    jumua_as_duhr: bool = False
    imsak_nb_min_before_fajr: int | None = 0

    @property
    def calendar(self) -> list[dict[str, list[str]]]:
        return months(DEFAULT_ROW, self.rows)

    @property
    def iqama_calendar(self) -> list[dict[str, list[str]]]:
        return months(DEFAULT_IQAMA, self.iqama)


def times(prayer: Prayer | None) -> tuple[str, str, str, str | None]:
    """The name, time, instant and iqama of a prayer, in UTC, to compare at once."""
    assert prayer is not None
    iqama = prayer.iqama
    return (
        prayer.name,
        prayer.time,
        prayer.at.astimezone(timezone.utc).isoformat(),
        iqama.astimezone(timezone.utc).isoformat() if iqama else None,
    )


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class TestPrayerDay:
    def test_a_day_of_a_real_calendar(self) -> None:
        day = prayer_day(PARIS, date(2026, 1, 1))

        assert day is not None
        assert day.date == date(2026, 1, 1)
        assert times(day.fajr) == (
            "fajr",
            "07:05",
            "2026-01-01T06:05:00+00:00",
            "2026-01-01T06:13:00+00:00",
        )
        assert times(day.shuruq) == (
            "shuruq",
            "08:44",
            "2026-01-01T07:44:00+00:00",
            None,
        )
        assert day.asr
        assert day.asr.iqama
        assert day.asr.iqama.strftime("%H:%M") == "14:56"
        assert day.maghrib
        assert day.maghrib.iqama == day.maghrib.at
        assert day.fajr
        assert day.fajr.at.tzinfo == PARIS_TZ
        assert day.imsak is None
        # A Thursday.
        assert day.jumua == ()

    @time_machine.travel("2026-01-01 23:30+00:00", tick=False)
    def test_today_by_default_in_the_time_zone_of_the_mosque(self) -> None:
        day = prayer_day(PARIS)

        # Already 2 January in Paris.
        assert day
        assert day.date == date(2026, 1, 2)

    def test_a_time_zone_given(self) -> None:
        day = prayer_day(PARIS, date(2026, 1, 1), timezone=timezone.utc)

        assert day
        assert day.fajr
        assert day.fajr.at.isoformat() == "2026-01-01T07:05:00+00:00"

    def test_summer_time(self) -> None:
        winter = prayer_day(PARIS, date(2026, 3, 28))
        summer = prayer_day(PARIS, date(2026, 3, 29))

        assert winter
        assert times(winter.fajr)[2] == "2026-03-28T04:03:00+00:00"
        assert summer
        assert times(summer.fajr)[2] == "2026-03-29T04:01:00+00:00"

    @pytest.mark.parametrize(
        ("day", "time", "at"),
        [
            # Skipped: 02:30 does not exist, so it is 03:30 of summer time.
            (date(2026, 3, 29), "03:30", "2026-03-29T01:30:00+00:00"),
            # Repeated: the first 02:30, in summer time.
            (date(2026, 10, 25), "02:30", "2026-10-25T00:30:00+00:00"),
        ],
    )
    def test_times_of_the_change_of_daylight_saving_time(
        self, day: date, time: str, at: str
    ) -> None:
        row = ["02:30", "07:30", "13:00", "16:00", "19:00", "20:30"]
        result = prayer_day(Times(rows={f"{day:%m-%d}": row}), day)

        assert result
        assert times(result.fajr)[1:3] == (time, at)

    def test_jumua_on_fridays(self) -> None:
        day = prayer_day(
            PARIS.model_copy(update={"jumua_3": "15:30"}), date(2026, 1, 2)
        )

        assert day is not None
        assert [times(prayer) for prayer in day.jumua] == [
            ("jumua", "13:50", "2026-01-02T12:50:00+00:00", None),
            ("jumua", "14:30", "2026-01-02T13:30:00+00:00", None),
            ("jumua", "15:30", "2026-01-02T14:30:00+00:00", None),
        ]
        assert day.dhuhr
        assert day.dhuhr.time == "13:00"

    def test_jumua_at_the_time_of_dhuhr(self) -> None:
        data = PARIS.model_copy(update={"jumua_as_duhr": True, "jumua": "12:00"})
        day = prayer_day(data, date(2026, 1, 2))

        assert day
        assert [prayer.time for prayer in day.jumua] == ["13:00", "14:30"]

    def test_jumua_at_the_time_of_an_invalid_dhuhr(self) -> None:
        row = ["06:00", "07:30", "--", "16:00", "19:00", "20:30"]
        data = Times(rows={"01-02": row}, jumua_as_duhr=True, jumua_2="14:00")
        day = prayer_day(data, date(2026, 1, 2))

        assert day
        assert [prayer.time for prayer in day.jumua] == ["14:00"]

    def test_without_jumua(self) -> None:
        data = PARIS.model_copy(update={"jumua": None, "jumua_2": "nonsense"})
        day = prayer_day(data, date(2026, 1, 2))

        assert day
        assert day.jumua == ()

    def test_imsak_from_the_calendar_with_sabah_as_fajr(self) -> None:
        row = ["05:20", "05:30", "07:30", "13:00", "16:00", "19:00", "20:30"]
        day = prayer_day(Times(rows={"03-01": row}), date(2026, 3, 1))

        assert day is not None
        assert times(day.imsak) == ("imsak", "05:20", "2026-03-01T04:20:00+00:00", None)
        assert times(day.fajr) == (
            "fajr",
            "05:30",
            "2026-03-01T04:30:00+00:00",
            "2026-03-01T04:40:00+00:00",
        )
        assert day.shuruq
        assert day.shuruq.time == "07:30"
        assert day.isha
        assert day.isha.time == "20:30"

    def test_imsak_minutes_before_fajr(self) -> None:
        day = prayer_day(Times(imsak_nb_min_before_fajr=10), date(2026, 3, 1))

        assert day
        assert times(day.imsak) == (
            "imsak",
            "05:50",
            "2026-03-01T04:50:00+00:00",
            None,
        )

    @pytest.mark.parametrize("minutes", [0, None])
    def test_no_imsak(self, minutes: int | None) -> None:
        day = prayer_day(Times(imsak_nb_min_before_fajr=minutes), date(2026, 3, 1))

        assert day
        assert day.imsak is None

    @pytest.mark.parametrize(
        ("iqama", "time", "at"),
        [
            ("+15", "23:45", "2026-06-20T21:45:00+00:00"),
            ("15", "23:45", "2026-06-20T21:45:00+00:00"),
            ("23:40", "23:40", "2026-06-20T21:40:00+00:00"),
            # After midnight, the next day.
            ("+45", "00:15", "2026-06-20T22:15:00+00:00"),
            ("00:10", "00:10", "2026-06-20T22:10:00+00:00"),
            (" +0 ", "23:30", "2026-06-20T21:30:00+00:00"),
        ],
    )
    def test_iqama_after_an_isha_at_23_30(self, iqama: str, time: str, at: str) -> None:
        isha = self.isha("23:30", iqama)

        assert isha
        assert isha.iqama
        assert isha.iqama.strftime("%H:%M") == time
        assert isha.iqama.astimezone(timezone.utc).isoformat() == at

    @pytest.mark.parametrize(
        "iqama",
        [
            "abc",
            "",
            "25:00",
            "-5",
            # In Arabic-Indic digits, which int() would read.
            "\u0660\u0665:\u0660\u0660",
            # 23 hours after the adhan: a mistake of the mosque.
            "23:00",
            "+720",
        ],
    )
    def test_invalid_iqama(self, iqama: str) -> None:
        isha = self.isha("23:30", iqama)

        assert isha
        assert isha.iqama is None

    @staticmethod
    def isha(time: str, iqama: str) -> Prayer | None:
        data = Times(
            rows={"06-20": ["03:50", "05:45", "13:55", "18:00", "21:55", time]},
            iqama={"06-20": ["+10", "+5", "+5", "+5", iqama]},
        )
        day = prayer_day(data, date(2026, 6, 20))
        return day.isha if day else None

    def test_when_the_mosque_publishes_no_iqama(self) -> None:
        data = PARIS.model_copy(update={"iqama_enabled": False})
        day = prayer_day(data, date(2026, 1, 1))

        assert day
        assert day.fajr
        assert day.fajr.iqama is None

    def test_without_a_valid_iqama_row(self) -> None:
        day = prayer_day(Times(iqama={"01-01": ["+5"]}), date(2026, 1, 1))

        assert day
        assert day.fajr
        assert day.fajr.iqama is None

    def test_an_isha_after_midnight_is_the_next_day(self) -> None:
        data = Times(
            rows={"06-20": ["03:00", "05:00", "13:55", "18:00", "22:30", "00:30"]},
            iqama={"06-20": ["+10", "+5", "+5", "+5", "00:40"]},
        )
        day = prayer_day(data, date(2026, 6, 20))

        assert day
        assert times(day.isha) == (
            "isha",
            "00:30",
            "2026-06-20T22:30:00+00:00",
            "2026-06-20T22:40:00+00:00",
        )

    @pytest.mark.parametrize("time", ["--", "", "24:00", "7h05", "\u0667:\u0660\u0665"])
    def test_an_invalid_time_entered_by_hand_is_none(self, time: str) -> None:
        row = ["06:00", "07:30", "13:00", time, "19:00", "20:30"]
        day = prayer_day(Times(rows={"01-01": row}), date(2026, 1, 1))

        assert day
        assert day.asr is None
        assert day.maghrib
        assert day.maghrib.time == "19:00"

    def test_times_without_a_leading_zero(self) -> None:
        row = ["6:00", "7:30", "13:00", "16:00", "19:00", "20:30"]
        day = prayer_day(Times(rows={"01-01": row}), date(2026, 1, 1))

        assert day
        assert day.fajr
        assert day.fajr.time == "06:00"

    def test_a_day_without_a_valid_row(self) -> None:
        short = PARIS.model_copy(update={"calendar": PARIS.calendar[:1]})

        assert prayer_day(short, date(2026, 3, 1)) is None
        assert prayer_day(Times(rows={"01-01": ["06:00"]}), date(2026, 1, 1)) is None

    def test_29_february_which_the_calendar_always_has(self) -> None:
        day = prayer_day(PARIS, date(2028, 2, 29))

        assert day
        assert day.fajr
        assert day.fajr.time == PARIS.calendar[1]["29"][0]

    def test_unknown_time_zone(self) -> None:
        with pytest.raises(ZoneInfoNotFoundError):
            prayer_day(replace(Times(), timezone="Europe/Atlantis"), date(2026, 1, 1))


class TestNextPrayer:
    @staticmethod
    def next(
        now: str,
        data: Times | PrayerTimes = PARIS,
        *,
        shuruq: bool = False,
        jumua: bool = True,
        iqama: bool = False,
    ) -> tuple[str, str, str, str | None]:
        prayer = next_prayer(data, utc(now), shuruq=shuruq, jumua=jumua, iqama=iqama)
        return times(prayer)

    def test_the_next_adhan(self) -> None:
        assert self.next("2026-01-01T10:00")[:2] == ("dhuhr", "12:59")

    def test_at_the_time_of_the_adhan_the_following_prayer(self) -> None:
        assert self.next("2026-01-01T11:59:00")[0] == "asr"
        assert self.next("2026-01-01T11:58:59")[0] == "dhuhr"

    def test_after_isha_the_fajr_of_the_next_day(self) -> None:
        assert self.next("2026-01-01T20:00")[::2] == (
            "fajr",
            "2026-01-02T06:05:00+00:00",
        )

    def test_after_the_last_isha_of_the_year_the_first_fajr(self) -> None:
        assert self.next("2026-12-31T22:00")[::2] == (
            "fajr",
            "2027-01-01T06:05:00+00:00",
        )

    @time_machine.travel("2026-01-01 10:00+00:00", tick=False)
    def test_now_by_default(self) -> None:
        prayer = next_prayer(PARIS)

        assert prayer
        assert prayer.name == "dhuhr"

    def test_a_naive_now(self) -> None:
        with pytest.raises(ValueError, match="time zone"):
            next_prayer(PARIS, datetime(2026, 1, 1, 10))

    def test_jumua_on_fridays(self) -> None:
        assert self.next("2026-01-02T10:00")[:2] == ("jumua", "13:50")
        assert self.next("2026-01-02T13:00")[:2] == ("jumua", "14:30")
        assert self.next("2026-01-02T13:30")[0] == "asr"
        assert self.next("2026-01-02T10:00", jumua=False)[0] == "dhuhr"

    def test_dhuhr_on_fridays_without_jumua(self) -> None:
        data = PARIS.model_copy(update={"jumua": None, "jumua_2": None})

        assert self.next("2026-01-02T10:00", data)[0] == "dhuhr"

    def test_with_shuruq(self) -> None:
        assert self.next("2026-01-01T07:00")[0] == "dhuhr"
        assert self.next("2026-01-01T07:00", shuruq=True)[0] == "shuruq"

    def test_the_next_iqama(self) -> None:
        no_iqama = PARIS.model_copy(update={"iqama_enabled": False})

        # Between the adhan of Dhuhr, 12:59, and its iqama, 13:07.
        assert self.next("2026-01-01T12:02")[0] == "asr"
        assert self.next("2026-01-01T12:02", iqama=True)[0] == "dhuhr"
        # Without an iqama, the adhan.
        assert self.next("2026-01-01T12:02", no_iqama, iqama=True)[0] == "asr"

    def test_an_isha_after_midnight_is_still_next_after_midnight(self) -> None:
        data = Times(
            rows={"06-20": ["03:00", "05:00", "13:55", "18:00", "22:30", "00:30"]}
        )

        # 00:15 in Paris on 21 June: the Isha of 20 June, at 00:30.
        assert self.next("2026-06-20T22:15", data)[::2] == (
            "isha",
            "2026-06-20T22:30:00+00:00",
        )

    def test_skips_invalid_times_and_missing_days(self) -> None:
        data = Times(
            rows={"01-01": ["06:00", "07:30", "13:00", "--", "19:00", "20:30"]}
        )
        empty = PARIS.model_copy(update={"calendar": []})

        assert self.next("2026-01-01T13:00", data)[0] == "maghrib"
        assert next_prayer(empty, utc("2026-01-01T10:00")) is None


class TestNight:
    def test_its_thirds(self) -> None:
        # Maghrib at 17:08, then Fajr at 07:05 the next day: 13 hours and 57 minutes.
        result = night(PARIS, date(2026, 1, 1))

        assert result is not None
        assert [
            at.astimezone(timezone.utc)
            for at in (
                result.start,
                result.first_third_end,
                result.middle,
                result.last_third_start,
                result.end,
            )
        ] == [
            utc("2026-01-01T16:08"),
            utc("2026-01-01T20:47"),
            utc("2026-01-01T23:06:30"),
            utc("2026-01-02T01:26"),
            utc("2026-01-02T06:05"),
        ]
        assert result.middle.tzinfo == PARIS_TZ

    def test_when_the_clocks_go_forward(self) -> None:
        # Maghrib at 19:18 in winter time, then Fajr at 06:01 in summer time.
        result = night(PARIS, date(2026, 3, 28))

        assert result
        assert result.middle == utc("2026-03-28T23:09:30")

    @time_machine.travel("2026-01-01 12:00+00:00", tick=False)
    def test_tonight_by_default(self) -> None:
        result = night(PARIS)

        assert result
        assert result.start == utc("2026-01-01T16:08")

    def test_without_maghrib_or_the_next_fajr(self) -> None:
        data = Times(
            rows={"01-02": ["--", "07:30", "13:00", "16:00", "19:00", "20:30"]}
        )
        short = PARIS.model_copy(update={"calendar": PARIS.calendar[:1]})

        assert night(data, date(2026, 1, 1)) is None
        assert night(short, date(2026, 1, 31)) is None
