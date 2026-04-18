# -*- coding: utf-8 -*-
"""Approximate apparent geocentric ecliptic longitude of the Sun (degrees).

Used for solar-term boundary search (e.g. 立春 ≈ λ = 315° tropical).
Not observatory-grade; suitable for engineering deltas vs naive anchors.

Reference: Meeus, Astronomical Algorithms (compact implementation).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

# Julian date at Unix epoch (1970-01-01 00:00 UTC)
_JD_UNIX = 2440587.5


def _datetime_to_jd_ut(dt: datetime) -> float:
    """Julian Date for UTC instant."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    t = dt.astimezone(timezone.utc)
    y = t.year
    m = t.month
    d = t.day + (
        t.hour + (t.minute + t.second / 60.0) / 60.0
    ) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5
    return float(jd)


def sun_apparent_ecliptic_longitude_deg(jd_ut: float) -> float:
    """Apparent longitude of Sun (λ, degrees), roughly aligned with tropical zodiac."""
    t = (jd_ut - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    m_rad = math.radians(m)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m_rad)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
        + 0.000289 * math.sin(3 * m_rad)
    )
    sun_lon = l0 + c
    sun_lon %= 360.0
    if sun_lon < 0:
        sun_lon += 360.0
    omega = 125.04 - 1934.136 * t
    lambda_app = sun_lon - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    lambda_app %= 360.0
    if lambda_app < 0:
        lambda_app += 360.0
    return float(lambda_app)


def jd_ut_to_datetime_utc(jd_ut: float) -> datetime:
    """UTC datetime from Julian Date."""
    epoch = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return epoch + timedelta(seconds=(jd_ut - _JD_UNIX) * 86400.0)


def lichun_jd_ut_for_year(year: int) -> float:
    """立春: Sun's apparent ecliptic longitude = 315° (tropical), Jan–Mar window."""
    jd0 = _datetime_to_jd_ut(datetime(year, 1, 15, 12, 0, 0, tzinfo=timezone.utc))
    jd1 = _datetime_to_jd_ut(datetime(year, 3, 1, 12, 0, 0, tzinfo=timezone.utc))
    lo, hi = jd0, jd1
    for _ in range(100):
        if hi - lo < 1e-8:
            break
        mid = (lo + hi) / 2.0
        if sun_apparent_ecliptic_longitude_deg(mid) < 315.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
