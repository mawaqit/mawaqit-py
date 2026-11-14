"""Prayer times calculated from a position, like mawaqit-js."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import time_machine

from mawaqit.hijri import HijriMonth, from_gregorian, today
from mawaqit.prayer_times import (
    CALCULATION_METHODS,
    CalculatedPrayerTimes,
    CalculationMethod,
    CalculationMethodAngles,
    CalculationOptions,
    CalculationPosition,
    CalculationSettings,
    calculate_prayer_times,
    calculation_method_name,
    default_calculation_method,
    default_calculation_settings,
    next_prayer,
    night,
    prayer_day,
)

DATA = Path(__file__).parent / "data" / "calculation"
PARIS = CalculationPosition(48.8566, 2.3522, "Europe/Paris")
LILLE = CalculationPosition(50.6292, 3.0573, "Europe/Paris")
OSLO = CalculationPosition(59.9139, 10.7522, "Europe/Oslo")
TROMSO = CalculationPosition(69.6496, 18.956, "Europe/Oslo")
MAKKAH = CalculationPosition(21.4225, 39.8262, "Asia/Riyadh")
MWL = CalculationSettings(
    method="muslim_world_league", madhab="shafi", high_latitude_rule="twilight_angle"
)
YEAR_2026 = CalculationOptions(year=2026)


def row(times: CalculatedPrayerTimes, day: str) -> list[str] | None:
    """The row of a day, from an ISO date."""
    parsed = date.fromisoformat(day)
    return times.calendar[parsed.month - 1].get(str(parsed.day))


def days(times: CalculatedPrayerTimes, year: int) -> list[tuple[date, list[str]]]:
    """Every day of a calculated year, and its row."""
    return [
        (date(year, month, int(day)), times_of_day)
        for month, rows in enumerate(times.calendar, start=1)
        for day, times_of_day in rows.items()
    ]


def minutes(time: str) -> int:
    return int(time[:2]) * 60 + int(time[3:])


def minutes_between(start: str, end: str) -> int:
    return (minutes(end) - minutes(start)) % 1440


def utc(instant: datetime | None) -> str:
    assert instant is not None
    return instant.astimezone(timezone.utc).isoformat()


def from_js(
    position: dict[str, Any], settings: dict[str, Any], options: dict[str, Any]
) -> tuple[CalculationPosition, CalculationSettings, CalculationOptions]:
    """The arguments of a calculation, from those of mawaqit-js."""
    return (
        CalculationPosition(
            position["latitude"], position["longitude"], position["timeZone"]
        ),
        CalculationSettings(
            method=settings["method"],
            madhab=settings["madhab"],
            high_latitude_rule=settings["highLatitudeRule"],
            fajr_angle=settings.get("fajrAngle"),
            isha_angle=settings.get("ishaAngle"),
            adjustments=settings.get("adjustments"),
        ),
        CalculationOptions(
            year=options.get("year"),
            hijri_adjustment=options.get("hijriAdjustment", 0),
        ),
    )


class TestSameAsMawaqitJs:
    """The minutes of `calculatePrayerTimes()` of mawaqit-js, which adhan-js checks.

    `tests/data/calculation/mawaqit-js/` has thousands of days of mawaqit-js: random
    positions from pole to pole, every method, madhab and rule, adjustments, Ramadan,
    and every day of a year at a few places. See the README there.
    """

    FIXTURE: dict[str, Any] = json.loads(
        (DATA / "mawaqit-js" / "mawaqit-js.json").read_text(encoding="utf-8")
    )

    def test_every_day(self) -> None:
        mismatches: list[tuple[str, str, list[str], list[str] | None]] = []
        compared = 0
        for case in self.FIXTURE["cases"]:
            position, settings, options = from_js(
                case["position"], case["settings"], case["options"]
            )
            times = calculate_prayer_times(position, settings, options)
            for day, expected in case["days"].items():
                compared += 1
                actual = row(times, day)
                if actual != expected:
                    mismatches.append(
                        (json.dumps(case["position"]), day, expected, actual)
                    )

        assert self.FIXTURE["version"] == "1.5.0"
        assert compared == self.FIXTURE["rows"] > 5000
        assert mismatches[:3] == []

    def test_method_names(self) -> None:
        for language, names in self.FIXTURE["methodNames"].items():
            for method, name in names.items():
                assert calculation_method_name(method, language) == name

    def test_default_settings(self) -> None:
        for country, settings in self.FIXTURE["defaultSettings"].items():
            _, expected, _ = from_js(
                {"latitude": 0, "longitude": 0, "timeZone": "UTC"}, settings, {}
            )
            assert default_calculation_settings(country) == expected

    def test_when_daylight_saving_time_starts_between_fajr_and_isha(self) -> None:
        times = calculate_prayer_times(TROMSO, MWL, YEAR_2026)

        # 01:57 in winter time, 22:33 in summer time.
        assert row(times, "2026-03-29") == [
            "01:57",
            "06:03",
            "12:50",
            "16:00",
            "19:38",
            "22:33",
        ]


class TestCalculatePrayerTimes:
    def test_fajr_and_isha_in_paris_on_21_december_by_angle(self) -> None:
        def fajr_and_isha(method: CalculationMethod) -> tuple[str, str]:
            settings = replace(MWL, method=method)
            day = row(calculate_prayer_times(PARIS, settings, YEAR_2026), "2026-12-21")
            assert day is not None
            return day[0], day[5]

        assert fajr_and_isha("muslims_of_france") == ("07:23", "18:14")
        assert fajr_and_isha("angle_15") == ("07:04", "18:33")
        assert fajr_and_isha("muslim_world_league") == ("06:45", "18:46")

    def test_the_high_latitude_rules_in_lille_on_21_june(self) -> None:
        def times(rule: Any) -> list[str]:
            settings = replace(MWL, high_latitude_rule=rule)
            return (
                row(calculate_prayer_times(LILLE, settings, YEAR_2026), "2026-06-21")
                or []
            )

        twilight = times("twilight_angle")
        assert twilight == ["03:20", "05:35", "13:51", "18:11", "22:04", "00:12"]
        assert times("middle_of_the_night") == ["01:49", *twilight[1:5], "01:50"]
        assert times("seventh_of_the_night")[0] == "04:31"

    def test_dhuhr_is_the_same_minute_for_every_method(self) -> None:
        dhuhrs = {
            (
                row(
                    calculate_prayer_times(
                        PARIS, replace(MWL, method=method), YEAR_2026
                    ),
                    "2026-06-21",
                )
                or []
            )[2]
            for method in CALCULATION_METHODS
        }

        assert dhuhrs == {"13:53"}

    def test_the_adjustments_in_minutes_then_the_rounding(self) -> None:
        adjustments: dict[Any, int] = {
            "fajr": -5,
            "shuruq": 2,
            "dhuhr": 3,
            "asr": 1,
            "maghrib": 4,
            "isha": -2,
        }
        plain = row(calculate_prayer_times(PARIS, MWL, YEAR_2026), "2026-12-21") or []
        settings = replace(MWL, adjustments=adjustments)
        adjusted = row(calculate_prayer_times(PARIS, settings, YEAR_2026), "2026-12-21")

        assert [
            minutes(time) - minutes(plain[i]) for i, time in enumerate(adjusted or [])
        ] == list(adjustments.values())

    def test_whole_floats_as_integers(self) -> None:
        settings = replace(MWL, adjustments={"fajr": -5.0})  # type: ignore[dict-item]
        options = CalculationOptions(year=2026.0)  # type: ignore[arg-type]

        times = calculate_prayer_times(PARIS, settings, options)

        assert row(times, "2026-12-21") == [
            "06:40",
            *(row(calculate_prayer_times(PARIS, MWL, YEAR_2026), "2026-12-21") or [])[
                1:
            ],
        ]


class TestIshaAfterMaghrib:
    UMM_AL_QURA = replace(MWL, method="umm_al_qura")

    @staticmethod
    def isha(times: CalculatedPrayerTimes, day: str) -> int:
        maghrib_and_isha = row(times, day) or []
        return minutes_between(maghrib_and_isha[4], maghrib_and_isha[5])

    def test_90_minutes_for_umm_al_qura_and_120_during_ramadan(self) -> None:
        times = calculate_prayer_times(MAKKAH, self.UMM_AL_QURA, YEAR_2026)
        gaps = [
            (
                from_gregorian(day).month is HijriMonth.RAMADAN,
                self.isha(times, str(day)),
            )
            for day, _ in days(times, 2026)
        ]

        assert set(gaps) == {(False, 90), (True, 120)}
        # 1 Ramadan 1447 is 17 February 2026.
        assert len([gap for gap in gaps if gap[0]]) == 30
        assert self.isha(times, "2026-02-17") == 120
        assert self.isha(times, "2026-02-16") == 90

    def test_ramadan_follows_hijri_adjustment(self) -> None:
        options = CalculationOptions(year=2026, hijri_adjustment=1)
        times = calculate_prayer_times(MAKKAH, self.UMM_AL_QURA, options)

        assert self.isha(times, "2026-02-16") == 120

    def test_from_maghrib_before_its_adjustment(self) -> None:
        settings = replace(MWL, method="qatar", adjustments={"maghrib": 5})
        times = calculate_prayer_times(MAKKAH, settings, YEAR_2026)

        # 90 minutes after sunset, so 85 after the adjusted Maghrib, in Ramadan too for
        # Qatar.
        assert self.isha(times, "2026-01-10") == 85
        assert self.isha(times, "2026-02-20") == 85


class TestPolarRegions:
    @pytest.mark.parametrize(
        ("when", "day"),
        [
            ("the sun does not set", "2026-06-21"),
            ("the sun does not rise", "2026-12-21"),
        ],
    )
    def test_the_times_of_the_same_longitude_at_65(self, when: str, day: str) -> None:
        times = calculate_prayer_times(TROMSO, MWL, YEAR_2026)
        at_65 = calculate_prayer_times(replace(TROMSO, latitude=65), MWL, YEAR_2026)

        assert row(times, day) == row(at_65, day), when

    def test_in_the_south_too(self) -> None:
        position = CalculationPosition(-77.85, 166.67, "Antarctica/McMurdo")
        times = calculate_prayer_times(position, MWL, YEAR_2026)
        at_65 = calculate_prayer_times(replace(position, latitude=-65), MWL, YEAR_2026)

        assert row(times, "2026-06-21") == row(at_65, "2026-06-21")
        assert row(times, "2026-06-21") == [
            "07:26",
            "11:08",
            "12:56",
            "13:09",
            "14:42",
            "18:15",
        ]

    def test_at_the_poles(self) -> None:
        position = CalculationPosition(90, 0, "UTC")
        times = calculate_prayer_times(position, MWL, YEAR_2026)

        assert len(row(times, "2026-06-21") or []) == 6


def test_the_day_of_the_noon_of_the_time_zone_near_the_date_line() -> None:
    # UTC+14 at 157° W: the noon of 1 January in Kiritimati is the one of 31 December
    # in UTC.
    position = CalculationPosition(1.87, -157.4, "Pacific/Kiritimati")
    times = calculate_prayer_times(position, MWL, YEAR_2026)

    assert row(times, "2026-01-01") == [
        "05:18",
        "06:32",
        "12:34",
        "15:58",
        "18:33",
        "19:44",
    ]
    day = prayer_day(times, date(2026, 1, 1))
    assert day is not None
    assert day.dhuhr is not None
    assert utc(day.dhuhr.at) == "2025-12-31T22:34:00+00:00"


class TestTheYear:
    @time_machine.travel(
        datetime(2027, 12, 31, 23, 30, tzinfo=timezone.utc), tick=False
    )
    def test_the_current_year_in_the_time_zone_by_default(self) -> None:
        # Already 2028 in Paris.
        times = calculate_prayer_times(PARIS, MWL)

        assert len(times.calendar[1]["29"]) == 6

    @pytest.mark.parametrize(
        ("year", "lengths"),
        [
            (2026, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]),
            (2028, [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]),
        ],
    )
    def test_every_day(self, year: int, lengths: list[int]) -> None:
        times = calculate_prayer_times(PARIS, MWL, CalculationOptions(year=year))

        assert [len(month) for month in times.calendar] == lengths
        assert list(times.calendar[0])[:3] == ["1", "2", "3"]
        for _, times_of_day in days(times, year):
            assert all(len(time) == 5 and time[2] == ":" for time in times_of_day)

    @pytest.mark.parametrize(
        ("day", "expected"),
        [
            ("2026-01-01", ["06:35", "09:18", "12:22", "13:17", "15:23", "17:58"]),
            ("2028-02-29", ["04:59", "07:17", "12:30", "15:00", "17:43", "19:54"]),
            # With the sunrise of the next year.
            ("2026-12-31", ["06:35", "09:19", "12:21", "13:16", "15:21", "17:57"]),
        ],
    )
    def test_a_day(self, day: str, expected: list[str]) -> None:
        options = CalculationOptions(year=int(day[:4]))

        assert row(calculate_prayer_times(OSLO, MWL, options), day) == expected

    def test_the_last_day_python_dates_have(self) -> None:
        # The next day, 10000-01-01, sets the length of the night.
        position = CalculationPosition(1.87, 179.9, "Etc/GMT-12")
        times = calculate_prayer_times(position, MWL, CalculationOptions(year=9999))

        assert len(times.calendar[11]["31"]) == 6


class TestTheOtherFields:
    def test_by_default(self) -> None:
        times = calculate_prayer_times(PARIS, MWL, YEAR_2026)

        assert replace(times, calendar=[]) == CalculatedPrayerTimes(
            timezone="Europe/Paris",
            calendar=[],
            iqama_calendar=[],
            iqama_enabled=False,
            jumua=None,
            jumua_2=None,
            jumua_3=None,
            jumua_as_duhr=False,
            imsak_nb_min_before_fajr=None,
            hijri_adjustment=0,
            hijri_date_force_to_30=False,
        )

    # A Monday: the next Friday is 9 October.
    @time_machine.travel(datetime(2026, 10, 5, 10, tzinfo=timezone.utc), tick=False)
    def test_jumua_at_the_time_of_dhuhr_the_next_friday(self) -> None:
        times = calculate_prayer_times(
            PARIS, MWL, CalculationOptions(jumua_at_dhuhr=True)
        )

        assert times.jumua_as_duhr is True
        assert times.jumua == (row(times, "2026-10-09") or [])[2]
        friday = prayer_day(times, date(2026, 10, 9))
        assert friday is not None
        assert [prayer.time for prayer in friday.jumua] == [times.jumua]
        next_friday = prayer_day(times, date(2026, 10, 16))
        assert next_friday is not None
        assert [prayer.time for prayer in next_friday.jumua] == [
            (row(times, "2026-10-16") or [])[2]
        ]

    @time_machine.travel(datetime(2026, 10, 5, 10, tzinfo=timezone.utc), tick=False)
    def test_jumua_of_another_year_its_first_friday(self) -> None:
        options = CalculationOptions(year=2027, jumua_at_dhuhr=True)
        times = calculate_prayer_times(PARIS, MWL, options)

        # 1 January 2027 is a Friday.
        assert times.jumua == (row(times, "2027-01-01") or [])[2]

    def test_imsak(self) -> None:
        options = CalculationOptions(year=2026, imsak_minutes_before_fajr=10)
        times = calculate_prayer_times(PARIS, MWL, options)
        day = prayer_day(times, date(2026, 12, 21))

        assert times.imsak_nb_min_before_fajr == 10
        assert day is not None
        assert day.imsak is not None
        assert day.fajr is not None
        assert (day.imsak.time, day.fajr.time) == ("06:35", "06:45")

    @time_machine.travel(datetime(2026, 2, 16, 12, tzinfo=timezone.utc), tick=False)
    def test_the_hijri_date(self) -> None:
        times = calculate_prayer_times(
            MAKKAH, MWL, CalculationOptions(hijri_adjustment=1)
        )

        assert times.hijri_adjustment == 1
        assert str(today(times, times.timezone)) == "1 Ramadan 1447"


class TestReadByTheHelpersOfAMosque:
    TIMES = calculate_prayer_times(LILLE, MWL, YEAR_2026)

    def test_an_isha_after_midnight(self) -> None:
        day = prayer_day(self.TIMES, date(2026, 6, 21))
        assert day is not None
        assert day.isha is not None
        night_of_day = night(self.TIMES, date(2026, 6, 21))
        assert night_of_day is not None

        assert utc(day.isha.at) == "2026-06-21T22:12:00+00:00"
        assert utc(night_of_day.start) == "2026-06-21T20:04:00+00:00"
        # 23:30 in Lille.
        now = datetime(2026, 6, 21, 21, 30, tzinfo=timezone.utc)
        upcoming = next_prayer(self.TIMES, now)
        assert upcoming is not None
        assert upcoming.name == "isha"
        later = next_prayer(self.TIMES, now + timedelta(hours=1))
        assert later is not None
        assert later.name == "fajr"

    @pytest.mark.parametrize(
        ("day", "sunrise"),
        [
            (date(2026, 3, 28), "2026-03-28T05:33:00+00:00"),
            (date(2026, 3, 29), "2026-03-29T05:31:00+00:00"),
            (date(2026, 10, 25), "2026-10-25T06:27:00+00:00"),
        ],
    )
    def test_daylight_saving_time(self, day: date, sunrise: str) -> None:
        prayers = prayer_day(self.TIMES, day)
        assert prayers is not None
        assert prayers.shuruq is not None

        assert utc(prayers.shuruq.at) == sunrise

    def test_no_iqama(self) -> None:
        day = prayer_day(self.TIMES, date(2026, 6, 21))
        assert day is not None
        assert day.fajr is not None
        noon = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
        upcoming = next_prayer(self.TIMES, noon, iqama=True)

        assert day.fajr.iqama is None
        assert upcoming is not None
        assert upcoming.name == "asr"


CUSTOM = replace(MWL, method="custom", fajr_angle=15, isha_angle=15)


class TestInvalidInput:
    @pytest.mark.parametrize(
        ("field", "position", "settings", "options"),
        [
            ("position.latitude", {"latitude": 90.5}, {}, {}),
            ("position.latitude", {"latitude": float("nan")}, {}, {}),
            ("position.latitude", {"latitude": "48.8"}, {}, {}),
            ("position.latitude", {"latitude": True}, {}, {}),
            ("position.longitude", {"longitude": -181}, {}, {}),
            ("position.timezone", {"timezone": "Paris"}, {}, {}),
            ("position.timezone", {"timezone": "../Paris"}, {}, {}),
            ("position.timezone", {"timezone": None}, {}, {}),
            ("settings.method", {}, {"method": "mwl"}, {}),
            ("settings.fajr_angle", {}, {"method": "custom", "fajr_angle": None}, {}),
            ("settings.isha_angle", {}, {"method": "custom", "isha_angle": 0}, {}),
            ("settings.isha_angle", {}, {"method": "custom", "isha_angle": 31}, {}),
            ("settings.madhab", {}, {"madhab": "maliki"}, {}),
            ("settings.high_latitude_rule", {}, {"high_latitude_rule": "none"}, {}),
            ("settings.adjustments.sunrise", {}, {"adjustments": {"sunrise": 1}}, {}),
            ("settings.adjustments.isha", {}, {"adjustments": {"isha": 1.5}}, {}),
            ("settings.adjustments.fajr", {}, {"adjustments": {"fajr": 721}}, {}),
            ("options.year", {}, {}, {"year": 2026.5}),
            ("options.year", {}, {}, {"year": 999}),
            ("options.year", {}, {}, {"year": float("inf")}),
            ("options.hijri_adjustment", {}, {}, {"hijri_adjustment": -3}),
            ("options.jumua_at_dhuhr", {}, {}, {"jumua_at_dhuhr": "yes"}),
            (
                "options.imsak_minutes_before_fajr",
                {},
                {},
                {"imsak_minutes_before_fajr": -10},
            ),
        ],
    )
    def test_the_field(
        self,
        field: str,
        position: dict[str, Any],
        settings: dict[str, Any],
        options: dict[str, Any],
    ) -> None:
        base = CUSTOM if settings.get("method") == "custom" else MWL
        with pytest.raises(ValueError, match=rf"^Invalid {field}: "):
            calculate_prayer_times(
                replace(PARIS, **position),
                replace(base, **settings),
                CalculationOptions(**{"year": 2026, **options}),
            )

    def test_the_message(self) -> None:
        with pytest.raises(
            ValueError,
            match=r"^Invalid position\.latitude: 91\. Use a number from -90 to 90\.$",
        ):
            calculate_prayer_times(replace(PARIS, latitude=91), MWL)
        with pytest.raises(
            ValueError,
            match=(
                r"^Invalid settings\.fajr_angle: None\. The custom method needs an "
                r"angle above 0 and up to 30 degrees\.$"
            ),
        ):
            calculate_prayer_times(PARIS, replace(MWL, method="custom"))
        with pytest.raises(
            ValueError,
            match=(
                r"^Invalid position\.timezone: 'Paris'\. "
                r'Use an IANA time zone, like "Europe/Paris"\.$'
            ),
        ):
            calculate_prayer_times(replace(PARIS, timezone="Paris"), MWL)

    def test_the_angles_of_another_method_than_custom_are_ignored(self) -> None:
        settings = replace(MWL, fajr_angle=99, adjustments={"asr": None})

        assert calculate_prayer_times(PARIS, settings, YEAR_2026) == (
            calculate_prayer_times(PARIS, MWL, YEAR_2026)
        )


class TestMethods:
    def test_their_angles(self) -> None:
        assert len(CALCULATION_METHODS) == 17
        assert CALCULATION_METHODS["angle_15"] == CalculationMethodAngles(
            fajr_angle=15, isha_angle=15, isha_minutes_after_maghrib=None
        )
        assert CALCULATION_METHODS["umm_al_qura"] == CalculationMethodAngles(
            fajr_angle=18.5, isha_angle=None, isha_minutes_after_maghrib=90
        )

    @pytest.mark.parametrize(
        ("country", "method"),
        [
            ("FR", "angle_15"),
            ("fr", "angle_15"),
            ("DZ", "algeria"),
            ("MA", "morocco"),
            ("SA", "umm_al_qura"),
            ("EG", "egypt"),
            ("SN", "egypt"),
            ("GB", "north_america"),
            ("PK", "karachi"),
            ("MY", "karachi"),
            ("ID", "singapore"),
            ("AE", "gulf"),
            ("KW", "kuwait"),
            ("QA", "qatar"),
            ("TR", "turkey"),
            ("IR", "tehran"),
            ("RU", "russia"),
            ("NO", "muslim_world_league"),
            ("", "muslim_world_league"),
            (None, "muslim_world_league"),
        ],
    )
    def test_the_method_of(self, country: str | None, method: str) -> None:
        assert default_calculation_method(country) == method

    @pytest.mark.parametrize(
        ("country", "method", "madhab"),
        [
            ("FR", "angle_15", "shafi"),
            ("pk", "karachi", "hanafi"),
            ("IN", "karachi", "hanafi"),
            ("BD", "karachi", "hanafi"),
            ("AF", "karachi", "hanafi"),
            ("MY", "karachi", "shafi"),
            (None, "muslim_world_league", "shafi"),
        ],
    )
    def test_the_settings_of(
        self, country: str | None, method: Any, madhab: Any
    ) -> None:
        assert default_calculation_settings(country) == CalculationSettings(
            method=method, madhab=madhab, high_latitude_rule="twilight_angle"
        )
        assert default_calculation_settings() == MWL

    @pytest.mark.parametrize(
        ("method", "language", "name"),
        [
            ("muslim_world_league", "en", "Muslim World League"),
            ("muslim_world_league", "fr", "Ligue du monde musulman"),
            ("angle_15", "fr-FR", "Fajr et Isha à 15°"),
            ("angle_15", "en", "Fajr and Isha at 15°"),
            ("custom", "ar", "زوايا مخصصة"),
            ("gulf", "de", "Golfregion"),
            ("moonsighting_committee", "tr_TR", "Ay Gözlem Komitesi"),
            ("muslims_of_france", "es", "Muslim of France (ex UOIF)"),
        ],
    )
    def test_the_name_of(
        self, method: CalculationMethod, language: str, name: str
    ) -> None:
        assert calculation_method_name(method, language) == name

    def test_every_method_has_a_name_in_every_language(self) -> None:
        methods: list[CalculationMethod] = [*CALCULATION_METHODS, "custom"]
        for language in ("ar", "de", "en", "fr", "tr"):
            for method in methods:
                assert calculation_method_name(method, language)
        assert (
            calculation_method_name("karachi")
            == "University of Islamic Sciences, Karachi"
        )


REFERENCES = sorted(DATA.glob("*.json"))


# The times of the MAWAQIT app, recorded with the same settings: see the README there.
@pytest.mark.parametrize(
    "path",
    [pytest.param(path, id=path.name) for path in REFERENCES]
    or [pytest.param(None, marks=pytest.mark.skip(reason="No reference times yet"))],
)
def test_the_times_of_the_mawaqit_app(path: Path) -> None:
    reference = json.loads(path.read_text(encoding="utf-8"))
    years: dict[int, CalculatedPrayerTimes] = {}
    for day, recorded in reference["days"].items():
        year = int(day[:4])
        if year not in years:
            position, settings, options = from_js(
                reference["position"],
                reference["settings"],
                {**reference.get("options", {}), "year": year},
            )
            years[year] = calculate_prayer_times(position, settings, options)
        # Dhuhr one minute later than recorded, as mawaqit/mawaqit-js#16 decided.
        fajr, shuruq, dhuhr, *rest = recorded
        later = datetime.strptime(dhuhr, "%H:%M") + timedelta(minutes=1)
        assert row(years[year], day) == [fajr, shuruq, f"{later:%H:%M}", *rest], day
