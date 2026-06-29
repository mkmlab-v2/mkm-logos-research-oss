#!/usr/bin/env python3
"""Minimum auditable cinematic PoC — economy default: reuse local, no Veo API unless allowed.

Hero shots (default 1-3): reuse workspace/donor clips, else animatic if spend blocked.
Tail shots: local ffmpeg animatic. Veo API only with --allow-veo-spend (+ optional --veo-smoke).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCENARIO = ART / "cinematic_scenario_auditable_poc_v1.txt"
DEFAULT_WORKSPACE = ART / "cinematic_auditable_poc_v1"
DEFAULT_REPORT = ART / "auditable_cinematic_poc_v1_latest.json"
DONOR_SCENARIO = ART / "cinematic_scenario_sample_v1.txt"
REF_DONOR = ART / "cinematic_consistency_pack_v1" / "references"
CLIP_DONOR = ART / "cinematic_consistency_pack_v1"

VARIANT_PROFILES: dict[str, dict[str, Any]] = {
    "economy": {
        "workspace": ART / "cinematic_auditable_poc_v1",
        "report_json": ART / "auditable_cinematic_poc_economy_latest.json",
        "master_name": "auditable_poc_master_economy_latest.mp4",
        "hero_animatic_only": True,
        "scenario_aligned": True,
        "label": "scenario_aligned_animatic",
    },
    "hybrid": {
        "workspace": ART / "cinematic_auditable_poc_hybrid_v1",
        "report_json": ART / "auditable_cinematic_poc_hybrid_latest.json",
        "master_name": "auditable_poc_master_hybrid_latest.mp4",
        "hero_animatic_only": False,
        "scenario_aligned": False,
        "label": "donor_veo_reuse_infra_only",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_py(script: Path, args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(script), *args]
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "cmd": " ".join(cmd),
        "exit_code": p.returncode,
        "stdout_tail": (p.stdout or "")[-2000:],
        "stderr_tail": (p.stderr or "")[-2000:],
    }


def ensure_subject_refs(workspace: Path) -> list[str]:
    refs = workspace / "references"
    refs.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if REF_DONOR.is_dir():
        for name in ("subject_kor_01.png", "subject_kor_02.png", "subject_kor_03.png"):
            src = REF_DONOR / name
            if src.is_file() and src.stat().st_size > 0:
                dst = refs / name
                if not dst.exists() or dst.stat().st_size == 0:
                    shutil.copy2(src, dst)
                copied.append(str(dst))
    return copied


def build_animatic_clip(
    workspace: Path,
    idx: int,
    line: str,
    shot_sec: int,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
) -> dict[str, Any]:
    shot_dir = workspace / "shots" / f"shot_{idx:02d}"
    shot_dir.mkdir(parents=True, exist_ok=True)
    clip = shot_dir / "clip.mp4"
    palette = ("#1f2937", "#1e3a8a", "#0f766e", "#334155", "#4c1d95", "#713f12")
    bg = palette[(idx - 1) % len(palette)]
    safe = line[:40].replace("'", "").replace(":", " ")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={bg}:s={width}x{height}:d={shot_sec}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={440 + idx * 15}:sample_rate=48000:duration={shot_sec}",
        "-vf",
        f"drawtext=text='{safe}':fontsize=22:fontcolor=white:x=(w-text_w)/2:y=h-60",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(clip),
    ]
    p = subprocess.run(cmd, text=True, capture_output=True)
    row = {
        "shot": idx,
        "clip": str(clip),
        "mode": "animatic_local_ffmpeg",
        "exit_code": p.returncode,
        "ok": p.returncode == 0 and clip.is_file(),
    }
    if p.returncode != 0:
        raise RuntimeError(f"animatic shot_{idx:02d} failed: {p.stderr[-800:]}")
    return row


def clip_usable(path: Path, min_bytes: int = 50_000) -> bool:
    return path.is_file() and path.stat().st_size >= min_bytes


def ensure_hero_clips(
    workspace: Path,
    lines: list[str],
    veo_shots: int,
    shot_sec: int,
    *,
    veo_overwrite: bool,
    hero_animatic_only: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i in range(1, veo_shots + 1):
        shot_dir = workspace / "shots" / f"shot_{i:02d}"
        shot_dir.mkdir(parents=True, exist_ok=True)
        dst = shot_dir / "clip.mp4"
        if hero_animatic_only:
            line = lines[i - 1] if i - 1 < len(lines) else f"Hero shot {i}"
            row = build_animatic_clip(workspace, i, line, shot_sec)
            row["mode"] = "animatic_hero_economy"
            results.append(row)
            continue
        if clip_usable(dst) and not veo_overwrite:
            results.append({"shot": i, "mode": "reuse_workspace", "clip": str(dst), "ok": True})
            continue
        donor = CLIP_DONOR / "shots" / f"shot_{i:02d}" / "clip.mp4"
        if clip_usable(donor) and not veo_overwrite:
            shutil.copy2(donor, dst)
            results.append(
                {
                    "shot": i,
                    "mode": "reuse_donor_pack",
                    "clip": str(dst),
                    "donor": str(donor),
                    "ok": True,
                    "note": "scenario_mismatch_possible",
                }
            )
            continue
        line = lines[i - 1] if i - 1 < len(lines) else f"Hero shot {i}"
        row = build_animatic_clip(workspace, i, line, shot_sec)
        row["mode"] = "animatic_hero_fallback"
        results.append(row)
    return results


def concat_shots(workspace: Path, shot_count: int, out_path: Path) -> None:
    list_path = workspace / "deliverables" / "_concat_list.txt"
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i in range(1, shot_count + 1):
        clip = workspace / "shots" / f"shot_{i:02d}" / "clip.mp4"
        if not clip.is_file():
            raise RuntimeError(f"missing clip for concat: {clip}")
        lines.append(f"file '{clip.as_posix()}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(out_path),
    ]
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"concat failed: {p.stderr[-800:]}")


def load_gate_decision(gate_stdout: str) -> dict[str, Any]:
    try:
        outer = json.loads(gate_stdout.strip().splitlines()[-1])
        path = Path(outer["out_json"])
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc.get("decision") or {}
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--shot-count", type=int, default=6)
    ap.add_argument("--veo-shots", type=int, default=3)
    ap.add_argument("--shot-sec", type=int, default=6)
    ap.add_argument("--allow-veo-spend", action="store_true")
    ap.add_argument("--veo-smoke", action="store_true", help="Cap paid Veo to 1 shot when spend allowed")
    ap.add_argument("--veo-overwrite", action="store_true")
    ap.add_argument(
        "--hero-animatic-only",
        action="store_true",
        help="Free scenario-aligned hero shots (skip Veo/donor reuse)",
    )
    ap.add_argument("--skip-veo", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--report-json", type=Path, default=None)
    ap.add_argument(
        "--variant",
        choices=sorted(VARIANT_PROFILES),
        default="",
        help="economy=animatic hero; hybrid=free donor Veo reuse (scenario mismatch OK)",
    )
    ap.add_argument("--master-name", type=str, default="")
    args = ap.parse_args()

    profile: dict[str, Any] = {}
    if args.variant:
        profile = dict(VARIANT_PROFILES[args.variant])
        args.workspace_root = profile["workspace"]
        args.hero_animatic_only = bool(profile["hero_animatic_only"])
        if not args.master_name:
            args.master_name = str(profile["master_name"])
        if args.report_json is None:
            args.report_json = profile["report_json"]
    if args.report_json is None:
        args.report_json = DEFAULT_REPORT
    if not args.master_name:
        args.master_name = "auditable_poc_master_latest.mp4"

    allow_spend = args.allow_veo_spend or os.environ.get("MKM_CINEMATIC_ALLOW_VEO_SPEND", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    workspace = args.workspace_root if args.workspace_root.is_absolute() else (ROOT / args.workspace_root)
    scenario = args.scenario_file if args.scenario_file.is_absolute() else (ROOT / args.scenario_file)
    if not scenario.is_file():
        raise RuntimeError(f"scenario not found: {scenario}")

    lines = [x.strip() for x in scenario.read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(lines) < args.shot_count:
        raise RuntimeError(f"scenario needs {args.shot_count} lines, got {len(lines)}")

    steps: list[dict[str, Any]] = []
    gate_args = [
        "--workspace-root",
        str(workspace),
        "--veo-shots",
        str(args.veo_shots),
    ]
    if allow_spend:
        gate_args.append("--allow-veo-spend")
    if args.veo_smoke:
        gate_args.append("--veo-smoke")
    if args.veo_overwrite:
        gate_args.append("--veo-overwrite")
    gate_step = run_py(ROOT / "scripts/cinematic/check_cinematic_veo_spend_gate_v1.py", gate_args)
    steps.append(gate_step)
    decision = load_gate_decision(gate_step.get("stdout_tail", ""))

    steps.append(
        run_py(
            ROOT / "scripts/cinematic/bootstrap_consistency_pack_v1.py",
            ["--root-dir", str(workspace), "--shot-count", str(args.shot_count), "--shot-sec", str(args.shot_sec)],
        )
    )
    steps.append(
        run_py(
            ROOT / "scripts/cinematic/director_agent_v1.py",
            [
                "--scenario-file",
                str(scenario),
                "--target-shots",
                str(args.shot_count),
                "--shot-sec",
                str(args.shot_sec),
                "--concept",
                "companion-human",
                "--workspace-root",
                str(workspace),
                "--out-json",
                str(ART / "director_agent_v1_shot_plan_auditable_poc_latest.json"),
            ],
        )
    )

    refs = ensure_subject_refs(workspace)
    hero: list[dict[str, Any]] = []
    veo_results: dict[str, Any] = {"api_called": False, "spend_risk": "none"}

    run_veo_api = bool(decision.get("allow_veo_api")) and not args.skip_veo
    if run_veo_api:
        end_shot = int(decision.get("veo_shots_to_generate") or args.veo_shots)
        if args.veo_smoke:
            end_shot = min(1, end_shot)
        veo_args = [
            "--shot-plan-json",
            str(ART / "director_agent_v1_shot_plan_auditable_poc_latest.json"),
            "--start-shot",
            "1",
            "--end-shot",
            str(end_shot),
            "--use-last-frame",
            "--force-duration-sec",
            str(args.shot_sec),
            "--overwrite",
        ]
        veo_step = run_py(ROOT / "scripts/cinematic/generate_veo_consistency_batch_v1.py", veo_args)
        steps.append(veo_step)
        veo_results = {
            "api_called": True,
            "exit_code": veo_step["exit_code"],
            "shots_generated": end_shot,
            "billing": "vertex_ai_mkm-lab-agi-2025",
            "spend_risk": "vertex_billed_maybe_credit_offset",
        }
        hero = ensure_hero_clips(
            workspace,
            lines,
            args.veo_shots,
            args.shot_sec,
            veo_overwrite=False,
            hero_animatic_only=args.hero_animatic_only,
        )
    else:
        hero = ensure_hero_clips(
            workspace,
            lines,
            args.veo_shots,
            args.shot_sec,
            veo_overwrite=args.veo_overwrite,
            hero_animatic_only=args.hero_animatic_only,
        )
        veo_results = {
            "api_called": False,
            "mode": decision.get("mode", "economy_no_api"),
            "spend_risk": "none",
        }

    tail_lines = lines[args.veo_shots : args.shot_count]
    animatic_tail: list[dict[str, Any]] = []
    for offset, line in enumerate(tail_lines, start=0):
        idx = args.veo_shots + 1 + offset
        animatic_tail.append(build_animatic_clip(workspace, idx, line, args.shot_sec))

    deliver = workspace / "deliverables" / args.master_name
    concat_shots(workspace, args.shot_count, deliver)

    clip_check = run_py(
        ROOT / "scripts/cinematic/check_consistency_clip_inputs_v1.py",
        [
            "--root-dir",
            str(workspace),
            "--shot-count",
            str(args.shot_count),
            "--target-shot-sec",
            str(float(args.shot_sec)),
            "--duration-tolerance-sec",
            "2.5",
        ],
    )
    steps.append(clip_check)

    ok = all(s.get("exit_code", 1) == 0 for s in steps) and all(h.get("ok") for h in hero + animatic_tail)
    variant_label = str(profile.get("label") or ("economy" if args.hero_animatic_only else "hybrid_or_mixed"))
    scenario_aligned = bool(profile.get("scenario_aligned", args.hero_animatic_only))
    report: dict[str, Any] = {
        "schema": "auditable_cinematic_poc_v1",
        "generated_at_utc": now_utc(),
        "ok": ok,
        "variant": args.variant or None,
        "variant_label": variant_label,
        "scenario_aligned": scenario_aligned,
        "donor_scenario_file": str(DONOR_SCENARIO) if not scenario_aligned else None,
        "economy_mode": True,
        "scenario_file": str(scenario),
        "workspace_root": str(workspace),
        "shot_count": args.shot_count,
        "veo_shots": args.veo_shots,
        "allow_veo_spend": allow_spend,
        "cost_gate": decision,
        "subject_refs_copied": refs,
        "outputs": {
            "master_mp4": str(deliver),
            "shot_plan_json": str(ART / "director_agent_v1_shot_plan_auditable_poc_latest.json"),
            "spend_gate_json": str(ART / "cinematic_veo_spend_gate_latest.json"),
        },
        "hero_shots": hero,
        "animatic_tail": animatic_tail,
        "veo": veo_results,
        "steps": steps,
        "reproduce_cmd": (
            "py scripts/cinematic/run_auditable_cinematic_poc_v1.py"
            + (f" --variant {args.variant}" if args.variant else "")
            + ("" if args.variant else (" --hero-animatic-only" if args.hero_animatic_only else ""))
        ),
        "send_gate": "HOLD",
        "promotion": "infra_only",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "veo_api_called": veo_results.get("api_called"),
                "cost_gate_mode": decision.get("mode"),
                "report_json": str(args.report_json),
                "master_mp4": str(deliver),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
