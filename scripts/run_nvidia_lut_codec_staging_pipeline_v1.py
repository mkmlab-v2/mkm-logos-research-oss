#!/usr/bin/env python3
"""[HYPO] Next step: full codec bench + staging review after DE/NIM anchor signoff."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_lut_codec_staging_pipeline_v1_latest.json"
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
    ap.add_argument(
        "--skip-dual-axis-push",
        action="store_true",
        help="Skip 320-combo latent sweep inside codec split",
    )
    args = ap.parse_args()

    if not SIGNOFF.is_file():
        print(json.dumps({"error": "missing_anchor_signoff"}))
        return 2

    steps: list[dict[str, Any]] = []
    rc = 0

    steps.append(
        _run(
            "scripts/record_nvidia_de_nim_commander_anchor_signoff_v1.py",
            ["--reapply-latest"],
        )
    )
    codec_args: list[str] = []
    if args.skip_dual_axis_push:
        codec_args.append("--skip-path-b-sweep")
    s_codec = _run("scripts/run_ng40_codec_bench_split_chain_v1.py", codec_args)
    steps.append({"name": "codec_bench_split", **s_codec})
    if s_codec["exit_code"] != 0:
        rc = s_codec["exit_code"]

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
                "lut_codec_staging_pipeline",
            ],
        )
    )
    steps.append(_run("scripts/build_nvidia_hybrid_operator_paste_pack_v1.py"))
    steps.append(_run("scripts/build_hybrid_ai_lab_status_v1.py"))

    review = {}
    rp = ROOT / "reports/nvidia_lut_codec_staging_review_v1_latest.json"
    if rp.is_file():
        review = json.loads(rp.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "nvidia_lut_codec_staging_pipeline_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "codec_wired": False,
        "track_a_active_write": False,
        "staging_review": review.get("staging_verdict"),
        "steps": steps,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hard = any(
        s.get("exit_code", 0) != 0
        for s in steps
        if s.get("name") == "codec_bench_split"
    )
    print(json.dumps({"wrote": str(OUT), "rc": rc if rc else (1 if hard else 0)}, ensure_ascii=False))
    return rc if rc else (1 if hard else 0)


if __name__ == "__main__":
    raise SystemExit(main())
