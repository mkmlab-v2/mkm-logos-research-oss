#!/usr/bin/env python3
"""BigSet Tier-0 + Logos Studio fusion chain (HD delegation · tier_0).

bridge → citation_lock → conflict_surface → studio sidecar → adoptable 3-pack

Reproducible:
  py scripts/run_bigset_logos_fusion_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = sys.executable
BIGSET_CHAIN = ROOT / "scripts/run_bigset_ingest_spike_chain_v1.py"
STUDIO_SIDECAR = ROOT / "scripts/build_bigset_studio_conflict_sidecar_v1.py"
LOGOS_ADOPTABLE = ROOT / "scripts/run_logos_adoptable_spike_chain_v1.py"
OUT_REPORT = ROOT / "reports/bigset_logos_fusion_chain_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_logos_fusion_chain_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--auto-setup", action="store_true")
    ap.add_argument("--skip-bigset", action="store_true")
    ap.add_argument("--skip-adoptable", action="store_true")
    ap.add_argument(
        "--free-tier",
        action="store_true",
        help="apply OpenRouter :free / Ollama profile before live subprocesses",
    )
    ap.add_argument("--free-tier-mode", choices=["openrouter_free", "ollama", "azure"], default=None)
    args = ap.parse_args()

    nodes: list[dict[str, Any]] = []
    ok_all = True
    free_profile: dict[str, Any] | None = None
    child_env = None
    if args.free_tier:
        from scripts.bigset_free_tier_profile_v1 import (
            apply_profile_to_environ,
            profile_public_snapshot,
            resolve_profile,
        )

        mode = "ollama_local" if args.free_tier_mode == "ollama" else args.free_tier_mode
        if args.free_tier_mode == "azure":
            mode = "azure_openai"
        prof = resolve_profile(mode=mode)
        apply_profile_to_environ(prof)
        free_profile = profile_public_snapshot(prof)
        child_env = os.environ.copy()
        nodes.append(
            {
                "step": "free_tier_profile",
                "ok": True,
                "profile": free_profile,
            }
        )

    if not args.skip_bigset:
        cmd = [PY, str(BIGSET_CHAIN)]
        if args.live:
            cmd.append("--live")
        if args.auto_setup:
            cmd.append("--auto-setup")
        if args.free_tier:
            cmd.append("--free-tier")
        if args.free_tier_mode:
            cmd.extend(["--free-tier-mode", args.free_tier_mode])
        nodes.append(_run(cmd, env=child_env))
        if not nodes[-1]["ok"]:
            ok_all = False

    nodes.append(_run([PY, str(STUDIO_SIDECAR)]))
    if not nodes[-1]["ok"]:
        ok_all = False

    if not args.skip_adoptable:
        nodes.append(_run([PY, str(LOGOS_ADOPTABLE)]))
        if not nodes[-1]["ok"]:
            ok_all = False

    completion = {
        "schema": "bigset_logos_fusion_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "quality_ok": ok_all,
        "exit_code": 0 if ok_all else 1,
        "mode": "live" if args.live else "dry_run",
        "cost_tier": "tier_0" if args.free_tier else ("tier_15" if args.live else "tier_0"),
        "free_tier_profile": free_profile,
        "reproducible_command": "py scripts/run_bigset_logos_fusion_chain_v1.py"
        + (" --live --auto-setup --free-tier" if args.live and args.free_tier else ""),
        "nodes": nodes,
        "artifact_paths": {
            "bigset_ingest": "reports/bigset_ingest_spike_chain_v1_latest.json",
            "studio_sidecar": "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json",
            "studio_mirror": "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json",
            "logos_adoptable": "reports/logos_adoptable_spike_chain_v1_latest.json",
            "free_tier_profile": "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json",
        },
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ARTIFACT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "report": str(OUT_REPORT)}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
