#!/usr/bin/env python3
"""O-P31c Zone B — deterministic 60s morning Shorts dialogue script from commander SSOT."""

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
    macro_posture_line,
    myeongni_pacing_line,
    read_json,
    resolve_path,
    sasang_brake_line,
)

DEFAULT_LOGOS = ROOT / "reports" / "commander_daily_logos_anchor_latest.json"
DEFAULT_BRIEFING = ROOT / "reports" / "commander_advanced_briefing_latest.json"
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.json"


def build_morning_shorts_doc(
    root: Path,
    *,
    logos_path: Path = DEFAULT_LOGOS,
    briefing_path: Path = DEFAULT_BRIEFING,
    fortune_path: Path = DEFAULT_FORTUNE,
) -> Dict[str, Any]:
    logos = read_json(resolve_path(root, logos_path))
    briefing = read_json(resolve_path(root, briefing_path))
    fortune = read_json(resolve_path(root, fortune_path))

    cal = (
        str(briefing.get("calendar_kst") or fortune.get("calendar_kst") or "")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    bid = f"MKM-RADIO-{cal.replace('-', '')}-SHORTS01"
    factory = DialogueLineFactory()

    segments: List[Dict[str, Any]] = [
        {
            "segment_index": 1,
            "segment_name": "opening_and_disclaimer",
            "dialogue": [factory.line("system_announcer", DISCLAIMER_TEXT_KO, tags=["DISCLAIMER"], dur=8.0)],
        },
        {
            "segment_index": 2,
            "segment_name": "logos_anchor_insight",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    logos_line(logos) if logos else "DJ Logos입니다. 오늘 앵커 데이터가 비어 있습니다.",
                    tags=["NON_GATING", "LOGOS"],
                    evidence="commander_daily_logos_anchor_v1.golden_anchor",
                    dur=18.0,
                ),
            ],
        },
        {
            "segment_index": 3,
            "segment_name": "myeongni_temporal_rhythm",
            "dialogue": [
                factory.line(
                    "mc_myeongni",
                    myeongni_pacing_line(briefing, fortune),
                    tags=["NON_GATING", "MYEONGNI", "HYPO"],
                    evidence="commander_daily_fortune_v1_1.myeongni_lines",
                    dur=18.0,
                ),
            ],
        },
        {
            "segment_index": 4,
            "segment_name": "sasang_bias_veto",
            "dialogue": [
                factory.line(
                    "dr_sasang",
                    sasang_brake_line(briefing),
                    tags=["NON_GATING", "SASANG", "HYPO"],
                    evidence="commander_hypothesis_stream_v1.branches",
                    dur=14.0,
                ),
            ],
        },
        {
            "segment_index": 5,
            "segment_name": "macro_posture_non_price",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    macro_posture_line(briefing),
                    tags=["NON_GATING", "MACRO_OBSERVATION"],
                    evidence="commander_world_pulse_fusion_v1.macro",
                    dur=10.0,
                ),
            ],
        },
        {
            "segment_index": 6,
            "segment_name": "closing_cta",
            "dialogue": [factory.line("system_announcer", CLOSING_CTA_KO, tags=["CTA"], dur=6.0)],
        },
    ]

    doc = base_doc_shell(
        briefing_id=bid,
        calendar_kst=cal,
        program_style="morning_shorts_60s",
        deployment_target="YOUTUBE_SHORTS",
        upstream_inputs={
            "logos_anchor": str(logos_path),
            "briefing": str(briefing_path),
            "fortune": str(fortune_path),
            "listener_story": None,
        },
        srt_name="reports/radio_dialogue_script_morning_shorts_latest.srt",
        program_skin="mkm_radio",
    )
    doc["segments"] = segments
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build morning 60s radio dialogue script (Zone B).")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--logos-json", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--briefing-json", type=Path, default=DEFAULT_BRIEFING)
    ap.add_argument("--fortune-json", type=Path, default=DEFAULT_FORTUNE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = build_morning_shorts_doc(
        args.root,
        logos_path=args.logos_json,
        briefing_path=args.briefing_json,
        fortune_path=args.fortune_json,
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
