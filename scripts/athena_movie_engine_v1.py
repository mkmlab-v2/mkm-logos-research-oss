#!/usr/bin/env python3
"""Athena Movie Engine v1 (MVP)

Google-credit-first orchestration:
1) Scenario planning with Gemini (Vertex preferred)
2) Whisper smart-cut prep (optional)
3) FFmpeg render plan handoff (manual/integration point)
4) Quality gate execution
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
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_PROFILE = ART / "athena_movie_engine_profile_google_cost_v1.json"
DEFAULT_PLAN_OUT = ART / "athena_movie_engine_plan_latest.json"
DEFAULT_SCRIPT_OUT = ART / "athena_movie_engine_narration_latest.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_py(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], cwd=str(ROOT), text=True, capture_output=True)


def build_prompt(goal: str, target_sec: int) -> str:
    return (
        "한국어 발표 영상용 제작 계획을 작성해줘.\n"
        f"목표: {goal}\n"
        f"총 길이: {target_sec}초\n"
        "출력 형식:\n"
        "1) 8초 단위 클립 리스트\n"
        "2) 각 클립 내레이션 1문장\n"
        "3) 화면 자막 1문장\n"
        "4) 전환 지시 1줄\n"
        "필수 키워드: Stage3 PASS, WATCH/HOLD, 로컬 기준선, 타깃 보드 실측 전환\n"
        "과장 표현 금지."
    )


def call_gemini_plan(prompt: str, model: str) -> dict[str, Any]:
    script = ROOT / "scripts" / "check_google_genai_readiness_v1.py"
    # lightweight call via smoke-vertex; response preview used as seed text
    proc = run_py(script, ["smoke-vertex", "--model", model, "--prompt", prompt])
    if proc.returncode != 0:
        return {
            "status": "FALLBACK",
            "reason": "vertex_call_failed",
            "stderr": proc.stderr.strip(),
            "text": "",
        }
    text = proc.stdout.strip()
    return {"status": "OK", "text": text}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goal", default="LG HS 발표용 60~90초 시네마틱 요약 영상")
    ap.add_argument("--target-sec", type=int, default=64)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN_OUT)
    ap.add_argument("--script-out", type=Path, default=DEFAULT_SCRIPT_OUT)
    ap.add_argument("--input-video", type=Path, default=None, help="Optional source video for smart cut")
    ap.add_argument("--run-smart-cut", action="store_true")
    ap.add_argument("--run-s2-render", action="store_true", help="Run one-click S2 preset v2 renderer")
    ap.add_argument("--s2-input-dir", type=Path, default=None, help="Folder following S2 preset convention")
    ap.add_argument("--s2-render-dry-run", action="store_true")
    ap.add_argument(
        "--audio-profile-json",
        type=Path,
        default=None,
        help="Optional: passed to render_s2_preset_v2 when --run-s2-render (duck/mix / full profile).",
    )
    ap.add_argument(
        "--video-profile-json",
        type=Path,
        default=None,
        help="Optional: passed to render_s2_preset_v2 when --run-s2-render (lut_cube from JSON).",
    )
    ap.add_argument("--run-gate-on-video", type=Path, default=None, help="Run quality gate on rendered video")
    args = ap.parse_args()

    profile = json.loads(args.profile_json.read_text(encoding="utf-8"))
    gemini_model = profile.get("gemini", {}).get("model_planning", "gemini-2.5-flash")
    prompt = build_prompt(args.goal, args.target_sec)
    plan_seed = call_gemini_plan(prompt, gemini_model)

    smart_cut = {"executed": False}
    if args.run_smart_cut and args.input_video:
        cut_script = ROOT / "scripts" / "run_s2_live_edit_whisper_cut_v1.py"
        cut_proc = run_py(cut_script, ["--input-video", str(args.input_video)])
        smart_cut = {
            "executed": True,
            "returncode": cut_proc.returncode,
            "stdout": cut_proc.stdout.strip(),
            "stderr": cut_proc.stderr.strip(),
        }

    s2_render: dict[str, Any] = {"executed": False}
    if args.run_s2_render and args.s2_input_dir:
        s2_script = ROOT / "scripts" / "render_s2_preset_v2.py"
        s2_args = ["--input-dir", str(args.s2_input_dir)]
        if args.s2_render_dry_run:
            s2_args.append("--dry-run")
        if args.audio_profile_json is not None:
            aj = args.audio_profile_json
            apath = aj if aj.is_absolute() else (ROOT / aj)
            if apath.is_file():
                s2_args += ["--audio-profile-json", str(apath)]
        if args.video_profile_json is not None:
            vj = args.video_profile_json
            vpath = vj if vj.is_absolute() else (ROOT / vj)
            if vpath.is_file():
                s2_args += ["--video-profile-json", str(vpath)]
        s2_proc = run_py(s2_script, s2_args)
        s2_render = {
            "executed": True,
            "returncode": s2_proc.returncode,
            "stdout": s2_proc.stdout.strip(),
            "stderr": s2_proc.stderr.strip(),
        }

    gate_result: dict[str, Any] = {"executed": False}
    if args.run_gate_on_video:
        gate_script = ROOT / "scripts" / "check_movie_render_gate_v1.py"
        gate_proc = run_py(
            gate_script,
            [
                "--video",
                str(args.run_gate_on_video),
                "--script-text",
                str(args.script_out),
            ],
        )
        gate_result = {
            "executed": True,
            "returncode": gate_proc.returncode,
            "stdout": gate_proc.stdout.strip(),
            "stderr": gate_proc.stderr.strip(),
        }

    plan_doc = {
        "schema": "athena_movie_engine_plan_v1",
        "generated_at_utc": now_utc(),
        "profile_json": str(args.profile_json),
        "goal": args.goal,
        "target_sec": args.target_sec,
        "billing_strategy": "vertex_first_local_second_optional_paid_last",
        "stages": {
            "scenario_planning": plan_seed,
            "smart_cut": smart_cut,
            "s2_preset_render": s2_render,
            "quality_gate": gate_result,
        },
        "notes": [
            "This MVP keeps external paid APIs optional and disabled by profile.",
            "Final render orchestration should remain ffmpeg/local for cost efficiency.",
        ],
    }
    args.plan_out.parent.mkdir(parents=True, exist_ok=True)
    args.script_out.parent.mkdir(parents=True, exist_ok=True)
    args.plan_out.write_text(json.dumps(plan_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Save a minimal narration seed for downstream editing.
    narration = (
        "# Athena Movie Engine Narration Seed\n\n"
        f"- goal: {args.goal}\n"
        f"- target_sec: {args.target_sec}\n\n"
        "## Mandatory keywords\n\n"
        "- Stage3 PASS\n"
        "- WATCH/HOLD\n"
        "- 로컬 기준선\n"
        "- 타깃 보드 실측 전환\n"
    )
    args.script_out.write_text(narration, encoding="utf-8")

    print(json.dumps({"ok": True, "plan_out": str(args.plan_out), "script_out": str(args.script_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
