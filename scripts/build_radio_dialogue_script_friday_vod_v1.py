#!/usr/bin/env python3
"""O-P31c Zone B — Friday 20m VOD dialogue script (listener story + 3 lenses)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_radio_dialogue_build_common_v1 import (  # noqa: E402
    CLOSING_CTA_KO,
    DISCLAIMER_TEXT_KO,
    DialogueLineFactory,
    base_doc_shell,
    logos_line,
    logos_story_line,
    macro_posture_line,
    myeongni_pacing_line,
    read_json,
    resolve_path,
    sasang_brake_line,
    story_narration_line,
)

DEFAULT_LOGOS = ROOT / "reports" / "commander_daily_logos_anchor_latest.json"
DEFAULT_BRIEFING = ROOT / "reports" / "commander_advanced_briefing_latest.json"
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_STORY = ROOT / "data" / "radio" / "listener_story_v1.example.json"
DEFAULT_NARRATIVE_FUEL = ROOT / "data" / "radio" / "narrative_fuel_science_v1.example.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_script_friday_vod_latest.json"


def build_friday_vod_doc(
    root: Path,
    *,
    logos_path: Path = DEFAULT_LOGOS,
    briefing_path: Path = DEFAULT_BRIEFING,
    fortune_path: Path = DEFAULT_FORTUNE,
    story_path: Path = DEFAULT_STORY,
    narrative_fuel_path: Path | None = None,
) -> Dict[str, Any]:
    logos = read_json(resolve_path(root, logos_path))
    briefing = read_json(resolve_path(root, briefing_path))
    fortune = read_json(resolve_path(root, fortune_path))
    story = read_json(resolve_path(root, story_path))

    cal = (
        str(briefing.get("calendar_kst") or fortune.get("calendar_kst") or story.get("calendar_kst") or "")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    bid = f"MKM-RADIO-{cal.replace('-', '')}-FRI01"
    body_ko = str(story.get("body_ko") or "")
    factory = DialogueLineFactory()

    segments: List[Dict[str, Any]] = [
        {
            "segment_index": 1,
            "segment_name": "opening_and_disclaimer",
            "dialogue": [factory.line("system_announcer", DISCLAIMER_TEXT_KO, tags=["DISCLAIMER"], dur=10.0)],
        },
        {
            "segment_index": 2,
            "segment_name": "opening_dj_macro_posture",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    macro_posture_line(briefing) + " 야간 부스에 오신 것을 환영합니다.",
                    tags=["NON_GATING", "MACRO_OBSERVATION"],
                    dur=22.0,
                ),
            ],
        },
        {
            "segment_index": 3,
            "segment_name": "listener_story_narration",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    story_narration_line(story),
                    tags=["STORY", "NON_GATING"],
                    evidence="listener_story_v1.body_ko",
                    dur=90.0,
                ),
            ],
        },
        {
            "segment_index": 4,
            "segment_name": "logos_citation_pack",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    logos_story_line(logos, body_ko) if logos else logos_line(logos),
                    tags=["LOGOS", "NON_GATING"],
                    dur=75.0,
                ),
            ],
        },
        {
            "segment_index": 5,
            "segment_name": "myeongni_temporal_rhythm",
            "dialogue": [
                factory.line(
                    "mc_myeongni",
                    myeongni_pacing_line(briefing, fortune)
                    + " 사연자에게는 결정을 미루고 흐름을 관찰하는 창이 더 넓을 수 있습니다.",
                    tags=["MYEONGNI", "HYPO"],
                    dur=80.0,
                ),
            ],
        },
        {
            "segment_index": 6,
            "segment_name": "sasang_bias_veto",
            "dialogue": [
                factory.line(
                    "dr_sasang",
                    sasang_brake_line(
                        briefing,
                        extra="사연자는 번아웃과 조급함이 겹친 편향 패턴으로 보입니다.",
                    ),
                    tags=["SASANG", "HYPO"],
                    dur=70.0,
                ),
            ],
        },
        {
            "segment_index": 7,
            "segment_name": "closing_cta",
            "dialogue": [factory.line("system_announcer", CLOSING_CTA_KO, tags=["CTA"], dur=12.0)],
        },
    ]

    upstream: Dict[str, Any] = {
        "logos_anchor": str(logos_path),
        "briefing": str(briefing_path),
        "fortune": str(fortune_path),
        "listener_story": str(story_path),
    }
    if narrative_fuel_path is not None:
        from scripts.mkm_radio_narrative_fuel_v1 import (  # noqa: WPS433
            insert_science_fuel_segment,
            load_narrative_fuel,
        )

        fuel_path = resolve_path(root, narrative_fuel_path)
        fuel = load_narrative_fuel(fuel_path)
        segments = insert_science_fuel_segment(segments, fuel, factory)
        upstream["narrative_fuel"] = str(fuel_path)

    doc = base_doc_shell(
        briefing_id=bid,
        calendar_kst=cal,
        program_style="friday_vod_20m",
        deployment_target="YOUTUBE_VOD",
        upstream_inputs=upstream,
        srt_name="reports/radio_dialogue_script_friday_vod_latest.srt",
        program_skin="mkm_radio",
    )
    doc["segments"] = segments
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Friday VOD radio dialogue script.")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--story-json", type=Path, default=DEFAULT_STORY)
    ap.add_argument(
        "--narrative-fuel-json",
        type=Path,
        default=None,
        help="Optional narrative_fuel_science_v1 JSON (B-track, non-gating).",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    fuel = args.narrative_fuel_json
    doc = build_friday_vod_doc(
        args.root,
        story_path=args.story_json,
        narrative_fuel_path=fuel,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    out = resolve_path(args.root, args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
