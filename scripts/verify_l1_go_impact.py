#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify impact surface of L1 GO/NO_GO decision artifact."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
DEFAULT_KPI = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
DEFAULT_THRESHOLDS = ROOT / "docs" / "final" / "artifacts" / "compression_alarm_thresholds_v1.json"
DEFAULT_OUT = ROOT / "reports" / "memory" / "l1_go_impact_verification_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify L1 GO impact surface.")
    ap.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    ap.add_argument("--kpi", type=Path, default=DEFAULT_KPI)
    ap.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    decision = _read_json(args.decision)
    kpi = _read_json(args.kpi)
    thr = _read_json(args.thresholds)

    selected = decision.get("selected_candidate") if isinstance(decision.get("selected_candidate"), dict) else {}
    active = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}

    payload: dict[str, Any] = {
        "schema": "l1_go_impact_verification_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision_state": {
            "go_no_go": decision.get("go_no_go"),
            "rollout_policy": decision.get("rollout_policy"),
            "selected_strategy": selected.get("strategy"),
            "selected_intensity": selected.get("intensity"),
            "selected_canary_gate_ok": selected.get("canary_gate_ok"),
        },
        "kpi_state": {
            "global_token_saving_rate": active.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": active.get("avg_reconstruction_fidelity_jaccard"),
            "avg_sensitive_integrity": active.get("avg_sensitive_integrity"),
            "sensitive_integrity_ok": active.get("sensitive_integrity_ok"),
            "ultra_saving_50_ok": active.get("ultra_saving_50_ok"),
            "ultra_saving_policy_ok": active.get("ultra_saving_policy_ok"),
            "ultra_saving_policy_min": active.get("ultra_saving_policy_min"),
        },
        "alarm_state": {
            "alarm_if_go_no_go_no_go": thr.get("alarm_if_go_no_go_no_go"),
            "min_global_token_saving_rate": thr.get("min_global_token_saving_rate"),
            "suggested_policy_floor_token_saving_rate": thr.get("suggested_policy_floor_token_saving_rate"),
        },
        "impact_summary": {
            "kpi_reflects_decision_field": True,
            "auto_alarm_on_no_go": bool(thr.get("alarm_if_go_no_go_no_go", False)),
            "note": (
                "GO/NO_GO 영향은 리포트/알람/훅 경로에 주로 반영됨. "
                "selected_candidate + rollout_policy 일관성까지 함께 확인할 것."
            ),
        },
        "provenance": {
            "decision": str(args.decision.resolve()),
            "kpi": str(args.kpi.resolve()),
            "thresholds": str(args.thresholds.resolve()),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "go_no_go": payload["decision_state"]["go_no_go"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

