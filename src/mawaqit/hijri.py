"""The Hijri date of a mosque, computed like the MAWAQIT apps and mosque screens.

MAWAQIT computes the Hijri date on the device: the Kuwaiti algorithm, an
arithmetic Islamic calendar, on today's date shifted by the `hijri_adjustment`
of the mosque, with the day replaced by 30 when `hijri_date_force_to_30` is
set. The API only returns these two settings, with
`client.mosques.hijri_settings()`.

Example:
    ```python
    settings = await client.mosques.hijri_settings(uuid)
    today = hijri.today(settings, "Europe/Paris")
    if today.month is HijriMonth.RAMADAN:
        ...
    ```

Only today's date is reliable: mosques change their settings day by day,
after the moon sighting, so a date computed in advance can change.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, tzinfo
from enum import IntEnum
from typing import Protocol
from zoneinfo import ZoneInfo

__all__ = [
    "HijriDate",
    "HijriMonth",
    "HijriSettingsLike",
    "from_gregorian",
    "kuwaiti",
    "today",
]

# Julian Day Number of date.min, and of 16 July 622, the first day of the calendar.
_JULIAN_DAY_OF_ORDINAL_0 = 1721425
_EPOCH = 1948084
# A 30-year cycle lasts 10631 days.
_CYCLE_DAYS = 10631
_YEAR_DAYS = _CYCLE_DAYS / 30
_SHIFT = 8.01 / 60


class HijriMonth(IntEnum):
    """A month of the Hijri calendar."""

    MUHARRAM = 1
    SAFAR = 2
    RABI_AL_AWWAL = 3
    RABI_AL_THANI = 4
    JUMADA_AL_ULA = 5
    JUMADA_AL_AKHIRA = 6
    RAJAB = 7
    SHABAN = 8
    RAMADAN = 9
    SHAWWAL = 10
    DHU_AL_QADA = 11
    DHU_AL_HIJJA = 12

    @property
    def label(self) -> str:
        """The English name of the month, like `Rabi' al-Awwal`."""
        return _LABELS[self]


_LABELS = {
    HijriMonth.MUHARRAM: "Muharram",
    HijriMonth.SAFAR: "Safar",
    HijriMonth.RABI_AL_AWWAL: "Rabi' al-Awwal",
    HijriMonth.RABI_AL_THANI: "Rabi' al-Thani",
    HijriMonth.JUMADA_AL_ULA: "Jumada al-Ula",
    HijriMonth.JUMADA_AL_AKHIRA: "Jumada al-Akhira",
    HijriMonth.RAJAB: "Rajab",
    HijriMonth.SHABAN: "Sha'ban",
    HijriMonth.RAMADAN: "Ramadan",
    HijriMonth.SHAWWAL: "Shawwal",
    HijriMonth.DHU_AL_QADA: "Dhu al-Qa'da",
    HijriMonth.DHU_AL_HIJJA: "Dhu al-Hijja",
}


@dataclass(frozen=True, order=True)
class HijriDate:
    """A date of the Hijri calendar.

    Attributes:
        year: The year, like 1448.
        month: The month.
        day: The day of the month, from 1 to 30.
    """

    year: int
    month: HijriMonth
    day: int

    def __str__(self) -> str:
        """Return the date like `9 Ramadan 1448`."""
        return f"{self.day} {self.month.label} {self.year}"


class HijriSettingsLike(Protocol):
    """The Hijri settings of a mosque, like those of `HijriSettings`."""

    @property
    def hijri_adjustment(self) -> int:
        """Number of days added to the date before computing the Hijri date."""
        ...

    @property
    def hijri_date_force_to_30(self) -> bool:
        """Whether the day of the Hijri date is replaced by 30."""
        ...


def kuwaiti(day: date) -> HijriDate:
    """Return the Hijri date of a Gregorian day with the Kuwaiti algorithm.

    This is the plain algorithm, without the settings of a mosque: prefer
    `from_gregorian()`.

    Args:
        day: The Gregorian day.

    Returns:
        Its Hijri date.
    """
    days = day.toordinal() + _JULIAN_DAY_OF_ORDINAL_0 - _EPOCH
    cycle, days = divmod(days, _CYCLE_DAYS)
    year = math.floor((days - _SHIFT) / _YEAR_DAYS)
    days -= math.floor(year * _YEAR_DAYS + _SHIFT)
    month = min(math.floor((days + 28.5001) / 29.5), 12)
    return HijriDate(
        year=30 * cycle + year,
        month=HijriMonth(month),
        day=days - math.floor(29.5001 * month - 29),
    )


def from_gregorian(day: date, settings: HijriSettingsLike | None = None) -> HijriDate:
    """Return the Hijri date of a mosque on a Gregorian day.

    Two cases differ from the MAWAQIT apps, which have bugs there:

    - The adjustment is added in calendar days, where the apps add 24 hours
      and are a day off for an hour around daylight saving time changes.
    - When the day is forced to 30 on the first day of a month, the date is the
      30th of the previous month, where the apps show the 30th of the new one.

    Args:
        day: The Gregorian day.
        settings: The Hijri settings of the mosque, from
            `client.mosques.hijri_settings()`. Without them, the plain Kuwaiti
            algorithm is used.

    Returns:
        The Hijri date shown by the mosque that day.
    """
    if settings is None:
        return kuwaiti(day)
    hijri = kuwaiti(day + timedelta(days=settings.hijri_adjustment))
    if not settings.hijri_date_force_to_30:
        return hijri
    if hijri.day != 1:
        return replace(hijri, day=30)
    if hijri.month is HijriMonth.MUHARRAM:
        return HijriDate(hijri.year - 1, HijriMonth.DHU_AL_HIJJA, 30)
    return HijriDate(hijri.year, HijriMonth(hijri.month - 1), 30)


def today(settings: HijriSettingsLike, timezone: str | tzinfo) -> HijriDate:
    """Return today's Hijri date of a mosque.

    The date changes at midnight in the time zone of the mosque, like on its
    screens, and not at Maghrib.

    Args:
        settings: The Hijri settings of the mosque, from
            `client.mosques.hijri_settings()`.
        timezone: The time zone of the mosque, like `"Europe/Paris"`: the
            `timezone` of `client.mosques.prayer_times()`.

    Returns:
        Today's Hijri date of the mosque.
    """
    tz = ZoneInfo(timezone) if isinstance(timezone, str) else timezone
    return from_gregorian(datetime.now(tz).date(), settings)
