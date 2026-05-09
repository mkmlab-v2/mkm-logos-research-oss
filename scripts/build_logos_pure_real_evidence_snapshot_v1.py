#!/usr/bin/env python3
"""Create a baseline evidence snapshot for pure-real PASS state."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
SNAP_ROOT = ART / "evidence_snapshots"
DEFAULT_OUT = ART / "logos_pure_real_evidence_snapshot_latest.json"

DEFAULT_FILES = [
    ART / "logos_pure_real_daily_go_nogo_latest.json",
    ART / "logos_backfill_dependence_monitor_latest.json",
    ART / "logos_pure_real_execution_gate_weekly_alert_latest.json",
    ART / "logos_pure_real_d7_stability_checklist_latest.json",
    ART / "logos_backfill_delta_sweep_latest.json",
    ART / "logos_temporal_holdout_compare_backfill_latest.json",
    ART / "logos_pure_real_progress_report_latest.json",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _slug_ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real evidence snapshot bundle.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--snapshot-label", type=str, default="pass_baseline")
    args = ap.parse_args()

    now = _utc_now()
    snap_dir = SNAP_ROOT / f"logos_pure_real_{args.snapshot_label}_{_slug_ts(now)}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    for src in DEFAULT_FILES:
        if not src.exists():
            missing.append(str(src).replace("\\", "/"))
            continue
        dst = snap_dir / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src).replace("\\", "/"),
                "snapshot": str(dst).replace("\\", "/"),
            }
        )

    index = {
        "schema": "logos_pure_real_evidence_snapshot_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "snapshot_label": str(args.snapshot_label),
        "snapshot_dir": str(snap_dir).replace("\\", "/"),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "copied": copied,
        "missing": missing,
    }

    (snap_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "snapshot_dir": str(snap_dir),
                "copied_count": len(copied),
                "missing_count": len(missing),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

