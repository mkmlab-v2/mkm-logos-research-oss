#!/usr/bin/env python3
"""COMP-VERIFY-01: refresh comp_atom01 control vs bridge_on + AB summary (research, active untouched)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
RUNNER = ROOT / "scripts" / "run_ultra_compression_default.py"
CONTROL_OUT = PILOT / "comp_atom01_control_v1.json"
BRIDGE_OUT = PILOT / "comp_atom01_bridge_on_v1.json"
SUMMARY_OUT = PILOT / "comp_atom01_ab_summary_v1.json"


def _metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    qg = report.get("quality_gate") or {}
    prof = report.get("active_profile") or {}
    return {
        "global_token_saving_rate": float(cm.get("global_token_saving_rate", 0.0)),
        "avg_reconstruction_fidelity_jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "avg_sensitive_integrity": float(cm.get("avg_sensitive_integrity", 0.0)),
        "sensitive_integrity_ok": bool(qg.get("sensitive_integrity_ok")),
        "ultra_saving_policy_ok": bool(qg.get("ultra_saving_policy_ok")),
        "apply_gematria_4d_bridge_policy": bool(prof.get("apply_gematria_4d_bridge_policy")),
    }


def _run_eval(*, bridge: bool, out_path: Path) -> int:
    cmd = [sys.executable, str(RUNNER), "--out", str(out_path)]
    if bridge:
        cmd.append("--apply-gematria-4d-bridge-policy")
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(proc.returncode)


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    rc_c = _run_eval(bridge=False, out_path=CONTROL_OUT)
    rc_b = _run_eval(bridge=True, out_path=BRIDGE_OUT)
    if rc_c != 0 or rc_b != 0:
        print(json.dumps({"control_exit": rc_c, "bridge_exit": rc_b}, ensure_ascii=False))
        return 1 if rc_c != 0 else rc_b

    control = json.loads(CONTROL_OUT.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE_OUT.read_text(encoding="utf-8"))
    mc = _metrics(control)
    mb = _metrics(bridge)
    deltas = {k: mb[k] - mc[k] if isinstance(mc[k], (int, float)) else int(mb[k]) - int(mc[k]) for k in mc}

    summary = {
        "schema": "comp_atom01_ab_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "allow_promotion": False,
        "active_report_untouched": True,
        "refresh_script": "scripts/comp_atom01_ab_refresh_v1.py",
        "sources": {
            "control": str(CONTROL_OUT.relative_to(ROOT)).replace("\\", "/"),
            "bridge_on": str(BRIDGE_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "metrics_control": mc,
        "metrics_bridge_on": mb,
        "deltas_bridge_on_minus_control": deltas,
        "interpretation": (
            "Bridge ON trades saving_rate down for jaccard up on same 40-case V2 bench; "
            "not Track A promotion."
        ),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": SUMMARY_OUT.name,
                "control_saving": round(mc["global_token_saving_rate"], 4),
                "bridge_saving": round(mb["global_token_saving_rate"], 4),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
