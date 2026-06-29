#!/usr/bin/env python3
"""Build ENTRY_13 shadow + ENTRY_16 Ezra deep-research supplements; refresh gates [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/entry_13_16_deep_research_supplement_chain_v1_latest.json"

STEPS = [
    ("entry13_supplement", "build_entry_13_ps5_8_9_deep_research_supplement_v1.py"),
    ("entry16_plan", "build_entry_16_ezra_2_54_deep_research_plan_v1.py"),
    ("entry13_va_packet", "build_entry_13_ps5_2_verified_anchor_evidence_packet_v1.py"),
    ("entry16_promotion_gate", "evaluate_entry16_promotion_gate.py"),
    ("wq_consolidated_gate", "build_cross_ref_waiting_queue_consolidated_gate_v1.py"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script in STEPS:
        steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_entry_13_16_deep_research_supplement_v1.py",
            "tests/test_cross_ref_dss_schema.py",
        ):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "-m", "pytest", test_path, "-q"], cwd=ROOT, capture_output=True, text=True)
            steps.append(
                {
                    "name": f"pytest:{test_path}",
                    "exit_code": proc.returncode,
                    "elapsed_sec": round(time.perf_counter() - t0, 2),
                    "stdout_tail": (proc.stdout or "")[-200:],
                    "ok": proc.returncode == 0,
                }
            )
            if proc.returncode != 0:
                break

    e13 = {}
    p13 = ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json"
    if p13.is_file():
        e13 = json.loads(p13.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "entry_13_16_deep_research_supplement_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "entry_13_verified_anchor_achieved": e13.get("verified_anchor_achieved"),
        "not_entry_16_psalm_confusion": e13.get("not_entry_16"),
        "reproduce": "py scripts/run_entry_13_16_deep_research_supplement_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "steps": len(steps)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
