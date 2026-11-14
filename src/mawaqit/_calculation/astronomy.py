# The MIT License (MIT)
#
# Copyright (c) 2016 Batoul Apps
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""The position of the sun and the times of a day.

Ported from mawaqit-js, itself ported from adhan-js 4.4.6
(https://github.com/batoulapps/adhan-js), after Jean Meeus' Astronomical Algorithms.
The equations keep the order of operations of adhan-js, and the instants are
milliseconds like JavaScript dates, so the times are the same to the millisecond.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import NamedTuple

MINUTE = 60_000
DAY = 86_400_000

# Where the sun rises and sets every day of the year.
_POLAR_LATITUDE = 65
_HALF_MINUTE = 30


@dataclass(frozen=True)
class DayParameters:
    """What sets the times of a day, besides the position.

    Attributes:
        fajr_angle: The angle of the sun below the horizon at Fajr, in degrees.
        isha_angle: The angle at Isha, in degrees, when `isha_interval` is 0.
        isha_interval: The minutes from sunset to Isha, or 0 for an angle.
        shadow_length: The shadow of an object at Asr, in lengths of the object.
        fajr_night_portion: The part of the night that bounds Fajr before sunrise.
        isha_night_portion: The part of the night that bounds Isha after sunset.
    """

    fajr_angle: float
    isha_angle: float
    isha_interval: float
    shadow_length: int
    fajr_night_portion: float
    isha_night_portion: float


class DayTimes(NamedTuple):
    """The instants of a day, in milliseconds, before the adjustments and rounding."""

    fajr: float
    sunrise: float
    transit: float
    asr: float
    sunset: float
    isha: float


def day_times(
    unix_day: int, latitude: float, longitude: float, parameters: DayParameters
) -> DayTimes:
    """Return the instants of a day, like `new PrayerTimes()` of adhan-js.

    Without its method adjustments, rounding and method-specific rules. When the sun
    does not rise or set, the day is the one of the latitude clamped to ±65°.
    """
    today = unix_day
    tomorrow = unix_day + 1
    solar_time = _solar_time(today, latitude, longitude)
    tomorrow_solar_time = _solar_time(tomorrow, latitude, longitude)
    if (
        math.isnan(solar_time.sunrise)
        or math.isnan(solar_time.sunset)
        or math.isnan(tomorrow_solar_time.sunrise)
    ):
        clamped = max(-_POLAR_LATITUDE, min(_POLAR_LATITUDE, latitude))
        solar_time = _solar_time(today, clamped, longitude)
        tomorrow_solar_time = _solar_time(tomorrow, clamped, longitude)

    transit = _utc_instant(solar_time.transit, today)
    sunrise = _utc_instant(solar_time.sunrise, today)
    sunset = _utc_instant(solar_time.sunset, today)
    asr = _utc_instant(solar_time.afternoon(parameters.shadow_length), today)
    tomorrow_sunrise = _utc_instant(tomorrow_solar_time.sunrise, tomorrow)
    night = (tomorrow_sunrise - sunset) / 1000

    fajr = _utc_instant(
        solar_time.hour_angle(-1 * parameters.fajr_angle, after_transit=False), today
    )
    safe_fajr = _add_seconds(sunrise, -(parameters.fajr_night_portion * night))
    if math.isnan(fajr) or safe_fajr > fajr:
        fajr = safe_fajr

    if parameters.isha_interval > 0:
        isha = _add_seconds(sunset, parameters.isha_interval * 60)
    else:
        isha = _utc_instant(
            solar_time.hour_angle(-1 * parameters.isha_angle, after_transit=True), today
        )
        safe_isha = _add_seconds(sunset, parameters.isha_night_portion * night)
        if math.isnan(isha) or safe_isha < isha:
            isha = safe_isha
    return DayTimes(fajr, sunrise, transit, asr, sunset, isha)


def rounded_minute(instant: float) -> float:
    """Round an instant to the nearest minute, from 30 seconds up, like adhan-js."""
    seconds = math.trunc(instant) // 1000 % 60
    offset = 60 - seconds if seconds >= _HALF_MINUTE else -1 * seconds
    return _add_seconds(instant, offset)


def civil_from_days(unix_day: int) -> tuple[int, int, int]:
    """Return the year, month and day of a day, past `date.max` too."""
    # Howard Hinnant's algorithm, in eras of 400 years.
    z = unix_day + 719468
    era = z // 146097
    day_of_era = z - era * 146097
    year_of_era = (
        day_of_era - day_of_era // 1460 + day_of_era // 36524 - day_of_era // 146096
    ) // 365
    day_of_year = day_of_era - (
        365 * year_of_era + year_of_era // 4 - year_of_era // 100
    )
    shifted_month = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * shifted_month + 2) // 5 + 1
    month = shifted_month + 3 if shifted_month < 10 else shifted_month - 9  # noqa: PLR2004
    return year_of_era + era * 400 + (month <= 2), month, day  # noqa: PLR2004


def _add_seconds(instant: float, seconds: float) -> float:
    # Like a JavaScript date: whole milliseconds, truncated toward zero.
    total = instant + seconds * 1000
    return float(math.trunc(total)) if math.isfinite(total) else math.nan


def _utc_instant(num: float, unix_day: int) -> float:
    """The instant of a time in hours of a day, in UTC, truncated to the second."""
    if math.isnan(num):
        return math.nan
    hours = math.floor(num)
    minutes = math.floor((num - hours) * 60)
    seconds = math.floor((num - (hours + minutes / 60)) * 60 * 60)
    return float(unix_day * DAY + ((hours * 60 + minutes) * 60 + seconds) * 1000)


# The tomorrow of a day is the today of the next one.
@lru_cache(maxsize=8)
def _solar_time(unix_day: int, latitude: float, longitude: float) -> _SolarTime:
    return _SolarTime(unix_day, latitude, longitude)


class _SolarTime:
    """The transit, sunrise and sunset of a day, in hours of the day in UTC."""

    __slots__ = (
        "_approx_transit",
        "_latitude",
        "_longitude",
        "_next_solar",
        "_prev_solar",
        "_solar",
        "sunrise",
        "sunset",
        "transit",
    )

    def __init__(self, unix_day: int, latitude: float, longitude: float) -> None:
        jd = _julian_day(*civil_from_days(unix_day))
        self._latitude = latitude
        self._longitude = longitude
        self._solar = _solar_coordinates(jd)
        self._prev_solar = _solar_coordinates(jd - 1)
        self._next_solar = _solar_coordinates(jd + 1)
        m0 = _approximate_transit(
            longitude,
            self._solar.apparent_sidereal_time,
            self._solar.right_ascension,
        )
        solar_altitude = -50.0 / 60.0
        self._approx_transit = m0
        self.transit = _corrected_transit(
            m0, longitude, self._solar, self._prev_solar, self._next_solar
        )
        self.sunrise = self.hour_angle(solar_altitude, after_transit=False)
        self.sunset = self.hour_angle(solar_altitude, after_transit=True)

    def hour_angle(self, angle: float, *, after_transit: bool) -> float:
        return _corrected_hour_angle(
            self._approx_transit,
            angle,
            self._latitude,
            self._longitude,
            self._solar,
            prev_solar=self._prev_solar,
            next_solar=self._next_solar,
            after_transit=after_transit,
        )

    def afternoon(self, shadow_length: int) -> float:
        tangent = abs(self._latitude - self._solar.declination)
        inverse = shadow_length + math.tan(_degrees_to_radians(tangent))
        angle = _radians_to_degrees(math.atan(1.0 / inverse))
        return self.hour_angle(angle, after_transit=True)


class _SolarCoordinates(NamedTuple):
    # The angle between the rays of the sun and the plane of the equator, in degrees.
    declination: float
    # In degrees.
    right_ascension: float
    # The hour angle of the vernal equinox, in degrees.
    apparent_sidereal_time: float


# Consecutive days share their coordinates: a year computes each day once.
@lru_cache(maxsize=1024)
def _solar_coordinates(julian_day: float) -> _SolarCoordinates:
    t = _julian_century(julian_day)
    l0 = _mean_solar_longitude(t)
    lp = _mean_lunar_longitude(t)
    omega = _ascending_lunar_node_longitude(t)
    lambda_ = _degrees_to_radians(_apparent_solar_longitude(t, l0))
    theta0 = _mean_sidereal_time(t)
    d_psi = _nutation_in_longitude(l0, lp, omega)
    d_epsilon = _nutation_in_obliquity(l0, lp, omega)
    epsilon0 = _mean_obliquity_of_the_ecliptic(t)
    epsilon_apparent = _degrees_to_radians(
        _apparent_obliquity_of_the_ecliptic(t, epsilon0)
    )
    return _SolarCoordinates(
        # Astronomical Algorithms, pages 165 and 88.
        declination=_radians_to_degrees(
            math.asin(math.sin(epsilon_apparent) * math.sin(lambda_))
        ),
        right_ascension=_unwind_angle(
            _radians_to_degrees(
                math.atan2(
                    math.cos(epsilon_apparent) * math.sin(lambda_), math.cos(lambda_)
                )
            )
        ),
        apparent_sidereal_time=theta0
        + (d_psi * 3600 * math.cos(_degrees_to_radians(epsilon0 + d_epsilon))) / 3600,
    )


# The page numbers are those of Astronomical Algorithms. `t * t` rather than `t ** 2`:
# the power of JavaScript multiplies for 2, the one of C may round differently.


def _mean_solar_longitude(t: float) -> float:
    # Page 163.
    term1 = 280.4664567
    term2 = 36000.76983 * t
    term3 = 0.0003032 * (t * t)
    return _unwind_angle(term1 + term2 + term3)


def _mean_lunar_longitude(t: float) -> float:
    # Page 144.
    term1 = 218.3165
    term2 = 481267.8813 * t
    return _unwind_angle(term1 + term2)


def _ascending_lunar_node_longitude(t: float) -> float:
    # Page 144.
    term1 = 125.04452
    term2 = 1934.136261 * t
    term3 = 0.0020708 * (t * t)
    term4 = t**3 / 450000
    return _unwind_angle(term1 - term2 + term3 + term4)


def _mean_solar_anomaly(t: float) -> float:
    # Page 163.
    term1 = 357.52911
    term2 = 35999.05029 * t
    term3 = 0.0001537 * (t * t)
    return _unwind_angle(term1 + term2 - term3)


def _solar_equation_of_the_center(t: float, mean_anomaly: float) -> float:
    # Page 164.
    m_rad = _degrees_to_radians(mean_anomaly)
    term1 = (1.914602 - 0.004817 * t - 0.000014 * (t * t)) * math.sin(m_rad)
    term2 = (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
    term3 = 0.000289 * math.sin(3 * m_rad)
    return term1 + term2 + term3


def _apparent_solar_longitude(t: float, mean_longitude: float) -> float:
    # Page 164.
    longitude = mean_longitude + _solar_equation_of_the_center(
        t, _mean_solar_anomaly(t)
    )
    omega = 125.04 - 1934.136 * t
    lambda_ = longitude - 0.00569 - 0.00478 * math.sin(_degrees_to_radians(omega))
    return _unwind_angle(lambda_)


def _mean_obliquity_of_the_ecliptic(t: float) -> float:
    # Page 147.
    term1 = 23.439291
    term2 = 0.013004167 * t
    term3 = 0.0000001639 * (t * t)
    term4 = 0.0000005036 * t**3
    return term1 - term2 - term3 + term4


def _apparent_obliquity_of_the_ecliptic(t: float, mean_obliquity: float) -> float:
    # Page 165.
    o = 125.04 - 1934.136 * t
    return mean_obliquity + 0.00256 * math.cos(_degrees_to_radians(o))


def _mean_sidereal_time(t: float) -> float:
    # Page 165.
    jd = t * 36525 + 2451545.0
    term1 = 280.46061837
    term2 = 360.98564736629 * (jd - 2451545)
    term3 = 0.000387933 * (t * t)
    term4 = t**3 / 38710000
    return _unwind_angle(term1 + term2 + term3 - term4)


def _nutation_in_longitude(l0: float, lp: float, omega: float) -> float:
    # Page 144.
    term1 = (-17.2 / 3600) * math.sin(_degrees_to_radians(omega))
    term2 = (1.32 / 3600) * math.sin(2 * _degrees_to_radians(l0))
    term3 = (0.23 / 3600) * math.sin(2 * _degrees_to_radians(lp))
    term4 = (0.21 / 3600) * math.sin(2 * _degrees_to_radians(omega))
    return term1 - term2 - term3 + term4


def _nutation_in_obliquity(l0: float, lp: float, omega: float) -> float:
    # Page 144.
    term1 = (9.2 / 3600) * math.cos(_degrees_to_radians(omega))
    term2 = (0.57 / 3600) * math.cos(2 * _degrees_to_radians(l0))
    term3 = (0.1 / 3600) * math.cos(2 * _degrees_to_radians(lp))
    term4 = (0.09 / 3600) * math.cos(2 * _degrees_to_radians(omega))
    return term1 + term2 + term3 - term4


def _altitude_of_celestial_body(
    observer_latitude: float, declination: float, local_hour_angle: float
) -> float:
    # Page 93.
    term1 = math.sin(_degrees_to_radians(observer_latitude)) * math.sin(
        _degrees_to_radians(declination)
    )
    term2 = (
        math.cos(_degrees_to_radians(observer_latitude))
        * math.cos(_degrees_to_radians(declination))
        * math.cos(_degrees_to_radians(local_hour_angle))
    )
    return _radians_to_degrees(_asin(term1 + term2))


def _approximate_transit(
    longitude: float, sidereal_time: float, right_ascension: float
) -> float:
    # Page 102.
    lw = longitude * -1
    m0 = _normalize_to_scale((right_ascension + lw - sidereal_time) / 360, 1)
    # Near the date line, m0 can be a day off: half a day away from the transit
    # expected at this longitude.
    expected_transit = _normalize_to_scale((12.0 - longitude / 15.0) / 24.0, 1)
    if m0 - expected_transit > 0.5:  # noqa: PLR2004
        return m0 - 1.0
    if expected_transit - m0 > 0.5:  # noqa: PLR2004
        return m0 + 1.0
    return m0


def _corrected_transit(
    m0: float,
    longitude: float,
    solar: _SolarCoordinates,
    prev_solar: _SolarCoordinates,
    next_solar: _SolarCoordinates,
) -> float:
    """The time at which the sun is at its highest point in the sky, in hours."""
    # Page 102.
    lw = longitude * -1
    theta = _unwind_angle(solar.apparent_sidereal_time + 360.985647 * m0)
    a = _unwind_angle(
        _interpolate_angles(
            solar.right_ascension,
            prev_solar.right_ascension,
            next_solar.right_ascension,
            m0,
        )
    )
    h = _quadrant_shift_angle(theta - lw - a)
    dm = h / -360
    return (m0 + dm) * 24


def _corrected_hour_angle(
    m0: float,
    h0: float,
    latitude: float,
    longitude: float,
    solar: _SolarCoordinates,
    *,
    prev_solar: _SolarCoordinates,
    next_solar: _SolarCoordinates,
    after_transit: bool,
) -> float:
    # Page 102.
    lw = longitude * -1
    term1 = math.sin(_degrees_to_radians(h0)) - math.sin(
        _degrees_to_radians(latitude)
    ) * math.sin(_degrees_to_radians(solar.declination))
    term2 = math.cos(_degrees_to_radians(latitude)) * math.cos(
        _degrees_to_radians(solar.declination)
    )
    cos_h0 = term1 / term2
    # The sun never reaches this angle: NaN, like Math.acos in JavaScript.
    if not -1 <= cos_h0 <= 1:
        return math.nan
    big_h0 = _radians_to_degrees(math.acos(cos_h0))
    m = m0 + big_h0 / 360 if after_transit else m0 - big_h0 / 360
    theta = _unwind_angle(solar.apparent_sidereal_time + 360.985647 * m)
    a = _unwind_angle(
        _interpolate_angles(
            solar.right_ascension,
            prev_solar.right_ascension,
            next_solar.right_ascension,
            m,
        )
    )
    delta = _interpolate(
        solar.declination, prev_solar.declination, next_solar.declination, m
    )
    h = theta - lw - a
    altitude = _altitude_of_celestial_body(latitude, delta, h)
    term3 = altitude - h0
    term4 = (
        360
        * math.cos(_degrees_to_radians(delta))
        * math.cos(_degrees_to_radians(latitude))
        * math.sin(_degrees_to_radians(h))
    )
    dm = term3 / term4
    return (m + dm) * 24


def _interpolate(y2: float, y1: float, y3: float, n: float) -> float:
    """Interpolate a value from the days before and after, at `n` of a day. Page 24."""
    a = y2 - y1
    b = y3 - y2
    c = b - a
    return y2 + (n / 2) * (a + b + n * c)


def _interpolate_angles(y2: float, y1: float, y3: float, n: float) -> float:
    """Like `_interpolate()`, for angles."""
    a = _unwind_angle(y2 - y1)
    b = _unwind_angle(y3 - y2)
    c = b - a
    return y2 + (n / 2) * (a + b + n * c)


def _julian_day(year: int, month: int, day: int) -> float:
    # Page 60.
    y = year if month > 2 else year - 1  # noqa: PLR2004
    m = month if month > 2 else month + 12  # noqa: PLR2004
    a = math.trunc(y / 100)
    b = math.trunc(2 - a + math.trunc(a / 4))
    i0 = math.trunc(365.25 * (y + 4716))
    i1 = math.trunc(30.6001 * (m + 1))
    return i0 + i1 + day + b - 1524.5


def _julian_century(julian_day: float) -> float:
    # Page 163.
    return (julian_day - 2451545.0) / 36525


def _degrees_to_radians(degrees: float) -> float:
    return (degrees * math.pi) / 180.0


def _radians_to_degrees(radians: float) -> float:
    return (radians * 180.0) / math.pi


def _asin(x: float) -> float:
    # NaN out of -1 to 1, like Math.asin in JavaScript, where Python raises.
    return math.asin(x) if -1 <= x <= 1 else math.nan


def _normalize_to_scale(num: float, max_: float) -> float:
    return num - max_ * math.floor(num / max_)


def _unwind_angle(angle: float) -> float:
    return _normalize_to_scale(angle, 360.0)


def _quadrant_shift_angle(angle: float) -> float:
    if -180 <= angle <= 180:  # noqa: PLR2004
        return angle
    return angle - 360 * _round(angle / 360)


def _round(x: float) -> int:
    # Like Math.round in JavaScript: halves up, where Python rounds them to even.
    floor = math.floor(x)
    return floor + 1 if x - floor >= 0.5 else floor  # noqa: PLR2004
