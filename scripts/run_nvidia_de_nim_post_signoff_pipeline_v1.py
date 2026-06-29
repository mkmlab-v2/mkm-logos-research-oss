#!/usr/bin/env python3
"""[HYPO] After commander anchor signoff: LUT refresh, eval, B2B, paste — no codec/ACTIVE."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_de_nim_post_signoff_pipeline_v1_latest.json"
SIGNOFF = ROOT / "reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"script": script, "args": extra or [], "exit_code": int(cp.returncode), "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--accept-all", action="store_true")
    ap.add_argument("--skip-dual-axis-push", action="store_true")
    ap.add_argument("--run-dual-axis-push", action="store_true", help="320-combo grid (slow)")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    signoff_args: list[str] = []
    if args.accept_all:
        signoff_args.append("--accept-all")

    if args.run_dual_axis_push and not args.skip_dual_axis_push:
        s = _run(
            "scripts/run_ng40_path_b_dual_axis_push_v1.py",
            ["--skip-promotion-packet"],
        )
        steps.append({"name": "path_b_dual_axis_push", **s})
        if s["exit_code"] != 0:
            rc = s["exit_code"]

    steps.append(_run("scripts/run_nvidia_de_nim_lut_staging_closure_v1.py"))
    steps.append(
        _run(
            "scripts/run_ng40_sequential_codec_product_chain_v1.py",
            ["--skip-path-b-sweep", "--skip-auto-ops"],
        )
    )
    steps.append(_run("scripts/run_ng40_b2b_product_export_chain_v1.py"))
    steps.append(
        _run(
            "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
            [
                "--path-b-knee-research-signoff",
                "--path-a-product-research-signoff",
                "--reviewer",
                "commander",
                "--note",
                "de_nim_post_signoff_pipeline",
            ],
        )
    )
    if not SIGNOFF.is_file():
        s0 = _run(
            "scripts/record_nvidia_de_nim_commander_anchor_signoff_v1.py",
            signoff_args,
        )
        steps.append({"name": "record_anchor_signoff", **s0})
        if s0["exit_code"] != 0:
            return s0["exit_code"]

    steps.append(
        _run(
            "scripts/record_nvidia_de_nim_commander_anchor_signoff_v1.py",
            ["--reapply-latest"],
        )
    )
    steps.append(_run("scripts/build_nvidia_hybrid_operator_paste_pack_v1.py"))
    steps.append(_run("scripts/build_hybrid_ai_lab_status_v1.py"))

    signoff_doc = json.loads(SIGNOFF.read_text(encoding="utf-8-sig")) if SIGNOFF.is_file() else {}
    doc = {
        "schema": "nvidia_de_nim_post_signoff_pipeline_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "anchor_signoff": signoff_doc,
        "codec_wired": False,
        "track_a_active_write": False,
        "steps": steps,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hard = any(s.get("exit_code", 0) != 0 for s in steps)
    print(json.dumps({"wrote": str(OUT), "rc": rc if rc else (1 if hard else 0)}, ensure_ascii=False))
    return rc if rc else (1 if hard else 0)


if __name__ == "__main__":
    raise SystemExit(main())
