#!/usr/bin/env python3
"""Harness pipeline: read_ssot → intent_router → (optional) BigSet Azure live fusion.

Default: dry-run fusion after routing. Pass --live for BigSet populate.

Reproducible:
  py scripts/run_mkm_bigset_harness_chain_v1.py --query "Benei HaElohim tier-0"
  py scripts/run_mkm_bigset_harness_chain_v1.py --query "..." --live --auto-setup
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
READ_SSOT = ROOT / "scripts/invoke_mkm_harness_read_ssot_v1.py"
ROUTER = ROOT / "scripts/mkm_intent_router_local_v1.py"
FUSION = ROOT / "scripts/run_bigset_logos_fusion_chain_v1.py"
OUT = ROOT / "reports/mkm_bigset_harness_chain_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--auto-setup", action="store_true")
    ap.add_argument("--skip-fusion", action="store_true")
    args = ap.parse_args()

    nodes: list[dict[str, Any]] = []
    nodes.append(_run([PY, str(READ_SSOT)]))
    nodes.append(_run([PY, str(ROUTER), "--query", args.query]))
    route = "hold_research"
    if nodes[-1]["ok"]:
        art = ROOT / "docs/final/artifacts/mkm_intent_router_local_v1_latest.json"
        if art.is_file():
            route = json.loads(art.read_text(encoding="utf-8")).get("route", route)

    ok_all = all(n.get("ok") for n in nodes)
    if route in {"azure_bigset", "bigset_ingest"} and not args.skip_fusion:
        cmd = [PY, str(FUSION), "--free-tier"]
        if route == "azure_bigset":
            cmd.extend(["--free-tier-mode", "azure"])
        elif route == "bigset_ingest":
            import os
            from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet

            load_dotenv_quiet()
            prof = (os.environ.get("BIGSET_LLM_PROFILE") or "openrouter_free").strip().lower()
            if prof in {"ollama", "local", "ollama_local"}:
                cmd.extend(["--free-tier-mode", "ollama"])
            elif prof in {"azure", "azure_openai", "azure_first"}:
                cmd.extend(["--free-tier-mode", "azure"])
        if args.live:
            cmd.append("--live")
        if args.auto_setup:
            cmd.append("--auto-setup")
        nodes.append(_run(cmd))
        ok_all = ok_all and nodes[-1]["ok"]
    elif route == "local_math":
        nodes.append({"step": "fusion_skipped", "ok": True, "reason": "local_math_route"})

    doc = {
        "schema": "mkm_bigset_harness_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok_all,
        "route": route,
        "mode": "live" if args.live else "dry_run",
        "nodes": nodes,
        "reproduce": "py scripts/run_mkm_bigset_harness_chain_v1.py --query \"...\"",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "route": route, "report": str(OUT)}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
