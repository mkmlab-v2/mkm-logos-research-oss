#!/usr/bin/env python3
"""Weekly dual-probe drift alert (non-gating observability) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRIFT = ROOT / "reports/sasang_4agent_dual_probe_drift_v1_latest.json"
OUT = ROOT / "reports/sasang_4agent_dual_probe_weekly_drift_alert_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    drift = _load(DRIFT)
    status = str(drift.get("drift_status") or "missing")
    if status == "drift_alert":
        alert_level = "warning"
        message = "Dual-probe MDD drift exceeded band — review only, no Track A action."
    elif status == "within_band":
        alert_level = "info"
        message = "Dual-probe drift within band."
    elif status == "baseline_seeded":
        alert_level = "info"
        message = "Dual-probe baseline seeded; drift monitoring active."
    else:
        alert_level = "unknown"
        message = "Dual-probe drift report missing or incomplete."

    alert_ok = drift.get("schema") == "sasang_4agent_dual_probe_drift_v1"
    return {
        "schema": "sasang_4agent_dual_probe_weekly_drift_alert_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "alert_ok": alert_ok,
        "alert_level": alert_level,
        "drift_status": status,
        "drift_ok": drift.get("drift_ok"),
        "max_abs_mdd_drift": drift.get("max_abs_mdd_drift"),
        "message": message,
        "drift_ref": str(DRIFT).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_4agent_dual_probe_weekly_drift_alert_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["alert_ok"], "alert_level": doc["alert_level"]}))
    return 0 if doc["alert_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
