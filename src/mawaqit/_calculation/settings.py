"""What a calculation of the prayer times takes: a position, settings and options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

CalculationMethod = Literal[
    "muslim_world_league",
    "muslims_of_france",
    "angle_15",
    "algeria",
    "morocco",
    "egypt",
    "karachi",
    "umm_al_qura",
    "gulf",
    "moonsighting_committee",
    "north_america",
    "kuwait",
    "qatar",
    "singapore",
    "turkey",
    "tehran",
    "russia",
    "custom",
]
"""A method of calculation: the angles of the sun below the horizon at Fajr and Isha.

Each one is in `CALCULATION_METHODS`, but `custom`, which takes them from the settings.
"""


@dataclass(frozen=True)
class CalculationPosition:
    """A position on Earth, and its time zone.

    Attributes:
        latitude: The latitude, in degrees from -90 to 90.
        longitude: The longitude, in degrees from -180 to 180.
        timezone: The IANA time zone, like `Europe/Paris`. Every time of the result
            is in it.
    """

    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True, kw_only=True)
class CalculationSettings:
    """The settings of a calculation.

    `default_calculation_settings()` gives those of a country, and
    `dataclasses.replace()` changes one of them.

    Attributes:
        method: The method: the angles of the sun at Fajr and Isha.
        madhab: The school of Asr: Asr is when the shadow of an object is its shadow
            at noon plus once its length for `shafi`, or twice for `hanafi`.
        high_latitude_rule: The rule that bounds Fajr and Isha, every day, for the
            high latitudes where the sun does not go as far below the horizon as the
            angles. Fajr is never earlier than sunrise minus a part of the night,
            from sunset to sunrise, and Isha never later than sunset plus that part:
            half the night for `middle_of_the_night`, a seventh for
            `seventh_of_the_night`, and the angle / 60 for `twilight_angle`, like
            18 / 60 for 18°.
        fajr_angle: The angle of the sun below the horizon at Fajr, in degrees, above
            0 and up to 30. Required by the `custom` method, and ignored by the
            others.
        isha_angle: The angle at Isha, like `fajr_angle`.
        adjustments: The minutes added to each time, as whole minutes from -720 to
            720. None by default.
    """

    method: CalculationMethod
    madhab: Literal["shafi", "hanafi"]
    high_latitude_rule: Literal[
        "middle_of_the_night", "seventh_of_the_night", "twilight_angle"
    ]
    fajr_angle: float | None = None
    isha_angle: float | None = None
    adjustments: (
        Mapping[
            Literal["fajr", "shuruq", "dhuhr", "asr", "maghrib", "isha"], int | None
        ]
        | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class CalculationOptions:
    """The options of `calculate_prayer_times()`.

    Attributes:
        year: The year, from 1000 to 9999. The current year in the time zone by
            default.
        hijri_adjustment: The days added to the date before computing the Hijri date,
            from -2 to 2, like in `client.mosques.hijri_settings()`. It also says
            when Ramadan is, for the Isha of Umm al-Qura.
        jumua_at_dhuhr: Whether Jumu'a is prayed at the time of Dhuhr on Fridays.
            `False` by default: no Jumu'a.
        imsak_minutes_before_fajr: The minutes between Imsak and Fajr, from 0 to 720,
            or `None` without Imsak, the default.
    """

    year: int | None = None
    hijri_adjustment: int = 0
    jumua_at_dhuhr: bool = False
    imsak_minutes_before_fajr: int | None = None
