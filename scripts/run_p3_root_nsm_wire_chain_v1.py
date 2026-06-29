#!/usr/bin/env python3
"""P3 root NSM wire chain — schema + handoff + offline oracle gap [HYPO] (Phase 11-C)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/p3_root_nsm_wire_chain_v1_latest.json"


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
        "pytest_nsm_wire": _run([py, "-m", "pytest", "tests/test_ollama_shallow_router_nsm_wire_v1.py", "-q"]),
        "offline_nsm_bench": _run([py, "scripts/build_ollama_shallow_nsm_wire_offline_bench_v1.py"]),
        "oracle_gap_offline": _run(
            [
                py,
                "scripts/build_ollama_shallow_routing_oracle_gap_v1.py",
                "--bench-json",
                "reports/ollama_shallow_router_bench_nsm_wire_offline_v1_latest.json",
                "--max-oracle-gap",
                "0.0",
            ]
        ),
        "handoff_example": _run(
            [
                py,
                "scripts/build_ollama_shallow_router_handoff_v1.py",
                "--input-json",
                "docs/final/schemas/ollama_shallow_router_output_v1.example.json",
            ]
        ),
    }

    ok = all(s["exit_code"] == 0 for s in steps.values())
    gap_summary = {}
    gap_path = ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_latest.json"
    if gap_path.is_file():
        gap_doc = json.loads(gap_path.read_text(encoding="utf-8"))
        gap_summary = gap_doc.get("raw") or {}

    out_doc = {
        "schema": "p3_root_nsm_wire_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "steps": steps,
        "oracle_gap_summary": gap_summary,
        "distortion_gate_note": (
            "Post Phase 11-E: NSM crosswalk distortion 1.4% (shadow remapped) gate PASS; "
            "nsm_wire + handoff layer_a_gate_hint wire DeepNSM sidecar pointer."
        ),
        "reproduce": "py scripts/run_p3_root_nsm_wire_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out), "oracle_gap_summary": gap_summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
