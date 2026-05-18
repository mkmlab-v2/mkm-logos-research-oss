#!/usr/bin/env python3
"""One-shot: align decision/canary/active KPI to RQ-016 bench floor 0.47 (promoted Track A)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
THR = ROOT / "docs/final/artifacts/compression_alarm_thresholds_v1.json"

from scripts.ultra_compression_track_a_policy_floor_v1 import (  # noqa: E402
    TRACK_A_PROMOTED_POLICY_MIN,
    apply_promoted_policy_floor_to_quality_gate,
)


def _patch_decision(doc: dict[str, Any]) -> dict[str, Any]:
    target = doc.setdefault("target", {})
    if isinstance(target, dict):
        target["saving_rate"] = TRACK_A_PROMOTED_POLICY_MIN
    canary = doc.get("canary_policy") or {}
    thresholds = canary.get("thresholds") if isinstance(canary, dict) else None
    if isinstance(thresholds, dict):
        thresholds["saving_rate_min"] = TRACK_A_PROMOTED_POLICY_MIN
    anchor = doc.setdefault("promotion_anchor", {})
    if isinstance(anchor, dict):
        anchor["bench_saving_floor_min"] = TRACK_A_PROMOTED_POLICY_MIN
        anchor["decision_canary_saving_rate_min"] = TRACK_A_PROMOTED_POLICY_MIN
        anchor["aligned_at_utc"] = datetime.now(timezone.utc).isoformat()
        anchor["note"] = (
            "Promoted Track A: decision/canary/KPI policy floor aligned to RQ-016 bench 0.47 "
            "(not global ssot 0.45 pin; case-allowlist only)."
        )
    return doc


def main() -> int:
    if not DECISION.is_file():
        print(f"ABORT: missing {DECISION}")
        return 1

    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    decision = _patch_decision(decision)
    DECISION.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PATCHED: {DECISION.relative_to(ROOT)}")

    if ACTIVE.is_file():
        active = json.loads(ACTIVE.read_text(encoding="utf-8"))
        apply_promoted_policy_floor_to_quality_gate(active)
        ACTIVE.write_text(json.dumps(active, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PATCHED: {ACTIVE.relative_to(ROOT)}")

    if THR.is_file():
        thr = json.loads(THR.read_text(encoding="utf-8"))
        thr["track_a_promoted_policy_min"] = TRACK_A_PROMOTED_POLICY_MIN
        thr["suggested_policy_floor_token_saving_rate"] = TRACK_A_PROMOTED_POLICY_MIN
        thr["description"] = (
            "Active_kpi bounds for send_compression_kpi_alarm_if_needed.ps1. "
            "Promoted Track A uses RQ-016 bench/decision floor 0.47 (ultra_saving_policy_ok). "
            "Legacy grid evaluate_report may still emit 0.49 for non-promoted sweeps."
        )
        THR.write_text(json.dumps(thr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PATCHED: {THR.relative_to(ROOT)}")

    import subprocess

    subprocess.run([sys.executable, str(ROOT / "scripts/run_ultra_compression_default.py")], check=True, cwd=str(ROOT))
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/report_ultra_compression_kpi_summary.py")],
        check=True,
        cwd=str(ROOT),
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_lg_hs_compression_discipline_deck_v1.py")],
        check=False,
        cwd=str(ROOT),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
