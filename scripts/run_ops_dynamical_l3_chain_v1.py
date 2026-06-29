#!/usr/bin/env python3
"""Ops dynamical L3 chain — ensure benches + cross-fixture eval [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ops_dynamical_l3_chain_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full L3 cross-fixture chain")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    steps: list[dict[str, Any]] = []

    for label, cmd in (
        ("bench", [sys.executable, str(ROOT / "scripts/run_ops_dynamical_bench_v1.py"), "--no-append-jsonl"]),
        (
            "l3_eval",
            [
                sys.executable,
                str(ROOT / "scripts/run_ops_dynamical_l3_cross_fixture_eval_v1.py"),
                "--ensure-artifacts",
            ],
        ),
    ):
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        steps.append({"step": label, "ok": proc.returncode == 0, "exit_code": proc.returncode, "tail": tail[-1] if tail else ""})

    ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "ops_dynamical_l3_chain_v1",
        "version": "1.0.0",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L3_cross_domain",
        "steps": steps,
        "ok": ok,
        "reproduce": "py scripts/run_ops_dynamical_l3_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
