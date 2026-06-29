#!/usr/bin/env python3
"""Build Flow i2v handoff pack for cinematic v2 SHOT_01 (manual Flow step)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SHOT_PLAN = ART / "director_agent_v2_shot_plan_latest.json"
DEFAULT_BOOTSTRAP = ART / "cinematic_v2_workspace_bootstrap_latest.json"
DEFAULT_OUT_JSON = ART / "cinematic_v2_shot01_flow_handoff_latest.json"
DEFAULT_OUT_TXT = ART / "cinematic_v2_shot01_flow_handoff_latest.txt"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shot-plan-json", type=Path, default=DEFAULT_SHOT_PLAN)
    ap.add_argument("--bootstrap-json", type=Path, default=DEFAULT_BOOTSTRAP)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-txt", type=Path, default=DEFAULT_OUT_TXT)
    args = ap.parse_args()

    shot_plan_path = args.shot_plan_json if args.shot_plan_json.is_absolute() else (ROOT / args.shot_plan_json)
    if not shot_plan_path.is_file():
        raise SystemExit(f"shot plan not found: {shot_plan_path}")

    doc = json.loads(shot_plan_path.read_text(encoding="utf-8"))
    shot = next((s for s in (doc.get("shots") or []) if s.get("shot_id") == "SHOT_01"), None)
    if not shot:
        raise SystemExit("SHOT_01 not found in shot plan")

    bootstrap: dict = {}
    bootstrap_path = args.bootstrap_json if args.bootstrap_json.is_absolute() else (ROOT / args.bootstrap_json)
    if bootstrap_path.is_file():
        bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))

    refs = shot.get("reference_inputs") or {}
    targets = shot.get("workspace_targets") or {}
    master_char = resolve_path(str(refs.get("master_character_image") or ""))
    master_loc = resolve_path(str(refs.get("master_location_image") or ""))
    narr_wav = resolve_path(str(targets.get("narration_wav") or ""))
    clip_out = resolve_path(str(targets.get("clip_output") or ""))

    blockers: list[str] = []
    if not master_char.is_file():
        blockers.append("master_character.png missing — Gemini app → references/")
    if not master_loc.is_file():
        blockers.append("master_location.png missing — Gemini app → references/")
    if not narr_wav.is_file():
        blockers.append("narration.wav missing — render_cinematic_v2_narration_edge_tts_v1.py --shot-id SHOT_01")

    payload = {
        "schema": "cinematic_v2_shot01_flow_handoff_v1",
        "generated_at_utc": now_utc(),
        "shot_id": "SHOT_01",
        "flow_mode_hint": shot.get("flow_mode_hint"),
        "duration_sec": shot.get("duration_sec"),
        "narration_ko": shot.get("narration_ko"),
        "prompt_motion_en": shot.get("prompt_motion_en"),
        "negative_nouns": shot.get("negative_nouns"),
        "flow_ingredients": {
            "master_character_png": master_char.as_posix(),
            "master_location_png": master_loc.as_posix(),
            "master_character_exists": master_char.is_file(),
            "master_location_exists": master_loc.is_file(),
        },
        "outputs": {
            "narration_wav": narr_wav.as_posix(),
            "narration_wav_exists": narr_wav.is_file(),
            "clip_mp4": clip_out.as_posix(),
            "clip_mp4_exists": clip_out.is_file(),
        },
        "flow_ui_steps": [
            "Open Google Flow → Veo 3.1 → Image to video",
            "Upload Ingredients: master_character.png + master_location.png",
            "Mode: Fast (fast_iterate) — save 3 takes",
            "Paste prompt_motion_en into motion prompt (English only)",
            "Paste negative_nouns as exclusion nouns if UI supports",
            "Export best take → clip.mp4 path below",
        ],
        "external_benchmark_anchors": (doc.get("fact_lock") or {}).get("external_benchmark_anchors") or [],
        "blockers": blockers,
        "ready_for_flow_i2v": not blockers,
        "send_gate": "HOLD",
        "promotion": "research_only",
        "bootstrap_json": str(bootstrap_path.resolve()) if bootstrap_path.is_file() else "",
        "workspace_ready_for_flow": bootstrap.get("ready_for_flow_i2v"),
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    blocker_lines = [f"- {b}" for b in blockers] if blockers else ["- (none — proceed to Flow)"]
    txt_lines = [
        "# Cinematic v2 SHOT_01 — Flow i2v handoff",
        f"# generated_at_utc: {payload['generated_at_utc']}",
        f"# ready_for_flow_i2v: {payload['ready_for_flow_i2v']}",
        "",
        "## Blockers",
        *blocker_lines,
        "",
        "## Ingredients",
        f"- character: {master_char}",
        f"- location: {master_loc}",
        "",
        "## prompt_motion_en (paste)",
        str(shot.get("prompt_motion_en") or ""),
        "",
        "## negative_nouns (paste)",
        str(shot.get("negative_nouns") or ""),
        "",
        "## Save clip to",
        str(clip_out),
    ]
    out_txt = args.out_txt if args.out_txt.is_absolute() else (ROOT / args.out_txt)
    out_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(out_json),
                "out_txt": str(out_txt),
                "ready_for_flow_i2v": payload["ready_for_flow_i2v"],
                "blockers": blockers,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
