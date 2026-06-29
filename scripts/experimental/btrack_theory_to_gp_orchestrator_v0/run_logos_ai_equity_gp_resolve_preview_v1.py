#!/usr/bin/env python3
"""Batch preview (and optional apply) for Logos AI equity general_prophecy chain."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "reports" / "general_prophecy_logos_ai_equity_resolve_batch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str]) -> dict:
    cmd = [sys.executable, str(PKG / script), *extra]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    payload = {}
    if cp.stdout.strip():
        try:
            payload = json.loads(cp.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            payload = {"raw_stdout": cp.stdout.strip()[-500:]}
    return {
        "script": script,
        "exit_code": cp.returncode,
        "payload": payload,
        "stderr_tail": (cp.stderr or "")[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-apply", action="store_true")
    ap.add_argument("--run-brier", action="store_true")
    ns = ap.parse_args()

    flags: list[str] = []
    if ns.apply:
        flags.append("--apply")
    if ns.force_apply:
        flags.append("--force-apply")
    if ns.run_brier:
        flags.append("--run-brier")

    steps = [
        _run("resolve_sox_gp_v1.py", flags),
        _run("resolve_nvda_gp_v1.py", flags),
        _run("resolve_qqq_gp_v1.py", flags),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)
    body = {
        "schema": "general_prophecy_logos_ai_equity_resolve_batch_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "apply_requested": ns.apply or ns.force_apply,
        "steps": steps,
        "ok": ok,
    }
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(ns.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
