#!/usr/bin/env python3
"""Daily mainline chain: sasang lens refresh → unified dynamics adapter [B-track HOLD].

  py scripts/run_sasang_unified_adapter_daily_chain_v1.py
  py scripts/run_sasang_unified_adapter_daily_chain_v1.py --skip-lens-refresh
"""

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
OUT = ROOT / "reports/sasang_unified_adapter_daily_chain_v1_latest.json"
MAINLINE_ARTIFACT = ROOT / "reports/sasang_dynamics_unified_v1_latest.json"
LENS_JSON = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-lens-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_lens_refresh:
        steps.append(_run("run_lens_sasang", [PY, str(ROOT / "scripts/run_lens_sasang.py")]))
        if not steps[-1]["ok"]:
            _write_report(args.out, steps, ok=False)
            return 1

    steps.append(
        _run(
            "unified_adapter_mainline",
            [
                PY,
                str(ROOT / "scripts/run_sasang_dynamics_unified_adapter_v1.py"),
                "--profile",
                "mainline",
            ],
        )
    )
    if not steps[-1]["ok"]:
        _write_report(args.out, steps, ok=False)
        return 1

    artifact_ok = MAINLINE_ARTIFACT.is_file()
    steps.append(
        {
            "name": "artifact_present",
            "ok": artifact_ok,
            "path": str(MAINLINE_ARTIFACT),
        }
    )
    if not artifact_ok:
        _write_report(args.out, steps, ok=False)
        return 1

    _write_report(args.out, steps, ok=True)
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "artifact": str(MAINLINE_ARTIFACT),
                "lens_json": str(LENS_JSON),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_report(path: Path, steps: list[dict[str, Any]], *, ok: bool) -> None:
    doc = {
        "schema": "sasang_unified_adapter_daily_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_allowed": False,
        "ok": ok,
        "steps": steps,
        "outputs": {
            "unified_artifact": "reports/sasang_dynamics_unified_v1_latest.json",
            "lens_input": "docs/final/artifacts/sasang_independent_lens_latest.json",
        },
        "reproduce": "py scripts/run_sasang_unified_adapter_daily_chain_v1.py",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
