#!/usr/bin/env python3
"""Chain: sidecar build → narrative path A/B bench → gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_chain_v1_latest.json"
AB = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    return cp.returncode, tail[-1] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-router", action="store_true", help="Faster smoke — flow/hop caps only")
    args = ap.parse_args()

    steps: list[dict] = []
    ok = True
    router_flag = ["--skip-router"] if args.skip_router else []

    for label, cmd in (
        ("sidecar_build", [sys.executable, "scripts/build_sasang_routing_sidecar_on_gematria_path_v1.py"]),
        (
            "narrative_ab",
            [sys.executable, "scripts/bench_sasang_routing_sidecar_narrative_path_ab_v1.py", *router_flag],
        ),
        ("ab_gate", [sys.executable, "scripts/check_sasang_routing_sidecar_narrative_path_ab_v1.py"]),
    ):
        code, tail = _run(cmd)
        steps.append({"step": label, "exit_code": code, "tail": tail})
        ok = ok and code == 0

    doc = {
        "schema": "sasang_routing_sidecar_narrative_path_ab_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "all_ok": ok,
        "send_gate": "HOLD",
        "research_only": True,
        "skip_router": args.skip_router,
        "artifacts": {
            "ab_report": str(AB.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
        "reproduce": "py scripts/run_sasang_routing_sidecar_narrative_path_ab_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
