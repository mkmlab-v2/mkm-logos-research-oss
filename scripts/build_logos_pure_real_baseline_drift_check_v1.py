#!/usr/bin/env python3
"""Compare current pure-real status against latest baseline snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SNAPSHOT_INDEX = ART / "logos_pure_real_evidence_snapshot_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_baseline_drift_check_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path)


def _find_snapshot_file(index: dict[str, Any], filename: str) -> Path | None:
    for item in index.get("copied") or []:
        if Path(str(item.get("snapshot") or "")).name == filename:
            return Path(str(item.get("snapshot")))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build baseline drift check against latest evidence snapshot.")
    ap.add_argument("--snapshot-index-json", type=Path, default=DEFAULT_SNAPSHOT_INDEX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    idx = _safe_load(args.snapshot_index_json)

    cur_go = _safe_load(ART / "logos_pure_real_daily_go_nogo_latest.json")
    cur_mon = _safe_load(ART / "logos_backfill_dependence_monitor_latest.json")
    cur_d7 = _safe_load(ART / "logos_pure_real_d7_stability_checklist_latest.json")

    snap_go = _safe_load(_find_snapshot_file(idx, "logos_pure_real_daily_go_nogo_latest.json") or Path(""))
    snap_mon = _safe_load(_find_snapshot_file(idx, "logos_backfill_dependence_monitor_latest.json") or Path(""))
    snap_d7 = _safe_load(_find_snapshot_file(idx, "logos_pure_real_d7_stability_checklist_latest.json") or Path(""))

    checks: list[dict[str, Any]] = []

    cur_go_dec = str(cur_go.get("decision") or "")
    base_go_dec = str(snap_go.get("decision") or "")
    checks.append(
        {
            "id": "go_nogo_decision",
            "status": "PASS" if cur_go_dec == base_go_dec else "FAIL",
            "current": cur_go_dec,
            "baseline": base_go_dec,
        }
    )

    cur_mon_status = str(cur_mon.get("status") or "")
    base_mon_status = str(snap_mon.get("status") or "")
    checks.append(
        {
            "id": "monitor_status",
            "status": "PASS" if cur_mon_status == base_mon_status else "WARN",
            "current": cur_mon_status,
            "baseline": base_mon_status,
        }
    )

    cur_d7_status = str((cur_d7.get("summary") or {}).get("overall_status") or "")
    base_d7_status = str((snap_d7.get("summary") or {}).get("overall_status") or "")
    checks.append(
        {
            "id": "d7_summary_status",
            "status": "PASS" if cur_d7_status == base_d7_status else "WARN",
            "current": cur_d7_status,
            "baseline": base_d7_status,
        }
    )

    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    if fail_count > 0:
        overall = "FAIL_DRIFT_DETECTED"
    elif warn_count > 0:
        overall = "WARN_PARTIAL_DRIFT"
    else:
        overall = "PASS_ALIGNED_WITH_BASELINE"

    out = {
        "schema": "logos_pure_real_baseline_drift_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "baseline_snapshot_index": str(args.snapshot_index_json).replace("\\", "/"),
        "summary": {
            "overall_status": overall,
            "fail_count": fail_count,
            "warn_count": warn_count,
            "check_count": len(checks),
        },
        "checks": checks,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "overall_status": overall}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

