#!/usr/bin/env python3
"""Free audio layer for auditable cinematic PoC — ambient BGM, TTS, SFX via athena_editor."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
EDITOR = ROOT / "scripts" / "cinematic" / "athena_editor_v1.py"
DEFAULT_SCENARIO = ART / "cinematic_scenario_auditable_poc_v1.txt"

VARIANTS: dict[str, dict[str, Any]] = {
    "economy": {
        "workspace": ART / "cinematic_auditable_poc_v1",
        "output_name": "auditable_poc_master_economy_audio_latest.mp4",
        "report_json": ART / "auditable_cinematic_audio_mix_economy_latest.json",
    },
    "hybrid": {
        "workspace": ART / "cinematic_auditable_poc_hybrid_v1",
        "output_name": "auditable_poc_master_hybrid_audio_latest.mp4",
        "report_json": ART / "auditable_cinematic_audio_mix_hybrid_latest.json",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_variant(
    name: str,
    *,
    scenario: Path,
    shot_sec: int,
    max_shots: int,
    pro_audio: bool,
    no_narration: bool,
) -> dict[str, Any]:
    profile = VARIANTS[name]
    workspace = profile["workspace"]
    shots_dir = workspace / "shots"
    if not shots_dir.is_dir():
        raise RuntimeError(f"missing shots dir: {shots_dir}")

    s2_dir = workspace / "s2_audio_mix"
    output_name = str(profile["output_name"])
    report_json = profile["report_json"]

    cmd = [
        sys.executable,
        str(EDITOR),
        "--input-clips-dir",
        str(shots_dir),
        "--scenario-file",
        str(scenario),
        "--shot-sec",
        str(shot_sec),
        "--max-shots",
        str(max_shots),
        "--s2-input-dir",
        str(s2_dir),
        "--output-name",
        output_name,
        "--report-json",
        str(report_json),
        "--render-width",
        "1280",
        "--render-height",
        "720",
        "--promo-pack",
        "--skip-quality-gate",
        "--no-ducking",
        "--bgm-gain-db",
        "-6",
    ]
    if pro_audio:
        cmd.append("--pro-audio")
    if no_narration:
        cmd.append("--no-narration")

    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    summary: dict[str, Any] = {}
    if p.stdout.strip():
        try:
            summary = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            summary = {"raw_tail": p.stdout.strip()[-500:]}

    deliver = workspace / "deliverables" / output_name
    deliver.parent.mkdir(parents=True, exist_ok=True)
    final_mp4 = Path(summary.get("final_mp4") or (s2_dir / "output" / output_name))
    copied = False
    if final_mp4.is_file():
        shutil.copy2(final_mp4, deliver)
        copied = True

    ok = p.returncode == 0 and bool(summary.get("ok")) and copied
    return {
        "variant": name,
        "exit_code": p.returncode,
        "ok": ok,
        "cmd": " ".join(cmd),
        "summary": summary,
        "deliverable_mp4": str(deliver) if copied else None,
        "stderr_tail": (p.stderr or "")[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variant", choices=[*VARIANTS.keys(), "all"], default="all")
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--shot-sec", type=int, default=6)
    ap.add_argument("--max-shots", type=int, default=6)
    ap.add_argument("--pro-audio", action="store_true", help="LUFS normalize + duck mix (still $0 local)")
    ap.add_argument("--no-narration", action="store_true")
    ap.add_argument("--out-json", type=Path, default=ART / "auditable_cinematic_audio_mix_v1_latest.json")
    args = ap.parse_args()

    scenario = args.scenario_file if args.scenario_file.is_absolute() else (ROOT / args.scenario_file)
    names = list(VARIANTS) if args.variant == "all" else [args.variant]

    results: list[dict[str, Any]] = []
    for name in names:
        results.append(
            run_variant(
                name,
                scenario=scenario,
                shot_sec=args.shot_sec,
                max_shots=args.max_shots,
                pro_audio=args.pro_audio,
                no_narration=args.no_narration,
            )
        )

    ok = all(r.get("ok") for r in results)
    doc = {
        "schema": "auditable_cinematic_audio_mix_v1",
        "generated_at_utc": now_utc(),
        "ok": ok,
        "cost_usd": 0,
        "audio_stack": {
            "engine": "athena_editor_v1",
            "promo_pack": True,
            "bgm": "ambient_two_tone_pad",
            "sfx": "transition_shot_boundary_ticks",
            "narration": "ffmpeg_flite_tts" if not args.no_narration else "disabled",
            "pro_audio_lufs": args.pro_audio,
            "lens_music_gate": False,
            "quality_gate": "skipped_auditable_poc",
            "ducking": False,
            "bgm_gain_db": -6,
        },
        "variants": results,
        "reproduce_cmd": (
            "py scripts/cinematic/run_auditable_cinematic_audio_mix_v1.py"
            + (" --pro-audio" if args.pro_audio else "")
        ),
        "send_gate": "HOLD",
        "promotion": "infra_only",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out_json": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
