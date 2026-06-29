#!/usr/bin/env python3
"""[HYPO] After staging review GO: confirm product-lane wire + refresh product artifacts."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_lut_codec_staging_wire_pipeline_v1_latest.json"


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
    ap.add_argument("--hold", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    hold_args = ["--hold"] if args.hold else []
    s0 = _run("scripts/record_nvidia_lut_codec_staging_wire_confirm_v1.py", hold_args)
    steps.append({"name": "wire_confirm", **s0})
    if s0["exit_code"] != 0:
        OUT.write_text(
            json.dumps(
                {"schema": "nvidia_lut_codec_staging_wire_pipeline_v1", "steps": steps},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return s0["exit_code"]

    if not args.hold:
        steps.append(
            _run(
                "scripts/build_ng40_salience_hook_from_nav_frame_v1.py",
                ["--mark-wired"],
            )
        )
        steps.append(
            _run(
                "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
                ["--keep-ratio", "0.88"],
            )
        )
        steps.append(
            _run(
                "scripts/run_ng40_path_a_product_signoff_chain_v1.py",
                ["--skip-auto-ops"],
            )
        )
        steps.append(_run("scripts/run_ng40_b2b_product_export_chain_v1.py"))
        steps.append(_run("scripts/build_nvidia_lut_codec_staging_review_v1.py"))
        steps.append(
            _run(
                "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
                [
                    "--path-b-knee-research-signoff",
                    "--path-a-product-research-signoff",
                    "--reviewer",
                    "commander",
                    "--note",
                    "lut_codec_staging_wire_confirmed",
                ],
            )
        )
    steps.append(_run("scripts/build_nvidia_hybrid_operator_paste_pack_v1.py"))
    steps.append(_run("scripts/build_hybrid_ai_lab_status_v1.py"))

    doc = {
        "schema": "nvidia_lut_codec_staging_wire_pipeline_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hold": args.hold,
        "steps": steps,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hard = any(s.get("exit_code", 0) != 0 for s in steps)
    print(json.dumps({"wrote": str(OUT), "rc": 1 if hard else 0}, ensure_ascii=False))
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
