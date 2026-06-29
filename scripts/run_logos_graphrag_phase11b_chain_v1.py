#!/usr/bin/env python3
"""Phase 11-B chain: validate UNIVERSAL_ROOT_GATE_SPEC + gate eval report [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11b_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps = {
        "check_gate_spec": _run([py, "scripts/check_universal_root_gate_spec_v1.py"]),
        "check_gate_spec_enforce": _run(
            [py, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"]
        ),
    }

    eval_report = ROOT / "reports/universal_root_gate_eval_v1_latest.json"
    eval_summary = {}
    if eval_report.is_file():
        doc = json.loads(eval_report.read_text(encoding="utf-8"))
        ev = doc.get("evaluation") or {}
        eval_summary = {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
            "planes": [
                {"plane": p.get("plane"), "ok": p.get("ok"), "enabled": p.get("enabled")}
                for p in (ev.get("planes") or [])
            ],
        }

    # Structural validate must pass; enforce may fail while gates HOLD (expected)
    ok = steps["check_gate_spec"]["exit_code"] == 0
    out_doc = {
        "schema": "logos_graphrag_phase11b_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "steps": steps,
        "gate_eval_summary": eval_summary,
        "spec_ssot": "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json",
        "reproduce": "py scripts/run_logos_graphrag_phase11b_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out), "gate_eval_summary": eval_summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
