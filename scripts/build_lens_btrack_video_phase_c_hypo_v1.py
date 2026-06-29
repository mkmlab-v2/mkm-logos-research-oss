#!/usr/bin/env python3
"""Phase C hypo orchestrator: prereq -> PIL baseline smoke or AnimateDiff/LTX dry-run report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/track_c_video_hook_samples_v1/phase_c_hypo_v1"

sys.path.insert(0, str(ROOT))
from scripts.video.lens_video_phase_c_tier_profiles_v1 import resolve_tier  # noqa: E402


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(args: list[str]) -> int:
    print(f"[phase-c-hypo] {' '.join(args)}", flush=True)
    return subprocess.run(args, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--engine",
        choices=("pil", "animatediff_hypo", "ltx_hypo"),
        default="pil",
        help="pil=existing ffmpeg bake; *_hypo=dry-run feasibility only",
    )
    ap.add_argument("--only-sasang", default="taeyang")
    ap.add_argument("--only-mode", default="idle")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-prereq", action="store_true")
    ap.add_argument(
        "--tier",
        choices=("smoke", "mq", "hq"),
        default="smoke",
        help="AnimateDiff bake profile (smoke|mq|hq); ignored for pil/ltx",
    )
    ap.add_argument(
        "--pil-hybrid",
        action="store_true",
        help="Blend PIL animated frames into AnimateDiff output (research C lane)",
    )
    ap.add_argument(
        "--pil-hybrid-blend",
        type=float,
        default=0.55,
        help="PIL weight when --pil-hybrid (recommended 0.55)",
    )
    args = ap.parse_args()

    if not args.skip_prereq:
        rc = _run([PY, "scripts/check_lens_video_phase_c_prereqs_v1.py"])
        if rc != 0 and args.engine == "pil":
            return rc

    report: dict[str, object] = {
        "schema": "lens_btrack_video_phase_c_hypo_report_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "generated_at_utc": _utc_now_z(),
        "engine": args.engine,
        "only_sasang": args.only_sasang,
        "only_mode": args.only_mode,
        "out_dir": str(args.out_dir),
        "status": "pending",
    }

    if args.engine == "ltx_hypo":
        report["status"] = "dry_run_hypo"
        report["note"] = "ltx_hypo: bake not wired; Track B research lane only."
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out = args.out_dir / "lens_btrack_video_phase_c_hypo_report_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[phase-c-hypo] WROTE {out}")
        return 0

    if args.engine == "animatediff_hypo":
        if args.dry_run:
            rc = _run(
                [
                    PY,
                    "scripts/video/animatediff_hypo_external_generator_v1.py",
                    "--sasang",
                    args.only_sasang,
                    "--mode",
                    args.only_mode,
                    "--out-webm",
                    str(args.out_dir / "lv_hp050_animatediff_hypo_dry.webm"),
                    "--dry-run",
                ]
            )
            report["status"] = "dry_run" if rc == 0 else "fail"
            report["animatediff_exit"] = rc
        else:
            tier = resolve_tier(args.tier)
            suffix = f"animatediff_{args.tier}"
            if args.pil_hybrid:
                suffix += "_pil_hybrid"
            stem = f"lv_hp050_{args.only_sasang}_{args.only_mode}_v1_{suffix}.webm"
            out_webm = args.out_dir / stem
            gen_report = args.out_dir / f"animatediff_{args.tier}_generator_v1_latest.json"
            cmd = [
                PY,
                "scripts/video/animatediff_hypo_external_generator_v1.py",
                "--sasang",
                args.only_sasang,
                "--mode",
                args.only_mode,
                "--out-webm",
                str(out_webm),
                "--num-frames",
                str(tier["num_frames"]),
                "--width",
                str(tier["width"]),
                "--height",
                str(tier["height"]),
                "--steps",
                str(tier["steps"]),
                "--fps",
                str(tier["fps"]),
                "--guidance",
                str(tier["guidance"]),
                "--bitrate-k",
                str(tier["bitrate_k"]),
                "--report-json",
                str(gen_report),
            ]
            if args.pil_hybrid:
                cmd.extend(["--pil-hybrid", "--pil-hybrid-blend", str(args.pil_hybrid_blend)])
            rc = _run(cmd)
            report["status"] = "ok" if rc == 0 else "fail"
            report["animatediff_exit"] = rc
            report["tier"] = args.tier
            report["tier_profile"] = tier
            report["pil_hybrid"] = bool(args.pil_hybrid)
            report["out_webm"] = str(out_webm)
            report["generator_report"] = str(gen_report)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out = args.out_dir / "lens_btrack_video_phase_c_hypo_report_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[phase-c-hypo] WROTE {out}")
        return 0 if report.get("status") in ("ok", "dry_run") else 1

    if args.dry_run:
        report["status"] = "dry_run"
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out = args.out_dir / "lens_btrack_video_phase_c_hypo_report_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[phase-c-hypo] WROTE {out}")
        return 0

    bake_args = [
        PY,
        "scripts/build_lens_btrack_video_loops_v1.py",
        "--out-dir",
        str(args.out_dir),
        "--only-sasang",
        args.only_sasang,
        "--only-mode",
        args.only_mode,
        "--seconds",
        "8",
    ]
    rc = _run(bake_args)
    report["status"] = "ok" if rc == 0 else "fail"
    report["bake_exit"] = rc
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / "lens_btrack_video_phase_c_hypo_report_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[phase-c-hypo] WROTE {out}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
