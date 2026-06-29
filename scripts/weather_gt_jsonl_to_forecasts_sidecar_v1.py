#!/usr/bin/env python3
"""Build logistic forecasts sidecar from weather ground-truth JSONL (B-track, [HYPO])."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _station_slug(station_or_region_id: str) -> str:
    s = station_or_region_id.lower()
    digits = "".join(ch for ch in s if ch.isdigit())
    if "seoul" in s and digits:
        return f"seoul{digits}"
    slug = "".join(ch for ch in s if ch.isalnum())
    return slug[:32] or "unknown"


def _question_id(station: str, obs_date: str, lens: str) -> str:
    ymd = obs_date.replace("-", "")
    return f"btrack.weather_hist.{station}.{ymd}.{lens}"


def _logistic_p(precip_mm: float, *, scale: float = 0.08, center: float = 0.1) -> float:
    x = max(0.0, float(precip_mm))
    p = 1.0 / (1.0 + math.exp(-(x - center) / max(scale, 0.001)))
    return max(0.001, min(0.999, round(p, 4)))


def build_sidecar(
    gt_jsonl: Path,
    *,
    out_path: Path,
    use_prior_day_precip: bool = True,
) -> int:
    rows: list[dict[str, Any]] = []
    for line in gt_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    rows.sort(key=lambda r: (r.get("station_or_region_id"), r.get("observation_date_local")))
    by_key = {
        (r.get("station_or_region_id"), r.get("observation_date_local")): r for r in rows
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            station = row.get("station_or_region_id", "unknown")
            obs_date = row.get("observation_date_local", "")
            station_slug = _station_slug(str(station))
            prior_mm = 0.0
            if use_prior_day_precip:
                try:
                    dt = datetime.strptime(obs_date, "%Y-%m-%d")
                    prior_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
                    prior = by_key.get((station, prior_date))
                    if prior is not None:
                        prior_mm = float(prior.get("precip_mm_day") or 0.0)
                except ValueError:
                    prior_mm = 0.0
            today_mm = float(row.get("precip_mm_day") or 0.0)
            # Prior-day for myeongri; same-day precip_mm (not binary label) for sasang — synthetic sidecar contract.
            p_m = _logistic_p(prior_mm, scale=0.06)
            p_s = _logistic_p(today_mm, scale=0.04)
            p_f = round(0.5 * p_m + 0.5 * p_s, 4)
            for lens, p_val in (
                ("lens_myeongri", p_m),
                ("lens_sasang", p_s),
                ("lens_fusion_v1", p_f),
            ):
                doc = {
                    "question_id": _question_id(station_slug, obs_date, lens),
                    "p_myeongri": p_m if lens == "lens_myeongri" else None,
                    "p_sasang": p_s if lens == "lens_sasang" else None,
                    "probability_0_1": p_val,
                    "source_detail": f"weather_gt_sidecar_logistic_v1 prior_mm={prior_mm:.2f}",
                    "generated_at_utc": _utc_now(),
                }
                out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                written += 1
    print(f"WROTE: {out_path} rows={written}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--no-prior-day", action="store_true")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2
    return build_sidecar(ns.input, out_path=ns.output, use_prior_day_precip=not ns.no_prior_day)


if __name__ == "__main__":
    raise SystemExit(main())
