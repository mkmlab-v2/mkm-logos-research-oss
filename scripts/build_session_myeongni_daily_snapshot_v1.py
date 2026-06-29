#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily session-myeongni snapshot (09:00 KST pillars + hybrid legs) for one calendar date."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-date", type=str, default=None, help="YYYY-MM-DD (default: local today)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--skip-panel-rebuild", action="store_true")
    args = ap.parse_args()

    target = args.target_date or datetime.now().strftime("%Y-%m-%d")
    tag = target.replace("-", "")
    out = args.out or (ROOT / f"reports/session_myeongni_prediction_{tag}_v1.json")
    panel_csv = ROOT / f"reports/btrack_session_myeongni_panel_{tag}_daily.csv"
    obs_path = ROOT / "docs/final/artifacts/session_myeongni_hybrid_observation_latest.json"

    if not args.skip_panel_rebuild:
        rc = _run(
            [
                sys.executable,
                "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
                "--date-from",
                target,
                "--date-to",
                target,
                "--out-csv",
                str(panel_csv),
            ]
        )
        if rc != 0:
            return rc

    pillars: dict[str, str] = {}
    five_mass: dict[str, float] = {}
    session_score: float | None = None
    mapping: str | None = None

    if panel_csv.is_file():
        with panel_csv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if str(row.get("session_local_date", ""))[:10] != target:
                    continue
                pillars = {
                    "year": row.get("year_pillar", ""),
                    "month": row.get("month_pillar", ""),
                    "day": row.get("day_pillar", ""),
                    "hour": row.get("hour_pillar", ""),
                }
                five_mass = {
                    "목": float(row.get("elem_wood") or 0),
                    "화": float(row.get("elem_fire") or 0),
                    "토": float(row.get("elem_earth") or 0),
                    "금": float(row.get("elem_metal") or 0),
                    "수": float(row.get("elem_water") or 0),
                }
                break

    obs = None
    if obs_path.is_file():
        obs = json.loads(obs_path.read_text(encoding="utf-8"))

    today_obs = (obs or {}).get("today") or {}
    if today_obs.get("session_local_date", "")[:10] == target:
        if today_obs.get("pillars_session"):
            pillars = today_obs["pillars_session"]
        if today_obs.get("session_direction_score") is not None:
            session_score = float(today_obs["session_direction_score"])
        if today_obs.get("mapping_target"):
            mapping = str(today_obs["mapping_target"])

    kospi_pred = "neutral"
    if mapping == "sideways":
        kospi_pred = "neutral"
    elif mapping in ("bull", "bear"):
        kospi_pred = mapping

    doc: dict[str, Any] = {
        "schema": "session_myeongni_prediction_daily_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "replaces_birth_myeongni": False,
        "disclaimer_ko": "세션 09:00 KST 四柱. 擇日/日課 전 학파 대표 아님. Track A·실매매 비연동.",
        "target_date": target,
        "session_open": {
            "iana_tz": "Asia/Seoul",
            "local_hms": "09:00:00",
            "calendar_mode": "krx_weekdays",
        },
        "pillars_session": pillars,
        "five_element_mass_v0": five_mass or None,
        "session_direction_score": session_score,
        "mapping_target": mapping,
        "neutral_band": 0.06,
        "prediction_1d": {
            "kospi": {
                "direction_hypo": kospi_pred,
                "hybrid_leg": "session_per_date",
            },
            "btc": {
                "direction_hypo": "bear",
                "hybrid_leg": "frozen_baseline",
            },
        },
        "artifacts": {
            "panel_csv": str(panel_csv.relative_to(ROOT)).replace("\\", "/"),
            "observation_latest": str(obs_path.relative_to(ROOT)).replace("\\", "/")
            if obs_path.is_file()
            else None,
        },
        "rolling_eval_pointer": (obs or {}).get("rolling_eval"),
        "holdout_252d_pointer": (obs or {}).get("holdout_252d"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/session_myeongni_daily_snapshot_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
