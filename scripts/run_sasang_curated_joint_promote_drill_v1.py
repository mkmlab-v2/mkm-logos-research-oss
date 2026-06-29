#!/usr/bin/env python3
"""Curated joint promote drill: CSV + JSONL ingest gates with optional apply [HYPO]."""

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
OUT = ROOT / "reports/sasang_curated_joint_promote_drill_v1_latest.json"


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
    ap.add_argument("--apply", action="store_true", help="Apply CSV/JSONL promote when gates report ready.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("build_sasang_curated_joint_ingest_gate_v1.py", ["--apply"] if args.apply else []))
    steps.append(
        _run(
            "build_sasang_literature_curated_promote_gate_v1.py",
            ["--apply"] if args.apply else [],
        )
    )
    if all(s["ok"] for s in steps):
        steps.append(_run("build_sasang_curated_joint_unified_gate_v1.py"))
    if all(s["ok"] for s in steps):
        steps.append(_run("validate_sasang_saju_joint_benchmark_jsonl_v1.py"))
        steps.append(_run("run_sasang_saju_joint_benchmark_smoke_v1.py"))

    unified_path = ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
    unified = json.loads(unified_path.read_text(encoding="utf-8-sig")) if unified_path.is_file() else {}

    doc = {
        "schema": "sasang_curated_joint_promote_drill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "apply_mode": args.apply,
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "curated_joint_status": unified.get("curated_joint_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_curated_joint_promote_drill_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "curated_joint_status": doc.get("curated_joint_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
