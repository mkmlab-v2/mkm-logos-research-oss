#!/usr/bin/env python3
"""Attested-dataset promote drill — default eval path from policy [HYPO]."""

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
POLICY = ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_v1.json"
OUT = ROOT / "reports/sasang_attested_joint_promote_drill_v1_latest.json"
SMOKE_OUT = ROOT / "data/myeongni/sasang_saju_joint_benchmark_attested_only_smoke_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _attested_dataset() -> Path:
    if POLICY.is_file():
        pol = json.loads(POLICY.read_text(encoding="utf-8-sig"))
        return ROOT / str(pol.get("default_eval_dataset") or "")
    return ROOT / "data/myeongni/sasang_saju_joint_benchmark_attested_only_v1.jsonl"


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
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    ds = _attested_dataset()
    steps: list[dict[str, Any]] = []
    steps.append(_run("build_sasang_joint_benchmark_attested_only_snapshot_v1.py"))
    if all(s["ok"] for s in steps):
        steps.append(_run("build_sasang_joint_benchmark_eval_path_policy_gate_v1.py"))
    if all(s["ok"] for s in steps):
        steps.append(_run("validate_sasang_saju_joint_benchmark_jsonl_v1.py", ["--path", str(ds)]))
    if all(s["ok"] for s in steps):
        steps.append(
            _run(
                "run_sasang_saju_joint_benchmark_smoke_v1.py",
                ["--dataset", str(ds), "--out", str(SMOKE_OUT)],
            )
        )
    if all(s["ok"] for s in steps):
        steps.append(_run("build_sasang_attested_only_classification_gate_v1.py"))

    doc = {
        "schema": "sasang_attested_joint_promote_drill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "eval_dataset": str(ds).replace("\\", "/"),
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "promote_drill_mode": "attested_default",
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_attested_joint_promote_drill_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "eval_dataset": doc["eval_dataset"]}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
