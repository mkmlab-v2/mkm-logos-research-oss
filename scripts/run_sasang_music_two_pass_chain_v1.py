#!/usr/bin/env python3
"""
Two-pass sasang music conditioning smoke (B-track [HYPO]).

Pass 1: seed -> conditioning -> external gen -> gate -> feedback sidecar
Pass 2: apply feedback patch -> patched conditioning -> external gen -> gate

Does not auto-promote Track A or mutate the seed file.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print(json.dumps({"step": cmd[1] if len(cmd) > 1 else cmd[0], "cmd": cmd}, ensure_ascii=False), flush=True)
    return subprocess.run(cmd, cwd=str(cwd or ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Sasang music two-pass conditioning chain smoke.")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=Path("workspace/audio_raw_economy/_two_pass_smoke"))
    ap.add_argument("--gate-track", choices=("A", "B"), default="B")
    ap.add_argument("--skip-pass1", action="store_true", help="Reuse pass1 artifacts under output-dir/pass1.")
    ap.add_argument("--pass1-feedback-json", type=Path, default=None, help="Use existing feedback instead of pass1 run.")
    ap.add_argument("--pass1-conditioning-json", type=Path, default=None)
    ap.add_argument("--dry-run-plan", action="store_true")
    args = ap.parse_args()

    seed_abs = args.seed_json.resolve()
    if not seed_abs.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    out_root = args.output_dir.resolve()
    pass1_dir = out_root / "pass1"
    pass2_dir = out_root / "pass2"
    pass1_cond = pass1_dir / "conditioning_pass1.json"
    pass2_cond = pass2_dir / "conditioning_pass2.json"

    external = (os.environ.get("MKM_AUDIO_EXTERNAL_SCRIPT") or "").strip()
    if not external and not args.dry_run_plan:
        print(json.dumps({"ok": False, "error": "MKM_AUDIO_EXTERNAL_SCRIPT required"}))
        return 4

    plan = {
        "pass1": {
            "build_conditioning": str(pass1_cond),
            "batch_dir": str(pass1_dir),
        },
        "pass2": {
            "apply_feedback": str(pass2_cond),
            "batch_dir": str(pass2_dir),
        },
    }
    if args.dry_run_plan:
        print(json.dumps({"ok": True, "dry_run_plan": plan}, indent=2, ensure_ascii=False))
        return 0

    if args.pass1_feedback_json and args.pass1_feedback_json.is_file():
        feedback_path = args.pass1_feedback_json.resolve()
        if args.pass1_conditioning_json and args.pass1_conditioning_json.is_file():
            pass1_cond = args.pass1_conditioning_json.resolve()
        elif not pass1_cond.is_file():
            print(json.dumps({"ok": False, "error": "pass1-conditioning-json required with external feedback"}))
            return 2
    elif args.skip_pass1:
        feedback_candidates = sorted(pass1_dir.glob("*.conditioning_feedback.json"))
        if not feedback_candidates or not pass1_cond.is_file():
            print(json.dumps({"ok": False, "error": "pass1 artifacts missing; run without --skip-pass1"}))
            return 2
        feedback_path = feedback_candidates[0]
    else:
        pass1_dir.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts/build_sasang_music_conditioning_from_seed_v1.py"),
                "--seed-json",
                str(seed_abs),
                "--out-json",
                str(pass1_cond),
            ]
        )
        if rc != 0:
            return rc

        os.environ["MKM_AUDIO_CONDITIONING_JSON"] = str(pass1_cond)
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts/audio/run_bgm_generation_batch.py"),
                "--seed-json",
                str(seed_abs),
                "--emit",
                "external",
                "--count",
                "1",
                "--output-dir",
                str(pass1_dir),
                "--run-gate",
                "--gate-track",
                args.gate_track,
            ]
        )
        if rc != 0:
            return rc

        feedback_candidates = sorted(pass1_dir.glob("*.conditioning_feedback.json"))
        if not feedback_candidates:
            print(json.dumps({"ok": False, "error": "pass1 feedback sidecar missing"}))
            return 5
        feedback_path = feedback_candidates[0]

    pass2_dir.mkdir(parents=True, exist_ok=True)
    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/apply_conditioning_feedback_patch_v1.py"),
            "--conditioning-json",
            str(pass1_cond),
            "--feedback-json",
            str(feedback_path),
            "--out-json",
            str(pass2_cond),
        ]
    )
    if rc != 0:
        return rc

    os.environ["MKM_AUDIO_CONDITIONING_JSON"] = str(pass2_cond)
    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/run_bgm_generation_batch.py"),
            "--seed-json",
            str(seed_abs),
            "--emit",
            "external",
            "--count",
            "1",
            "--output-dir",
            str(pass2_dir),
            "--run-gate",
            "--gate-track",
            args.gate_track,
        ]
    )
    if rc != 0:
        return rc

    summary = {
        "ok": True,
        "pass1_conditioning": str(pass1_cond),
        "pass1_feedback": str(feedback_path),
        "pass2_conditioning": str(pass2_cond),
        "pass2_dir": str(pass2_dir),
    }
    (out_root / "_two_pass_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
