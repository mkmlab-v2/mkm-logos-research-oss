#!/usr/bin/env python3
"""Commander clinical promote drill: deid gate → human-gate ingest → attested refresh [HYPO]."""

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
OUT = ROOT / "reports/sasang_commander_clinical_promote_drill_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-gate-ack", action="store_true", help="Apply clinical deid row to mainline.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("build_sasang_commander_clinical_deid_row_gate_v1.py"))
    if all(s["ok"] for s in steps):
        extra = ["--human-gate-ack"] if args.human_gate_ack else []
        steps.append(_run("apply_commander_attested_clinical_stub_v1.py", extra))
    if all(s["ok"] for s in steps) and args.human_gate_ack:
        steps.append(_run("build_sasang_commander_clinical_ingest_gate_v1.py"))
        steps.append(_run("build_sasang_joint_benchmark_attested_only_snapshot_v1.py"))
        steps.append(_run("run_sasang_attested_only_eval_chain_v1.py"))

    ingest_gate = ROOT / "docs/final/artifacts/sasang_commander_clinical_ingest_gate_v1_latest.json"
    ingest = json.loads(ingest_gate.read_text(encoding="utf-8-sig")) if ingest_gate.is_file() else {}

    doc = {
        "schema": "sasang_commander_clinical_promote_drill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "human_gate_ack_mode": args.human_gate_ack,
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "clinical_ingest_status": ingest.get("clinical_ingest_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_commander_attested_clinical_promote_drill_v1.py --human-gate-ack",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "clinical_ingest_status": doc.get("clinical_ingest_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
