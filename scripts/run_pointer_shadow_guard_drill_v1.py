#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointer_shadow_guard_drill_latest.json"
ALERT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_alert_latest.json"
GUARDED_DEFAULT = ART / "genesis_pointer_routing_decision_guarded_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    py = sys.executable
    # 1) Force alert with aggressive thresholds (min_sample_count=1, high required ok-rate)
    s1 = _run(
        [
            py,
            "scripts/check_pointer_shadow_health_alert_v1.py",
            "--min-sample-count",
            "1",
            "--candidate-ok-rate-min",
            "0.95",
            "--max-unresolved-per-run",
            "1",
        ]
    )
    alert = _read_json(ALERT_DEFAULT)

    # 2) Apply guard and expect HOLD downgrade
    s2 = _run([py, "scripts/apply_pointer_shadow_alert_guard_v1.py"])
    guarded = _read_json(GUARDED_DEFAULT)
    guard_ok = bool(guarded.get("guard_applied")) and guarded.get("decision") == "HOLD_POINTER_ROUTE"

    # 3) Restore normal alert thresholds to avoid leaving forced-alert state
    s3 = _run([py, "scripts/check_pointer_shadow_health_alert_v1.py"])
    restored_alert = _read_json(ALERT_DEFAULT)

    out_doc = {
        "schema": "pointer_shadow_guard_drill_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "steps": [s1, s2, s3],
        "forced_alert_snapshot": {
            "should_alert": alert.get("should_alert"),
            "severity": alert.get("severity"),
            "reasons": alert.get("reasons"),
        },
        "guard_snapshot": {
            "guard_applied": guarded.get("guard_applied"),
            "decision": guarded.get("decision"),
            "route_mode": guarded.get("route_mode"),
            "guard_reason": guarded.get("guard_reason"),
        },
        "restored_alert_snapshot": {
            "should_alert": restored_alert.get("should_alert"),
            "severity": restored_alert.get("severity"),
            "reasons": restored_alert.get("reasons"),
        },
        "drill_passed": guard_ok,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "drill_passed": guard_ok}, ensure_ascii=False))
    return 0 if guard_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
