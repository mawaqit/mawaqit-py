"""The prayer times of a day, the next prayer and the night.

`client.mosques.prayer_times()` returns the times of the whole year as `HH:MM` strings
in the time zone of the mosque, with iqama times either as `HH:MM` or as minutes after
the adhan, like `+10`. These functions read them for a given day, as datetimes, with
the iqama resolved, Imsak, and Jumu'a on Fridays.

Example:
    ```python
    from mawaqit.prayer_times import next_prayer, prayer_day

    times = await client.mosques.prayer_times(uuid)
    today = prayer_day(times)
    print(today.fajr.time, today.fajr.iqama)  # 06:12 2026-10-05 06:30:00+02:00

    upcoming = next_prayer(times)
    print(upcoming.name, upcoming.at)  # asr 2026-10-05 16:46:00+02:00
    ```

Times entered by hand by the mosque can be invalid: such a prayer is `None`, rather
than wrong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from datetime import timezone as dt_timezone
from typing import TYPE_CHECKING, Literal, Protocol
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "Night",
    "Prayer",
    "PrayerDay",
    "PrayerName",
    "PrayerTimesLike",
    "next_prayer",
    "night",
    "prayer_day",
]

PrayerName = Literal[
    "imsak", "fajr", "shuruq", "dhuhr", "asr", "maghrib", "isha", "jumua"
]
"""The name of a prayer, or of Shuruq and Imsak."""

# The order of the prayers in the calendar, after Imsak for the mosques that display it.
_CALENDAR: tuple[PrayerName, ...] = (
    "fajr",
    "shuruq",
    "dhuhr",
    "asr",
    "maghrib",
    "isha",
)
_ROW_LENGTHS = (6, 7)
_WITH_IMSAK = 7
_IQAMA_LENGTH = 5
_FRIDAY = 4
# An iqama this late after its adhan, or an Isha this late after Maghrib, is a mistake
# of the mosque.
_HALF_DAY = timedelta(hours=12)
# ASCII digits only, like the TypeScript library.
_TIME = re.compile(r"([0-9]{1,2}):([0-9]{2})")
_MINUTES = re.compile(r"\+?[0-9]+")
_UTC = dt_timezone.utc


@dataclass(frozen=True)
class Prayer:
    """A prayer of a day.

    Attributes:
        name: The name of the prayer.
        at: Its time, in the time zone of the mosque.
        iqama: Its iqama, in the time zone of the mosque, or `None` without one: for
            Imsak, Shuruq and Jumu'a, and when the mosque publishes no iqama times or
            an invalid one.
    """

    name: PrayerName
    at: datetime
    iqama: datetime | None

    @property
    def time(self) -> str:
        """The time, as `HH:MM` in the time zone of the mosque."""
        return self.at.strftime("%H:%M")


@dataclass(frozen=True)
class PrayerDay:
    """The prayers of a day.

    A prayer is `None` when the mosque has no valid time for it.

    Attributes:
        date: The day.
        imsak: Imsak: from the calendar of the mosques that display it, or
            `imsak_nb_min_before_fajr` minutes before Fajr. `None` for the other
            mosques.
        fajr: Fajr, or Sabah for the mosques that display Imsak.
        shuruq: Shuruq.
        dhuhr: Dhuhr.
        asr: Asr.
        maghrib: Maghrib.
        isha: Isha.
        jumua: On Fridays, the Jumu'a prayers in order. Empty the other days.
    """

    date: date
    imsak: Prayer | None
    fajr: Prayer | None
    shuruq: Prayer | None
    dhuhr: Prayer | None
    asr: Prayer | None
    maghrib: Prayer | None
    isha: Prayer | None
    jumua: tuple[Prayer, ...]


@dataclass(frozen=True)
class Night:
    """The night between Maghrib and the next Fajr, as the Sunnah divides it.

    Attributes:
        start: Maghrib.
        first_third_end: The end of the first third.
        middle: The middle of the night.
        last_third_start: The start of the last third.
        end: Fajr of the next day.
    """

    start: datetime
    first_third_end: datetime
    middle: datetime
    last_third_start: datetime
    end: datetime


class PrayerTimesLike(Protocol):
    """The fields of `PrayerTimes` these functions read."""

    @property
    def timezone(self) -> str:
        """IANA time zone of the mosque."""
        ...

    @property
    def calendar(self) -> Sequence[dict[str, list[str]]]:
        """Prayer times of the year, one item per month."""
        ...

    @property
    def iqama_calendar(self) -> Sequence[dict[str, list[str]]]:
        """Iqama times of the year, one item per month."""
        ...

    @property
    def iqama_enabled(self) -> bool:
        """Whether the mosque publishes iqama times."""
        ...

    @property
    def jumua(self) -> str | None:
        """Time of the first Jumu'a prayer."""
        ...

    @property
    def jumua_2(self) -> str | None:
        """Time of the second Jumu'a prayer."""
        ...

    @property
    def jumua_3(self) -> str | None:
        """Time of the third Jumu'a prayer."""
        ...

    @property
    def jumua_as_duhr(self) -> bool:
        """Whether Jumu'a is prayed at the time of Dhuhr."""
        ...

    @property
    def imsak_nb_min_before_fajr(self) -> int | None:
        """Number of minutes between Imsak and Fajr."""
        ...


def prayer_day(
    prayer_times: PrayerTimesLike,
    day: date | None = None,
    *,
    timezone: tzinfo | None = None,
) -> PrayerDay | None:
    """Return the prayers of a day.

    Args:
        prayer_times: The prayer times of the mosque, from
            `client.mosques.prayer_times()`.
        day: The day. Today in the time zone of the mosque by default.
        timezone: The time zone of the mosque, to avoid loading it from its
            `timezone`.

    Returns:
        The prayers of the day, or `None` when the calendar of the mosque has no valid
        row for it.

    Raises:
        ZoneInfoNotFoundError: The time zone of the mosque is unknown.
    """
    tz = timezone or ZoneInfo(prayer_times.timezone)
    return _day(prayer_times, day or datetime.now(tz).date(), tz)


def next_prayer(
    prayer_times: PrayerTimesLike,
    now: datetime | None = None,
    *,
    shuruq: bool = False,
    jumua: bool = True,
    iqama: bool = False,
    timezone: tzinfo | None = None,
) -> Prayer | None:
    """Return the next prayer: Fajr, Dhuhr, Asr, Maghrib or Isha, or Jumu'a on Fridays.

    After Isha, this is the Fajr of the next day. An Isha after midnight, in summer
    far from the equator, is still the next prayer until its time.

    Args:
        prayer_times: The prayer times of the mosque, from
            `client.mosques.prayer_times()`.
        now: The time to search from. Now by default.
        shuruq: Whether Shuruq counts as a prayer.
        jumua: Whether Jumu'a replaces Dhuhr on Fridays, when the mosque has one.
        iqama: Whether to search the next iqama rather than the next adhan: between
            the adhan and the iqama, the prayer is still the next one.
        timezone: The time zone of the mosque, to avoid loading it from its
            `timezone`.

    Returns:
        The next prayer, or `None` when the calendar of the mosque has no valid time
        around `now`.

    Raises:
        ValueError: `now` has no time zone.
        ZoneInfoNotFoundError: The time zone of the mosque is unknown.
    """
    tz = timezone or ZoneInfo(prayer_times.timezone)
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        msg = "now must have a time zone."
        raise ValueError(msg)
    today = now.astimezone(tz).date()
    found: tuple[float, Prayer] | None = None
    # Yesterday for an Isha after midnight.
    for offset in (-1, 0, 1, 2):
        day = _day(prayer_times, today + timedelta(days=offset), tz)
        if day is None:
            continue
        on_jumua = jumua and bool(day.jumua)
        prayers = [
            day.fajr,
            day.shuruq if shuruq else None,
            None if on_jumua else day.dhuhr,
            *(day.jumua if on_jumua else ()),
            day.asr,
            day.maghrib,
            day.isha,
        ]
        for prayer in prayers:
            if prayer is None:
                continue
            at = ((prayer.iqama or prayer.at) if iqama else prayer.at).timestamp()
            if at > now.timestamp() and (found is None or at < found[0]):
                found = (at, prayer)
    return found[1] if found else None


def night(
    prayer_times: PrayerTimesLike,
    day: date | None = None,
    *,
    timezone: tzinfo | None = None,
) -> Night | None:
    """Return the night that starts at the Maghrib of a day, and its thirds.

    Args:
        prayer_times: The prayer times of the mosque, from
            `client.mosques.prayer_times()`.
        day: The day of the Maghrib. Today in the time zone of the mosque by default.
        timezone: The time zone of the mosque, to avoid loading it from its
            `timezone`.

    Returns:
        The night, or `None` without a valid Maghrib that day and Fajr the next day.

    Raises:
        ZoneInfoNotFoundError: The time zone of the mosque is unknown.
    """
    tz = timezone or ZoneInfo(prayer_times.timezone)
    day = day or datetime.now(tz).date()
    tonight = _day(prayer_times, day, tz)
    tomorrow = _day(prayer_times, day + timedelta(days=1), tz)
    maghrib = tonight and tonight.maghrib
    fajr = tomorrow and tomorrow.fajr
    if not maghrib or not fajr or fajr.at.timestamp() <= maghrib.at.timestamp():
        return None
    start = maghrib.at.astimezone(_UTC)
    length = fajr.at.astimezone(_UTC) - start

    # In UTC: in wall-clock times, a change of daylight saving time would shift them.
    def at(fraction: float) -> datetime:
        return (start + length * fraction).astimezone(tz)

    return Night(
        start=maghrib.at,
        first_third_end=at(1 / 3),
        middle=at(1 / 2),
        last_third_start=at(2 / 3),
        end=fajr.at,
    )


def _day(prayer_times: PrayerTimesLike, day: date, tz: tzinfo) -> PrayerDay | None:
    row = _row(prayer_times.calendar, day)
    if row is None or len(row) not in _ROW_LENGTHS:
        return None
    # Mosques that display Imsak have it first, then Sabah as Fajr.
    imsak_time, times = (row[0], row[1:]) if len(row) == _WITH_IMSAK else (None, row)
    iqama_row = (
        _row(prayer_times.iqama_calendar, day) if prayer_times.iqama_enabled else None
    )
    iqamas = iqama_row if iqama_row and len(iqama_row) == _IQAMA_LENGTH else None

    prayers: dict[PrayerName, Prayer | None] = {}
    last: Prayer | None = None
    for i, name in enumerate(_CALENDAR):
        iqama = None if iqamas is None or name == "shuruq" else iqamas[max(i - 1, 0)]
        after = last if name == "isha" else None
        prayers[name] = _prayer(name, times[i], iqama, day, tz, after=after)
        last = prayers[name] or last

    fajr = prayers["fajr"]
    imsak = _prayer("imsak", imsak_time, None, day, tz)
    minutes_before_fajr = prayer_times.imsak_nb_min_before_fajr or 0
    if imsak is None and fajr and imsak_time is None and minutes_before_fajr > 0:
        imsak = Prayer("imsak", _add(fajr.at, -minutes_before_fajr, tz), None)

    jumua: tuple[Prayer, ...] = ()
    if day.weekday() == _FRIDAY:
        dhuhr = prayers["dhuhr"]
        if prayer_times.jumua_as_duhr:
            first = dhuhr.time if dhuhr else None
        else:
            first = prayer_times.jumua
        jumua = tuple(
            prayer
            for value in (first, prayer_times.jumua_2, prayer_times.jumua_3)
            if (prayer := _prayer("jumua", value, None, day, tz))
        )

    return PrayerDay(
        date=day,
        imsak=imsak,
        fajr=fajr,
        shuruq=prayers["shuruq"],
        dhuhr=prayers["dhuhr"],
        asr=prayers["asr"],
        maghrib=prayers["maghrib"],
        isha=prayers["isha"],
        jumua=jumua,
    )


def _row(calendar: Sequence[dict[str, list[str]]], day: date) -> list[str] | None:
    if day.month > len(calendar):
        return None
    return calendar[day.month - 1].get(str(day.day))


def _prayer(
    name: PrayerName,
    value: str | None,
    iqama: str | None,
    day: date,
    tz: tzinfo,
    *,
    after: Prayer | None = None,
) -> Prayer | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    at = _zoned(day, parsed, tz)
    # An Isha earlier than Maghrib is after midnight, in summer far from the equator.
    # Not any other prayer: a mistake of the mosque, like 16:30 for Fajr, would move the
    # whole day.
    next_day = _zoned(day + timedelta(days=1), parsed, tz)
    if (
        after
        and at.timestamp() < after.at.timestamp()
        and next_day.timestamp() - after.at.timestamp() < _HALF_DAY.total_seconds()
    ):
        day += timedelta(days=1)
        at = next_day
    return Prayer(name, at, _iqama(at, iqama, day, tz) if iqama else None)


def _iqama(adhan: datetime, value: str, day: date, tz: tzinfo) -> datetime | None:
    """Return the iqama of an adhan: `+N` minutes after it, or an `HH:MM` time."""
    value = value.strip()
    if _MINUTES.fullmatch(value):
        at = _add(adhan, int(value), tz)
    else:
        parsed = _parse_time(value)
        if parsed is None:
            return None
        at = _zoned(day, parsed, tz)
        # Like the iqama of an Isha just before midnight.
        if at.timestamp() < adhan.timestamp():
            at = _zoned(day + timedelta(days=1), parsed, tz)
    delay = at.timestamp() - adhan.timestamp()
    return at if delay < _HALF_DAY.total_seconds() else None


def _parse_time(value: str | None) -> time | None:
    """Return an `HH:MM` time, or `None` when it is not one."""
    match = _TIME.fullmatch((value or "").strip())
    if not match:
        return None
    try:
        return time(int(match[1]), int(match[2]))
    except ValueError:
        return None


def _zoned(day: date, at: time, tz: tzinfo) -> datetime:
    """Return a time of a day, normalized when the clocks skip it."""
    return datetime.combine(day, at, tz).astimezone(_UTC).astimezone(tz)


def _add(at: datetime, minutes: int, tz: tzinfo) -> datetime:
    # In UTC: Python adds to aware datetimes in wall-clock time.
    return (at.astimezone(_UTC) + timedelta(minutes=minutes)).astimezone(tz)
