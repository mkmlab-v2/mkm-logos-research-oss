#!/usr/bin/env python3
"""Build Fact-Lock shot plan and prompt pack for external generators.

Input:
- scenario text file (one sentence per line recommended)

Output:
- director_agent_v1_shot_plan_latest.json
- director_agent_v1_prompt_pack_latest.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCENARIO = ART / "cinematic_scenario_sample_v1.txt"
DEFAULT_JSON = ART / "director_agent_v1_shot_plan_latest.json"
DEFAULT_TXT = ART / "director_agent_v1_prompt_pack_latest.txt"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def split_lines(text: str, target_shots: int) -> list[str]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        lines = ["MKM LAB 제어 무결성 시연 장면."]
    out = []
    while len(out) < target_shots:
        out.append(lines[len(out) % len(lines)])
    return out


def build_action_anchor(line: str) -> str:
    ll = line.lower()
    if "memory scene" in ll:
        return "show workout shirt recognition and Sports Refresh recommendation near washer; no cup interaction"
    if "sync scene" in ll:
        return "show memory particles flowing from washer into ThinQ hub and AC switching to dehumidify mode; no cup interaction"
    if "guard scene" in ll:
        return "show delicate silk warning and gentle intervention gesture near washer; no cup interaction"
    if "watch/hold" in ll:
        return "show WATCH/HOLD dashboard review on wall panel, one-handed touch interaction only; no cup interaction"
    if "long memory" in ll:
        return "show on-device memory panel and privacy-safe inference cards; no cup interaction"
    if "distributed memory orchestration" in ll:
        return "show washer, AC, and robot cleaner linked through a glowing ThinQ hub network; no cup interaction"
    if "final refrain" in ll:
        return "hero close-up with calm nod and gentle smile in living room; no cup interaction"
    if "measured facts" in ll:
        return "show objective and latency values on monitor while protagonist points to data; no cup interaction"
    if "smiles with visible relief" in ll:
        return "close-up relief expression with empty hands; no cup interaction"
    return "home AI interaction with purposeful hand gestures and no drink props"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--target-shots", type=int, default=10)
    ap.add_argument("--shot-sec", type=int, default=6)
    ap.add_argument("--workspace-root", type=Path, default=ART / "cinematic_consistency_pack_v1")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--out-prompt-pack", type=Path, default=DEFAULT_TXT)
    ap.add_argument("--concept", choices=["companion-human", "appliance-fusion"], default="companion-human")
    args = ap.parse_args()

    scenario = args.scenario_file.read_text(encoding="utf-8")
    lines = split_lines(scenario, args.target_shots)

    if args.concept == "appliance-fusion":
        fact_lock = {
            "subject_anchor": "smart home appliances and ThinQ hub only; no human protagonist",
            "object_anchor": "washer, air conditioner, robot cleaner, smart display, compact home appliances",
            "location_anchor": "modern Korean home interiors with clean futuristic product staging",
            "visual_anchor": "memory particles, soft holographic lines, glowing hub convergence, calm premium lighting",
            "camera_anchor": "stable cinematic camera with deliberate product-focused motion",
            "safety_anchor": "no hazardous visuals, no offensive content, no misleading emergency UI",
            "use_subject_refs": False,
            "consistency_tail": "same product family identity, same hub motif, same visual language, no people, no faces, no human hands",
        }
    else:
        fact_lock = {
            "character_anchor": "single Korean woman in early 30s, same identity across all shots",
            "appearance_anchor": "same face shape, same hairstyle, same natural makeup tone, same warm expression",
            "wardrobe_anchor": "clean modern homemaker outfit palette in beige/ivory/navy, no abrupt outfit swaps",
            "location_anchor": "same Korean home context with varied rooms (laundry, kitchen, living room), not a control-room loop",
            "color_anchor": "natural cinematic realism, soft contrast, no extreme filters",
            "camera_anchor": "stable professional camera language, no abrupt style jumps",
            "safety_anchor": "no graphic harm, no unsafe behavior, no offensive content",
            "use_subject_refs": True,
            "consistency_tail": "same single woman identity, same face, same age, same hair, same wardrobe, same home environment, realistic motion, no identity drift",
        }

    workspace_root = args.workspace_root if args.workspace_root.is_absolute() else (ROOT / args.workspace_root)
    shots = []
    camera_cycle = [
        "static medium shot, no camera shake",
        "slow pan left, subtle motion only",
        "slight dolly in, very stable",
        "static close-up, no abrupt movement",
    ]
    for i, line in enumerate(lines, start=1):
        shot_id = f"SHOT_{i:02d}"
        shot_dir = workspace_root / "shots" / f"shot_{i:02d}"
        ref_prev = (
            f"{(workspace_root / 'shots' / f'shot_{i-1:02d}' / 'last_frame.png').as_posix()}"
            if i > 1
            else ""
        )
        action_anchor = build_action_anchor(line)
        if args.concept == "appliance-fusion":
            prompt_core = (
                f"{line}. {camera_cycle[(i - 1) % len(camera_cycle)]}. "
                f"action anchor: {action_anchor}. "
                "smart appliance fusion showcase, premium Korean home interior, "
                "ThinQ hub-centered memory orchestration visuals, cinematic realism, "
                "no people, no human face, no human body, no spoken character lip-sync, "
                "16:9, natural motion, no watermark, no text overlay."
            )
            negative_prompt = (
                "person, human, face, hand selfie framing, lip movement dialogue shot, "
                "identity drift, distorted products, unreadable UI, heavy flicker, sudden style shift, watermark, logo text"
            )
        else:
            prompt_core = (
                f"{line}. {camera_cycle[(i - 1) % len(camera_cycle)]}. "
                f"action anchor: {action_anchor}. "
                "single Korean woman in early 30s, elegant and natural, same identity across shots, "
                "Korean home interior context with room variation, cinematic realism, "
                "no cup, no mug, no coffee, no drinking action, no sipping gesture, "
                "16:9, natural motion, no watermark, no text overlay."
            )
            negative_prompt = (
                "identity drift, different person, extra fingers, warped face, "
                "distorted body, unreadable UI, heavy flicker, sudden style shift, watermark, logo text, "
                "cup, mug, coffee, tea, sipping, drinking"
            )
        shots.append(
            {
                "shot_id": shot_id,
                "duration_sec": args.shot_sec,
                "intent": line,
                "camera_rule": camera_cycle[(i - 1) % len(camera_cycle)],
                "reference_inputs": {
                    "master_character_image": (workspace_root / "references" / "master_character.png").as_posix(),
                    "master_location_image": (workspace_root / "references" / "master_location.png").as_posix(),
                    "previous_shot_last_frame": ref_prev,
                },
                "workspace_targets": {
                    "shot_dir": shot_dir.as_posix(),
                    "clip_output": (shot_dir / "clip.mp4").as_posix(),
                    "first_frame_export": (shot_dir / "first_frame.png").as_posix(),
                    "last_frame_export": (shot_dir / "last_frame.png").as_posix(),
                },
                "prompt_core": prompt_core,
                "negative_prompt": negative_prompt,
            }
        )

    payload = {
        "schema": "director_agent_v1_shot_plan",
        "generated_at_utc": now_utc(),
        "scenario_file": str(args.scenario_file),
        "target_shots": args.target_shots,
        "shot_sec": args.shot_sec,
        "concept": args.concept,
        "fact_lock": fact_lock,
        "shots": shots,
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    block = []
    block.append("# MKM Director-Agent v1 Prompt Pack")
    block.append(f"# generated_at_utc: {payload['generated_at_utc']}")
    block.append("")
    block.append("## Global Fact-Lock Anchors")
    for k, v in fact_lock.items():
        block.append(f"- {k}: {v}")
    block.append("")
    block.append("## Reference Wiring Rule")
    block.append("- SHOT_01 uses master_character.png + master_location.png as the only visual anchors.")
    block.append("- SHOT_02+ must include previous shot last_frame.png as a chained reference.")
    block.append("- Keep camera motion limited to static / slow pan / slight dolly.")
    block.append("")
    block.append("## Shot Prompts")
    for shot in shots:
        block.append(f"- {shot['shot_id']} ({shot['duration_sec']}s): {shot['prompt_core']}")
        block.append(f"  - negative: {shot['negative_prompt']}")
        refs = shot["reference_inputs"]
        block.append(
            "  - refs: "
            f"character={refs['master_character_image']}, "
            f"location={refs['master_location_image']}, "
            f"prev_last={refs['previous_shot_last_frame'] or '(none for first shot)'}"
        )
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
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

