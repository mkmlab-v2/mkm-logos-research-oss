# -*- coding: utf-8 -*-
"""Global birth time → local civil (IANA) → PerfectManseryeok (y,m,d,h) inputs.

Production contract (v1):
- Prefer **birth_instant_utc** (ISO Z) + **iana_tz** — avoids DST gap/ambiguous wall-clock bugs.
- Alternative: local civil **y,m,d,h[,mi,s]** + **iana_tz** + optional **dst_fold** {0,1}.

Limitations:
- Uses OS/tzdata IANA zones (same as Python zoneinfo). Pre-modern LMT offsets are coarse;
  for astro-grade historical instants outside modern tzdb, supply UTC explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class BirthResolution:
    """Canonical inputs for PerfectManseryeok.calculate_full_saju_perfect."""

    birth_instant_utc: datetime
    iana_tz: str
    local_datetime: datetime
    engine_year: int
    engine_month: int
    engine_day: int
    engine_hour: int
    warnings: tuple[str, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)


def normalize_iana_tz(name: str) -> str:
    """Return trimmed IANA id; raises ValueError if zoneinfo cannot load it."""
    n = name.strip()
    if not n:
        raise ValueError("iana_tz is empty")
    try:
        ZoneInfo(n)
    except Exception as e:
        raise ValueError(f"invalid or unavailable IANA timezone: {name!r}") from e
    return n


def _parse_utc_iso(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        raise ValueError("UTC ISO must include Z or offset")
    return dt.astimezone(timezone.utc)


def _wall_parts(dt: datetime) -> tuple[int, int, int, int, int, int]:
    return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def _round_trip_skewed(zi: ZoneInfo, local: datetime) -> bool:
    """True if local wall is in a DST gap or was adjusted (not a stable civil clock in this zone)."""
    utc = local.astimezone(timezone.utc)
    back = utc.astimezone(zi)
    return _wall_parts(local) != _wall_parts(back)


def _ambiguous_wall_clocks(zi: ZoneInfo, y: int, m: int, d: int, h: int, mi: int, s: int) -> bool:
    """Whether two UTC instants share this civil wall time (fall-back repeated hour)."""
    try:
        a = datetime(y, m, d, h, mi, s, tzinfo=zi, fold=0).astimezone(timezone.utc)
        b = datetime(y, m, d, h, mi, s, tzinfo=zi, fold=1).astimezone(timezone.utc)
    except Exception:
        return False
    return a != b


def resolve_from_utc_instant(birth_instant_utc_iso: str, iana_tz: str) -> BirthResolution:
    """Primary path: absolute instant + zone for local calendar/hour extraction."""
    zi_name = normalize_iana_tz(iana_tz)
    zi = ZoneInfo(zi_name)
    utc = _parse_utc_iso(birth_instant_utc_iso)
    local = utc.astimezone(zi)
    warnings: list[str] = []
    return BirthResolution(
        birth_instant_utc=utc,
        iana_tz=zi_name,
        local_datetime=local,
        engine_year=local.year,
        engine_month=local.month,
        engine_day=local.day,
        engine_hour=local.hour,
        warnings=tuple(warnings),
        meta={"mode": "utc_instant"},
    )


def resolve_from_local_civil(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
    iana_tz: str,
    *,
    dst_fold: int = 0,
) -> BirthResolution:
    """Local civil clock in **iana_tz**. Use dst_fold 0 or 1 in repeated-DST hour (rare)."""
    if dst_fold not in (0, 1):
        raise ValueError("dst_fold must be 0 or 1")
    zi_name = normalize_iana_tz(iana_tz)
    zi = ZoneInfo(zi_name)
    local = datetime(year, month, day, hour, minute, second, tzinfo=zi, fold=int(dst_fold))
    if _round_trip_skewed(zi, local):
        raise ValueError(
            "local_civil_invalid_or_skewed: wall time does not exist in this zone (DST gap) "
            "or was adjusted; use birth_instant_utc + iana_tz instead."
        )
    utc = local.astimezone(timezone.utc)

    warnings: list[str] = []
    if _ambiguous_wall_clocks(zi, year, month, day, hour, minute, second):
        warnings.append(
            "dst_ambiguous_wall_clock: same local time maps to two UTC instants; "
            "dst_fold was applied. Prefer birth_instant_utc for irreversible clarity."
        )

    return BirthResolution(
        birth_instant_utc=utc,
        iana_tz=zi_name,
        local_datetime=local,
        engine_year=local.year,
        engine_month=local.month,
        engine_day=local.day,
        engine_hour=local.hour,
        warnings=tuple(warnings),
        meta={"mode": "local_civil", "dst_fold": int(dst_fold)},
    )


def try_zoneinfo(name: str) -> bool:
    try:
        ZoneInfo(name.strip())
        return True
    except Exception:
        return False
