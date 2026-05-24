#!/usr/bin/env python3
"""Auto: RAG pipeline (no gold taint) → R3 eval → promotion gate → review packet."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports/constitution" / "btrack_pilot"
DEFAULT_OUT = PILOT / "comp_logos_rag_promotion_auto_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild-index", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    full_cmd = [py, str(ROOT / "scripts/run_logos_rag_full_auto_v1.py"), "--skip-auto-adjudication"]
    if args.rebuild_index:
        full_cmd.append("--rebuild-index")
    steps.append(_run(full_cmd, "full_auto_skip_adjudication"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_retrieval_eval_r3_v1.py")], "eval_r3_weak_gold"))
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py"),
                "--run-pytest",
            ],
            "promotion_gate",
        )
    )
    steps.append(
        _run([py, str(ROOT / "scripts/build_logos_rag_promotion_review_packet_v1.py")], "review_packet")
    )

    gate_path = ROOT / "docs/final/artifacts/logos_rag_btrack_promotion_gate_v1_latest.json"
    gate: dict[str, Any] = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    gate_rc = next((s.get("exit_code") for s in steps if s.get("step") == "promotion_gate"), 0)
    doc = {
        "schema": "comp_logos_rag_promotion_auto_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "ok": all(s.get("exit_code", 0) == 0 for s in steps if s.get("step") != "promotion_gate")
        and gate_rc in (0, 1),
        "promotion_gate_exit_code": gate_rc,
        "steps": steps,
        "recommended_commander_action": gate.get("recommended_commander_action"),
        "tiers": {
            k: {"passed": (v or {}).get("passed"), "approval_ready": (v or {}).get("approval_ready")}
            for k, v in (gate.get("tiers") or {}).items()
        },
        "approve_when_ready": {
            "L1": "py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L1",
            "L2": "py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L2",
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "action": doc["recommended_commander_action"],
                "L1_ready": (gate.get("tiers") or {}).get("L1_btrack_lab_bundle", {}).get("approval_ready"),
                "L2_ready": (gate.get("tiers") or {}).get("L2_track_c_shadow_ingest", {}).get("approval_ready"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
