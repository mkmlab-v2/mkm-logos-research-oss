# -*- coding: utf-8 -*-
"""Phase A: Grid-based edge-case timestamps for manseryeok / ganji regression (no engine calls).

Outputs JSON aligned with docs/final/artifacts/schemas/manseryeok_diff_target_output_v1.schema.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.core.solar_longitude_meeus_v1 import (  # noqa: E402
    jd_ut_to_datetime_utc,
    lichun_jd_ut_for_year,
)

SCHEMA_IN = "manseryeok_diff_target_input_v1"
SCHEMA_OUT = "manseryeok_diff_target_output_v1"
VERSION = "1.0.0"


def _default_input() -> dict[str, Any]:
    return {
        "schema": SCHEMA_IN,
        "version": VERSION,
        "timezone": "Asia/Seoul",
        "grid": {
            "kind": "compound",
            "years": list(range(2024, 2028)),
            "ipchun_window_hours": 48,
            "ipchun_step_hours": 2,
            "zi_anchor_date": "1992-03-13",
            "zi_hour_samples": [22.5, 23.0, 23.5, 0.0, 0.5, 1.0, 1.5],
        },
    }


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash_spec(spec: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(spec).encode("utf-8")).hexdigest()


def _build_targets(spec: dict[str, Any], tz_name: str) -> list[dict[str, Any]]:
    tz = ZoneInfo(tz_name)
    targets: list[dict[str, Any]] = []
    grid = spec.get("grid") or {}
    kind = grid.get("kind", "compound")
    years = grid.get("years") or [2024]
    win_h = float(grid.get("ipchun_window_hours", 48))
    step_h = float(grid.get("ipchun_step_hours", 2))

    if kind in ("ipchun_window", "compound"):
        for y in years:
            jd_lichun = lichun_jd_ut_for_year(int(y))
            t0 = jd_ut_to_datetime_utc(jd_lichun)
            start = t0 - timedelta(hours=win_h)
            t = start
            i = 0
            while t <= t0 + timedelta(hours=win_h):
                local = t.astimezone(tz)
                targets.append(
                    {
                        "target_id": f"ipchun_{y}_{i:04d}",
                        "category": "ipchun_adjacent",
                        "iso_local": local.isoformat(),
                        "iso_utc": t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "labels": {
                            "year": str(y),
                            "offset_hours_from_lichun_meeus": str(
                                round((t - t0).total_seconds() / 3600.0, 4)
                            ),
                        },
                    }
                )
                t += timedelta(hours=step_h)
                i += 1

    if kind in ("zi_boundary", "compound"):
        anchor = grid.get("zi_anchor_date") or "1992-03-13"
        y, m, d = (int(x) for x in anchor.split("-"))
        samples = grid.get("zi_hour_samples") or [23.0, 23.5, 0.0, 0.5, 1.0]
        for j, frac_h in enumerate(samples):
            base = datetime(y, m, d, 0, 0, 0, tzinfo=tz)
            # frac_h e.g. 23.5 = 23:30 same calendar day in local
            whole = int(frac_h)
            minute = int(round((frac_h - whole) * 60))
            if whole >= 24:
                base = base + timedelta(days=1)
                whole -= 24
            local_dt = base.replace(hour=whole, minute=minute, second=0, microsecond=0)
            utc_dt = local_dt.astimezone(timezone.utc)
            targets.append(
                {
                    "target_id": f"zi_{anchor}_{j:03d}",
                    "category": "zi_boundary",
                    "iso_local": local_dt.isoformat(),
                    "iso_utc": utc_dt.isoformat().replace("+00:00", "Z"),
                    "labels": {"anchor_date_local": anchor, "local_hour_frac": str(frac_h)},
                }
            )

    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate manseryeok diff target grid JSON.")
    ap.add_argument("--input", type=Path, help="Input JSON (manseryeok_diff_target_input_v1)")
    ap.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs/final/artifacts/manseryeok_diff_target_latest.json",
    )
    args = ap.parse_args()

    spec = _default_input()
    if args.input and args.input.exists():
        spec = json.loads(args.input.read_text(encoding="utf-8"))

    tz_name = spec.get("timezone", "Asia/Seoul")
    h = _hash_spec(spec)
    targets = _build_targets(spec, tz_name)

    out = {
        "schema": SCHEMA_OUT,
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timezone": tz_name,
        "reproducibility": {"grid_spec_hash": h},
        "targets": targets,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(targets)} targets to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
