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
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

__all__ = [
    "HijriDate",
    "HijriMonth",
    "HijriSettingsLike",
    "IslamicEvent",
    "UpcomingEvent",
    "from_gregorian",
    "kuwaiti",
    "month_name",
    "today",
    "upcoming_events",
]

# Julian Day Number of date.min, and of 16 July 622, the first day of the calendar.
_JULIAN_DAY_OF_ORDINAL_0 = 1721425
_EPOCH = 1948084
# A 30-year cycle lasts 10631 days.
_CYCLE_DAYS = 10631
_YEAR_DAYS = _CYCLE_DAYS / 30
_SHIFT = 8.01 / 60


class HijriMonth(IntEnum):
    """A month of the Hijri calendar, named like in the MAWAQIT apps."""

    MUHARRAM = 1
    SAFAR = 2
    RABI_AL_AWWAL = 3
    RABI_AL_THANI = 4
    JUMADA_AL_ULA = 5
    JUMADA_AL_AKHIRAH = 6
    RAJAB = 7
    SHABAN = 8
    RAMADAN = 9
    SHAWWAL = 10
    DHU_AL_QIDAH = 11
    DHU_AL_HIJJAH = 12

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
    HijriMonth.JUMADA_AL_AKHIRAH: "Jumada al-Akhirah",
    HijriMonth.RAJAB: "Rajab",
    HijriMonth.SHABAN: "Sha'ban",
    HijriMonth.RAMADAN: "Ramadan",
    HijriMonth.SHAWWAL: "Shawwal",
    HijriMonth.DHU_AL_QIDAH: "Dhu al-Qi'dah",
    HijriMonth.DHU_AL_HIJJAH: "Dhu al-Hijjah",
}

# Arabic as on the mosque screens, the other languages as on the MAWAQIT website.
_MONTH_NAMES = {
    "ar": (
        "محرم",
        "صفر",
        "ربيع الأول",
        "ربيع الثاني",
        "جمادى الأولى",
        "جمادى الثانية",
        "رجب",
        "شعبان",
        "رمضان",
        "شوال",
        "ذو القعدة",
        "ذو الحجة",
    ),
    "de": (
        "Muharram",
        "Safar",
        "Rabīʿ al-awwal",
        "Rabīʿ ath-thānī",
        "Dschumādā l-ūlā",
        "Dschumādā l-āchira",
        "Radschab",
        "Schaʿbān",
        "Ramadan",
        "Schawwāl",
        "Dhū l-qaʿda",
        "Dhū l-ḥiddscha",
    ),
    "fr": (
        "Mouharram",
        "Safar",
        "Rabi al-awal",
        "Rabi al-thani",
        "Joumada al-oula",
        "Joumada al-thania",
        "Rajab",
        "Chaabane",
        "Ramadan",
        "Chawwal",
        "Dhou al-qi'da",
        "Dhou al-hijja",
    ),
    "tr": (
        "Muharrem",
        "Safer",
        "Rebiülevvel",
        "Rebiülahir",
        "Cemaziyelevvel",
        "Cemaziyelahir",
        "Recep",
        "Şaban",
        "Ramazan",
        "Şevval",
        "Zilkade",
        "Zilhicce",
    ),
}


def month_name(month: HijriMonth, language: str = "en") -> str:
    """Return the name of a Hijri month, like `Rabi' al-Awwal`.

    Args:
        month: The month.
        language: A language, like `fr`, or a language tag, like `fr-FR` or
            `fr_FR`. Arabic, English, French, German and Turkish have their
            names, as on the MAWAQIT website; the other languages get the
            English name.

    Returns:
        The name of the month in this language.
    """
    names = _MONTH_NAMES.get(language.replace("_", "-").partition("-")[0].lower())
    return month.label if names is None else names[month - 1]


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

    Three cases differ from the MAWAQIT apps, which have bugs there:

    - The adjustment is added in calendar days, where the apps add 24 hours
      and are a day off for an hour around daylight saving time changes.
    - When the day is forced to 30 on the first day of a month, the date is the
      30th of the previous month, where the apps show the 30th of the new one.
    - An adjustment outside -2 to 2 counts as 0. The API returns -3 for a French
      mosque that has not chosen its adjustment yet, which the apps add as is.

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
    hijri = kuwaiti(day + timedelta(days=_adjustment(settings)))
    if not settings.hijri_date_force_to_30:
        return hijri
    if hijri.day != 1:
        return replace(hijri, day=30)
    if hijri.month is HijriMonth.MUHARRAM:
        return HijriDate(hijri.year - 1, HijriMonth.DHU_AL_HIJJAH, 30)
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
    return from_gregorian(_day_in(timezone), settings)


IslamicEvent = Literal[
    "islamic_new_year", "ashura", "ramadan", "eid_al_fitr", "arafah", "eid_al_adha"
]
"""An event of the Islamic year.

`islamic_new_year` on 1 Muharram, `ashura` on 10 Muharram, `ramadan` on
1 Ramadan, `eid_al_fitr` on 1 Shawwal, `arafah` on 9 Dhu al-Hijjah and
`eid_al_adha` on 10 Dhu al-Hijjah.
"""

_EVENTS: dict[tuple[HijriMonth, int], IslamicEvent] = {
    (HijriMonth.MUHARRAM, 1): "islamic_new_year",
    (HijriMonth.MUHARRAM, 10): "ashura",
    (HijriMonth.RAMADAN, 1): "ramadan",
    (HijriMonth.SHAWWAL, 1): "eid_al_fitr",
    (HijriMonth.DHU_AL_HIJJAH, 9): "arafah",
    (HijriMonth.DHU_AL_HIJJAH, 10): "eid_al_adha",
}


@dataclass(frozen=True)
class UpcomingEvent:
    """The next day of an Islamic event.

    Attributes:
        event: The event.
        date: The Gregorian day.
        hijri_date: The Hijri date of the day.
        days_until: The number of days from today: 0 when the event is today.
    """

    event: IslamicEvent
    date: date
    hijri_date: HijriDate
    days_until: int


def upcoming_events(
    settings: HijriSettingsLike, timezone: str | tzinfo
) -> list[UpcomingEvent]:
    """Return the next day of each Islamic event at a mosque, today included.

    Only an event of today is certain. The days ahead assume that the mosque
    keeps its settings, which it changes after the moon sighting: an event can
    move by a day or two. When today is forced to the 30th where the Kuwaiti
    algorithm starts a month, the month starts tomorrow.

    Args:
        settings: The Hijri settings of the mosque, from
            `client.mosques.hijri_settings()`.
        timezone: The time zone of the mosque, like `"Europe/Paris"`: the
            `timezone` of `client.mosques.prayer_times()`.

    Returns:
        The six events, sorted by date.
    """
    start = _day_in(timezone)
    adjustment = _adjustment(settings)
    if (
        settings.hijri_date_force_to_30
        and kuwaiti(start + timedelta(days=adjustment)).day == 1
    ):
        adjustment -= 1
    upcoming: list[UpcomingEvent] = []
    days_until = 0
    # Each event comes within a Hijri year, before the first one found comes again.
    while len(upcoming) < len(_EVENTS):
        day = start + timedelta(days=days_until)
        hijri_date = (
            from_gregorian(day, settings)
            if days_until == 0
            else kuwaiti(day + timedelta(days=adjustment))
        )
        event = _EVENTS.get((hijri_date.month, hijri_date.day))
        if event is not None:
            upcoming.append(UpcomingEvent(event, day, hijri_date, days_until))
        days_until += 1
    return upcoming


# The adjustments the mosques can choose.
_MAX_ADJUSTMENT = 2


def _adjustment(settings: HijriSettingsLike) -> int:
    adjustment = settings.hijri_adjustment
    return adjustment if abs(adjustment) <= _MAX_ADJUSTMENT else 0


def _day_in(timezone: str | tzinfo) -> date:
    tz = ZoneInfo(timezone) if isinstance(timezone, str) else timezone
    return datetime.now(tz).date()
