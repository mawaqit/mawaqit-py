"""Prayer times calculated from a position, in the shape of `PrayerTimes`."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal, NoReturn
from zoneinfo import ZoneInfo

from mawaqit.hijri import HijriMonth, _kuwaiti_of_ordinal

from .astronomy import (
    DAY,
    MINUTE,
    DayParameters,
    civil_from_days,
    day_times,
    rounded_minute,
)
from .methods import CALCULATION_METHODS
from .settings import CalculationOptions

if TYPE_CHECKING:
    from .settings import CalculationPosition, CalculationSettings


@dataclass(frozen=True)
class CalculatedPrayerTimes:
    """A year of calculated prayer times, in the shape of `PrayerTimes`.

    `prayer_day()`, `next_prayer()`, `night()`, and `hijri.today()` read it like the
    times of a mosque. It holds no position and no name.

    Attributes:
        timezone: The IANA time zone of the position. Every time is in it.
        calendar: The times of the year, one item per month from January to December.
            Each month maps its days, from `"1"`, to the Fajr, Shuruq, Dhuhr, Asr,
            Maghrib and Isha times, as `HH:MM`.
        iqama_calendar: Empty: a calculation has no iqama.
        iqama_enabled: `False`.
        jumua: With `jumua_at_dhuhr`, the Dhuhr time of the next Friday, or of the
            first Friday of another year, as `HH:MM`. `None` otherwise.
        jumua_2: `None`.
        jumua_3: `None`.
        jumua_as_duhr: `jumua_at_dhuhr`: whether Jumu'a is prayed at the time of
            Dhuhr on Fridays.
        imsak_nb_min_before_fajr: `imsak_minutes_before_fajr`.
        hijri_adjustment: `hijri_adjustment`.
        hijri_date_force_to_30: `False`.
    """

    timezone: str
    calendar: list[dict[str, list[str]]]
    iqama_calendar: list[dict[str, list[str]]]
    iqama_enabled: Literal[False]
    jumua: str | None
    jumua_2: None
    jumua_3: None
    jumua_as_duhr: bool
    imsak_nb_min_before_fajr: int | None
    hijri_adjustment: int
    hijri_date_force_to_30: Literal[False]


_ADJUSTED = ("fajr", "shuruq", "dhuhr", "asr", "maghrib", "isha")
# Dhuhr is a minute after the transit, once the whole disc of the sun has passed the
# meridian.
_DHUHR_MINUTES = 1
_UMM_AL_QURA_RAMADAN_ISHA_MINUTES = 120
_MAX_ANGLE = 30
_MAX_MINUTES = 720
_MIN_YEAR = 1000
_MAX_YEAR = 9999
_MAX_HIJRI_ADJUSTMENT = 2
# 1 January 1970 was a Thursday.
_FRIDAY = 1
_UNIX_ORDINAL = date(1970, 1, 1).toordinal()
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_LAST_YEAR = (date(_MAX_YEAR, 1, 1).toordinal() - _UNIX_ORDINAL) * DAY
# The days of 400 years, after which the calendar and the rules of a time zone repeat.
_CYCLE = 146097 * DAY
_MINUTES_PER_DAY = 1440


def calculate_prayer_times(
    position: CalculationPosition,
    settings: CalculationSettings,
    options: CalculationOptions | None = None,
) -> CalculatedPrayerTimes:
    """Calculate the prayer times of a year at a position.

    This calls no API: it works offline. The astronomy is the one of
    [adhan-js](https://github.com/batoulapps/adhan-js), after Jean Meeus'
    *Astronomical Algorithms*, and gives the same minutes as `calculatePrayerTimes()`
    of mawaqit-js:

    - Fajr and Isha are when the sun is at the angles of the method below the
      horizon, bounded by the high-latitude rule. Isha is 90 minutes after Maghrib
      for Umm al-Qura and Qatar, and 120 minutes during Ramadan for Umm al-Qura,
      counted from Maghrib before its adjustment. Ramadan is the one of the Hijri
      dates of `hijri.from_gregorian()`, with `hijri_adjustment`.
    - Dhuhr is one minute after the solar transit, for every method.
    - Asr is when the shadow of an object reaches the length of the madhab.
    - Shuruq and Maghrib are sunrise and sunset.
    - The adjustments are added, then every time is rounded to the nearest minute,
      from 30 seconds up.
    - When the sun does not rise or set, near the poles, the day is the one of the
      latitude clamped to ±65°, where it does.

    The times of a day are those of its solar noon in the time zone, through daylight
    saving time changes. An Isha after midnight stays in the row of its day, like in
    the calendar of a mosque.

    Example:
        ```python
        times = calculate_prayer_times(
            CalculationPosition(48.85, 2.35, "Europe/Paris"),
            default_calculation_settings("FR"),
        )
        prayer_day(times).fajr.time  # "06:42" on 26 November
        ```

    Args:
        position: The position, and its time zone.
        settings: The settings, like `default_calculation_settings("FR")`.
        options: The year, and the fields of the result that the calculation does
            not set.

    Returns:
        The times of the year, in the shape of `client.mosques.prayer_times()`.

    Raises:
        ValueError: A field is invalid, like a latitude out of range, an unknown time
            zone or method, the custom method without its angles, or an adjustment
            that is not a whole number of minutes. The message names the field.
    """
    latitude, longitude, tz = _check_position(position)
    parameters, adjustments = _check_settings(settings)
    if options is None:
        options = CalculationOptions()
    hijri_adjustment = _check_integer(
        "options.hijri_adjustment",
        options.hijri_adjustment,
        -_MAX_HIJRI_ADJUSTMENT,
        _MAX_HIJRI_ADJUSTMENT,
    )
    jumua_at_dhuhr = _check_boolean("options.jumua_at_dhuhr", options.jumua_at_dhuhr)
    imsak = options.imsak_minutes_before_fajr
    if imsak is not None:
        imsak = _check_integer(
            "options.imsak_minutes_before_fajr", imsak, 0, _MAX_MINUTES
        )
    year = options.year
    if year is None:
        year = datetime.now(tz).year
    year = _check_integer("options.year", year, _MIN_YEAR, _MAX_YEAR)

    ramadan_parameters = replace(
        parameters, isha_interval=_UMM_AL_QURA_RAMADAN_ISHA_MINUTES
    )
    umm_al_qura = settings.method == "umm_al_qura"

    def row(day: int) -> list[str]:
        ramadan = (
            umm_al_qura
            and _kuwaiti_of_ordinal(day + _UNIX_ORDINAL + hijri_adjustment).month
            is HijriMonth.RAMADAN
        )
        day_parameters = ramadan_parameters if ramadan else parameters
        times = day_times(day, latitude, longitude, day_parameters)
        # Near the date line, the noon of a day in its time zone is the noon of
        # another day in UTC, like in Kiribati.
        shift = day - _day_in(times.transit, tz)
        if shift != 0:
            times = day_times(day + shift, latitude, longitude, day_parameters)
        instants = [
            rounded_minute(times.fajr + adjustments["fajr"] * MINUTE),
            rounded_minute(times.sunrise + adjustments["shuruq"] * MINUTE),
            rounded_minute(
                times.transit + (_DHUHR_MINUTES + adjustments["dhuhr"]) * MINUTE
            ),
            rounded_minute(times.asr + adjustments["asr"] * MINUTE),
            rounded_minute(times.sunset + adjustments["maghrib"] * MINUTE),
            rounded_minute(times.isha + adjustments["isha"] * MINUTE),
        ]
        # One offset for the day, unless it changes, like mawaqit-js.
        offset = _offset_at(min(instants), tz)
        if offset != _offset_at(max(instants), tz):
            return [_format(instant, _offset_at(instant, tz)) for instant in instants]
        return [_format(instant, offset) for instant in instants]

    first = date(year, 1, 1).toordinal() - _UNIX_ORDINAL
    end = date(year, 12, 31).toordinal() - _UNIX_ORDINAL + 1
    calendar: list[dict[str, list[str]]] = [{} for _ in range(12)]
    for day in range(first, end):
        _, month, day_of_month = civil_from_days(day)
        calendar[month - 1][str(day_of_month)] = row(day)

    jumua: str | None = None
    if jumua_at_dhuhr:
        today = datetime.now(tz).date().toordinal() - _UNIX_ORDINAL
        friday = today if first <= today < end else first
        while friday % 7 != _FRIDAY:
            friday += 1
        jumua = row(friday)[2]

    return CalculatedPrayerTimes(
        timezone=position.timezone,
        calendar=calendar,
        iqama_calendar=[],
        iqama_enabled=False,
        jumua=jumua,
        jumua_2=None,
        jumua_3=None,
        jumua_as_duhr=jumua_at_dhuhr,
        imsak_nb_min_before_fajr=imsak,
        hijri_adjustment=hijri_adjustment,
        hijri_date_force_to_30=False,
    )


def _offset_at(instant: float, tz: ZoneInfo) -> int:
    """Return the offset of a time zone from UTC at an instant, in milliseconds."""
    # Python dates end in 9999, where JavaScript dates go on.
    if instant >= _LAST_YEAR:
        instant -= _CYCLE
    utc = _EPOCH + timedelta(milliseconds=instant)
    offset = utc.astimezone(tz).utcoffset() or timedelta()
    return offset // timedelta(milliseconds=1)


def _day_in(instant: float, tz: ZoneInfo) -> int:
    """Return the day it is at an instant in a time zone."""
    return math.floor((instant + _offset_at(instant, tz)) / DAY)


def _format(instant: float, offset: int) -> str:
    """Return the `HH:MM` time of an instant, at an offset in milliseconds."""
    minutes = math.floor((instant + offset) / MINUTE) % _MINUTES_PER_DAY
    return f"{minutes // 60:02}:{minutes % 60:02}"


def _check_position(position: CalculationPosition) -> tuple[float, float, ZoneInfo]:
    latitude = _check_number("position.latitude", position.latitude, -90, 90)
    longitude = _check_number("position.longitude", position.longitude, -180, 180)
    tz = _zone(position.timezone)
    if tz is None:
        _invalid(
            "position.timezone",
            position.timezone,
            'Use an IANA time zone, like "Europe/Paris".',
        )
    return latitude, longitude, tz


def _check_settings(
    settings: CalculationSettings,
) -> tuple[DayParameters, dict[str, int]]:
    method = settings.method
    if method != "custom" and method not in CALCULATION_METHODS:
        _invalid(
            "settings.method",
            method,
            'Use "custom" or a method of CALCULATION_METHODS.',
        )
    isha_interval = 0
    if method == "custom":
        fajr_angle = _check_angle("settings.fajr_angle", settings.fajr_angle)
        isha_angle = _check_angle("settings.isha_angle", settings.isha_angle)
    else:
        angles = CALCULATION_METHODS[method]
        fajr_angle = angles.fajr_angle
        isha_angle = angles.isha_angle or 0
        isha_interval = angles.isha_minutes_after_maghrib or 0
    madhab: object = settings.madhab
    if madhab not in ("shafi", "hanafi"):
        _invalid("settings.madhab", madhab, 'Use "shafi" or "hanafi".')
    portions = {
        "middle_of_the_night": (1 / 2, 1 / 2),
        "seventh_of_the_night": (1 / 7, 1 / 7),
        "twilight_angle": (fajr_angle / 60, isha_angle / 60),
    }
    rule = settings.high_latitude_rule
    if rule not in portions:
        _invalid(
            "settings.high_latitude_rule",
            rule,
            'Use "middle_of_the_night", "seventh_of_the_night" or "twilight_angle".',
        )

    adjustments: dict[str, int] = dict.fromkeys(_ADJUSTED, 0)
    for name, minutes in (settings.adjustments or {}).items():
        field = f"settings.adjustments.{name}"
        if name not in adjustments:
            _invalid(field, minutes, f"Adjust {', '.join(_ADJUSTED)}.")
        if minutes is not None:
            adjustments[name] = _check_integer(
                field, minutes, -_MAX_MINUTES, _MAX_MINUTES
            )

    fajr_portion, isha_portion = portions[rule]
    parameters = DayParameters(
        fajr_angle=fajr_angle,
        isha_angle=isha_angle,
        isha_interval=isha_interval,
        shadow_length=2 if madhab == "hanafi" else 1,
        fajr_night_portion=fajr_portion,
        isha_night_portion=isha_portion,
    )
    return parameters, adjustments


def _zone(name: object) -> ZoneInfo | None:
    if not isinstance(name, str):
        return None
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        return None


def _number(value: object) -> float | None:
    """Return the value when it is a number, and not a boolean."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _check_angle(field: str, value: object) -> float:
    angle = _number(value)
    if angle is None or not 0 < angle <= _MAX_ANGLE:
        _invalid(
            field,
            value,
            f"The custom method needs an angle above 0 and up to {_MAX_ANGLE} degrees.",
        )
    return angle


def _check_number(field: str, value: object, min_: float, max_: float) -> float:
    number = _number(value)
    if number is None or not min_ <= number <= max_:
        _invalid(field, value, f"Use a number from {min_} to {max_}.")
    return number


def _check_integer(field: str, value: object, min_: int, max_: int) -> int:
    number = _number(value)
    if number is None or number % 1 != 0 or not min_ <= number <= max_:
        _invalid(field, value, f"Use a whole number from {min_} to {max_}.")
    return int(number)


def _check_boolean(field: str, value: object) -> bool:
    if not isinstance(value, bool):
        _invalid(field, value, "Use a boolean.")
    return value


def _invalid(field: str, value: object, help_: str) -> NoReturn:
    msg = f"Invalid {field}: {value!r}. {help_}"
    raise ValueError(msg)
