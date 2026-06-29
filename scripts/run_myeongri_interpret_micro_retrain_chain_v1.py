#!/usr/bin/env python3
"""Myeongri Interpret optional micro-retrain chain (CPU gate default, GPU optional) [HYPO]."""

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
OUT = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _cuda_available() -> bool:
    proc = subprocess.run(
        [PY, "-c", "import torch; print(torch.cuda.is_available())"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and "True" in (proc.stdout or "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-steps", type=int, default=15)
    ap.add_argument("--with-gpu-train", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(
        _run_step(
            "interpret_cpu_guard",
            [PY, str(ROOT / "scripts/verify_myeongri_interpret_v4_guard_bundle_v1.py")],
        )
    )

    gpu_train_attempted = False
    gpu_train_skipped_reason: str | None = None
    if args.with_gpu_train:
        if not _cuda_available():
            gpu_train_skipped_reason = "cuda_unavailable"
        else:
            gpu_train_attempted = True
            ps1 = ROOT / "scripts/Run-MyeongriInterpretV4EvalChain_v1.ps1"
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
                "-SkipRebuild",
                "-SkipOracleAudit",
                "-SkipEval25",
                "-SkipEval100",
                "-SkipNarrativeAudit",
                "-TrainSteps",
                str(max(10, min(20, args.train_steps))),
            ]
            steps.append(_run_step("interpret_gpu_micro_train", cmd))

    cpu_ok = steps[0]["ok"] if steps else False
    gpu_ok = True
    if gpu_train_attempted:
        gpu_ok = steps[-1]["ok"] if len(steps) > 1 else False

    doc = {
        "schema": "myeongri_interpret_micro_retrain_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "train_steps_requested": args.train_steps,
        "with_gpu_train": args.with_gpu_train,
        "gpu_train_attempted": gpu_train_attempted,
        "gpu_train_skipped_reason": gpu_train_skipped_reason,
        "steps": steps,
        "cpu_guard_ok": cpu_ok,
        "gpu_train_ok": gpu_ok if gpu_train_attempted else None,
        "chain_ok": cpu_ok and (gpu_ok if gpu_train_attempted else True),
        "reproduce": "py scripts/run_myeongri_interpret_micro_retrain_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["chain_ok"], "cpu_guard_ok": cpu_ok, "gpu_train": gpu_train_attempted}))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
