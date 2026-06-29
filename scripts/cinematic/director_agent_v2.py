#!/usr/bin/env python3
"""Build Fact-Lock shot plan for cinematic v2 (Flow Veo i2v + Edge-TTS).

Rules (Slot 1 Decomposer → Slot 2 Mapper):
- narration_ko: visible layer for TTS only
- graph_anchor: backend JSON only — never injected into video prompts
- prompt_motion_en: i2v motion + camera + ambient only (English)
- negative_nouns: noun-list exclusions per Vertex guidance
- flow_mode_hint: fast_iterate | quality_final

Input: scenario text file (one narration line per shot)
Output:
- director_agent_v2_shot_plan_latest.json
- director_agent_v2_prompt_pack_latest.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCENARIO = ART / "cinematic_scenario_v2_ko.txt"
DEFAULT_JSON = ART / "director_agent_v2_shot_plan_latest.json"
DEFAULT_TXT = ART / "director_agent_v2_prompt_pack_latest.txt"
DEFAULT_WORKSPACE = ART / "cinematic_v2_workspace"

NEGATIVE_NOUNS_BASE = (
    "text overlay, subtitles, captions, lip sync, dialogue speech, "
    "face warp, identity change, extra fingers, warped hands, distorted body, "
    "watermark, logo, heavy flicker, sudden camera whip, "
    "cup, mug, coffee, tea, drinking, sipping"
)

GRAPH_ANCHORS: list[dict[str, str]] = [
    {"anchor_id": "dawn_witness", "lens": "Logos", "gating": "NON_GATING"},
    {"anchor_id": "purify_daily", "lens": "Sasang", "gating": ""},
    {"anchor_id": "observe_field", "lens": "Field", "gating": ""},
    {"anchor_id": "base_lock", "lens": "Logos", "gating": ""},
    {"anchor_id": "rest_gate", "lens": "Myeongni", "gating": ""},
    {"anchor_id": "noise_filter", "lens": "Sasang", "gating": ""},
    {"anchor_id": "manifest_commit", "lens": "Field", "gating": ""},
    {"anchor_id": "final_sync", "lens": "HOLD", "gating": "send_gate_HOLD"},
]

CAMERA_CYCLE = [
    "static medium shot, micro handheld stability",
    "static close-up, no abrupt movement",
    "over-shoulder static shot",
    "static wide shot, slow natural motion only",
    "slow dolly in, very stable",
    "static medium near window",
    "close-up hands and journal only",
    "static wide shot, golden hour stillness",
]

MOTION_BEATS = [
    (
        "Soft dawn light gradually brightens through sheer curtains; "
        "subtle dust motes drift in the air. Camera holds still."
    ),
    (
        "Hands run under a slow cold water stream at the bathroom sink; "
        "gentle water flow only, no face toward camera."
    ),
    (
        "Hand writes three short items on a notepad with slow deliberate pen strokes; "
        "minimal shoulder movement."
    ),
    (
        "Subtle motion of arranging shoes and hanging a coat on a hook in the entryway; "
        "calm purposeful gestures."
    ),
    (
        "Figure leans back into an armchair with a gentle exhale; "
        "minimal body shift, no abrupt motion."
    ),
    (
        "Curtains sway slightly from a breeze near the window; "
        "subject remains still, gazing outward."
    ),
    (
        "Pen writes one line in a journal with a slow steady hand; "
        "focus on paper texture and ink motion."
    ),
    (
        "Living room at golden hour; subtle ambient light shift across the room; "
        "calm stillness, no on-screen title text."
    ),
]

AMBIENT_TAIL = "Ambient: quiet domestic room tone, no dialogue, no subtitles. 24fps cinematic naturalism."

# Slot 2 GLOBAL_TECH_CINEMATIC_SECURITY_SLOT2_V1 — metadata only; never in prompt_motion_en
EXTERNAL_BENCHMARK_ANCHORS: list[dict[str, str]] = [
    {
        "anchor_id": "deepmind_a24_previz",
        "source_tier0": "docs/research/raw/global_tech_core_inject_tier0_2026-06-23.md",
        "claim": "storyboard and pre-viz assist for film workflows",
        "mkm_alignment": "companion-daily-v2 i2v pre-viz; not festival deliverable",
        "gating": "NON_GATING",
        "overclaim_guard": "O-02",
        "send_gate": "HOLD",
    },
    {
        "anchor_id": "openai_security_lint_inspiration",
        "source_tier0": "docs/research/raw/global_tech_core_inject_tier0_2026-06-23.md",
        "claim": "security copy lint inspiration only; no vendor API wire in Slot 2",
        "mkm_alignment": "check_cinematic_overclaim_copy_guard_v1.py + pytest",
        "gating": "NON_GATING",
        "overclaim_guard": "O-03",
        "send_gate": "HOLD",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def split_lines(text: str, target_shots: int) -> list[str]:
    lines = [x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith("#")]
    if not lines:
        lines = ["창밖이 먼저 밝아온다."]
    out: list[str] = []
    while len(out) < target_shots:
        out.append(lines[len(out) % len(lines)])
    return out[:target_shots]


def build_prompt_motion_en(camera_rule: str, motion_beat: str) -> str:
    return f"{camera_rule}. {motion_beat} {AMBIENT_TAIL}"


def anchor_ids_must_not_leak(prompt: str, anchors: list[dict[str, str]]) -> None:
    for anchor in anchors:
        anchor_id = anchor["anchor_id"]
        if anchor_id.lower() in prompt.lower():
            raise ValueError(f"graph_anchor leaked into prompt: {anchor_id}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--target-shots", type=int, default=8)
    ap.add_argument("--shot-sec", type=int, default=5)
    ap.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--out-prompt-pack", type=Path, default=DEFAULT_TXT)
    args = ap.parse_args()

    scenario_path = args.scenario_file if args.scenario_file.is_absolute() else (ROOT / args.scenario_file)
    if not scenario_path.is_file():
        raise SystemExit(f"scenario file not found: {scenario_path}")

    narrations = split_lines(scenario_path.read_text(encoding="utf-8"), args.target_shots)
    if len(GRAPH_ANCHORS) < args.target_shots:
        raise SystemExit(f"GRAPH_ANCHORS has {len(GRAPH_ANCHORS)} entries; need {args.target_shots}")

    fact_lock = {
        "concept": "companion-daily-v2",
        "video_surface": "plain Korean daily monologue (TTS layer only)",
        "video_prompt_language": "English motion+camera only for Flow/Veo i2v",
        "graph_anchor_policy": "JSON metadata only; never inject anchor_id into prompt_motion_en",
        "audio_policy": "Edge-TTS ko-KR-SunHiNeural per shot; Veo native dialogue disabled",
        "flow_ingredients": "master_character.png + master_location.png (+ optional prev last_frame)",
        "credit_policy": "fast_iterate for takes; quality_final for selected master only",
        "send_gate": "HOLD",
        "promotion": "research_only",
        "external_benchmark_anchors": EXTERNAL_BENCHMARK_ANCHORS,
        "external_benchmark_policy": "JSON metadata only; never inject into prompt_motion_en or PUBLIC_FACING without overclaim guard",
    }

    workspace_root = args.workspace_root if args.workspace_root.is_absolute() else (ROOT / args.workspace_root)
    shots = []
    for i, narration_ko in enumerate(narrations, start=1):
        shot_id = f"SHOT_{i:02d}"
        idx = i - 1
        shot_dir = workspace_root / "shots" / f"shot_{i:02d}"
        ref_prev = (
            (workspace_root / "shots" / f"shot_{i-1:02d}" / "last_frame.png").as_posix()
            if i > 1
            else ""
        )
        camera_rule = CAMERA_CYCLE[idx % len(CAMERA_CYCLE)]
        motion_beat = MOTION_BEATS[idx % len(MOTION_BEATS)]
        prompt_motion_en = build_prompt_motion_en(camera_rule, motion_beat)
        graph_anchor = dict(GRAPH_ANCHORS[idx])
        anchor_ids_must_not_leak(prompt_motion_en, GRAPH_ANCHORS)

        flow_mode_hint = "quality_final" if i == args.target_shots else "fast_iterate"
        shots.append(
            {
                "shot_id": shot_id,
                "duration_sec": args.shot_sec,
                "narration_ko": narration_ko,
                "graph_anchor": graph_anchor,
                "camera_rule": camera_rule,
                "prompt_motion_en": prompt_motion_en,
                "negative_nouns": NEGATIVE_NOUNS_BASE,
                "flow_mode_hint": flow_mode_hint,
                "reference_inputs": {
                    "master_character_image": (workspace_root / "references" / "master_character.png").as_posix(),
                    "master_location_image": (workspace_root / "references" / "master_location.png").as_posix(),
                    "previous_shot_last_frame": ref_prev,
                },
                "workspace_targets": {
                    "shot_dir": shot_dir.as_posix(),
                    "narration_wav": (shot_dir / "narration.wav").as_posix(),
                    "clip_output": (shot_dir / "clip.mp4").as_posix(),
                    "first_frame_export": (shot_dir / "first_frame.png").as_posix(),
                    "last_frame_export": (shot_dir / "last_frame.png").as_posix(),
                },
            }
        )

    payload = {
        "schema": "director_agent_v2_shot_plan",
        "generated_at_utc": now_utc(),
        "scenario_file": str(scenario_path),
        "target_shots": args.target_shots,
        "shot_sec": args.shot_sec,
        "total_duration_sec": args.target_shots * args.shot_sec,
        "generator_stack": {
            "video": "Google Flow Veo 3.1 i2v",
            "voice": "edge-tts ko-KR-SunHiNeural",
            "assemble": "ffmpeg concat + athena_editor --no-ducking",
        },
        "fact_lock": fact_lock,
        "prompt_rules": {
            "formula": "[Cinematography] + [Motion beat] + [Ambient audio hint]",
            "i2v_rule": "Do not restate subject appearance; Ingredients carry identity",
            "negative_style": "noun list only (no 'no watermark' phrasing in Flow UI)",
            "single_beat_per_clip": True,
        },
        "shots": shots,
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    block: list[str] = [
        "# MKM Director-Agent v2 Prompt Pack (Flow i2v)",
        f"# generated_at_utc: {payload['generated_at_utc']}",
        "",
        "## Global rules",
        "- narration_ko → Edge-TTS only",
        "- prompt_motion_en → Flow i2v (motion + camera + ambient)",
        "- graph_anchor → JSON manifest only; never paste into Flow prompt",
        "- negative_nouns → paste as exclusion list where UI supports it",
        "",
        "## Flow Ingredients",
        f"- character: {workspace_root / 'references' / 'master_character.png'}",
        f"- location: {workspace_root / 'references' / 'master_location.png'}",
        "",
        "## Shots",
    ]
    for shot in shots:
        block.append(f"### {shot['shot_id']} ({shot['duration_sec']}s) [{shot['flow_mode_hint']}]")
        block.append(f"- narration_ko: {shot['narration_ko']}")
        block.append(f"- graph_anchor: {json.dumps(shot['graph_anchor'], ensure_ascii=False)}")
        block.append(f"- prompt_motion_en: {shot['prompt_motion_en']}")
        block.append(f"- negative_nouns: {shot['negative_nouns']}")
        block.append("")

    out_txt = args.out_prompt_pack if args.out_prompt_pack.is_absolute() else (ROOT / args.out_prompt_pack)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("\n".join(block) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "shot_plan_json": str(out_json),
                "prompt_pack_txt": str(out_txt),
                "shot_count": len(shots),
                "shot_sec": args.shot_sec,
                "workspace_root": str(workspace_root),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
