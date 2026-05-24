#!/usr/bin/env python3
"""O-P31c Zone B — TKM health skin 5m rhythm shorts (non-clinical)."""

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
    DialogueLineFactory,
    base_doc_shell,
    clip,
    myeongni_pacing_line,
    read_json,
    resolve_path,
    sasang_brake_line,
)
from scripts.mkm_radio_program_skin_v1 import get_skin  # noqa: E402
from scripts.tkm_health_dialogue_guard_v1 import sanitize_health_audio_text  # noqa: E402

DEFAULT_LOGOS = ROOT / "reports" / "commander_daily_logos_anchor_latest.json"
DEFAULT_BRIEFING = ROOT / "reports" / "commander_advanced_briefing_latest.json"
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_WEATHER = ROOT / "reports" / "commander_weather_seoul_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_script_health_shorts_latest.json"


def _seasonal_line(weather: Dict[str, Any]) -> str:
    band = str(weather.get("weather_band") or weather.get("band") or "mild")
    temp = weather.get("temp_c") or weather.get("temperature_c")
    temp_s = f"{temp}°C " if temp is not None else ""
    return sanitize_health_audio_text(
        f"오늘 환경 리듬은 {temp_s}밴드 {band}입니다. "
        "수분·통풍·가벼운 스트레칭으로 체온 변화에 맞추십시오. 진단이 아닌 생활 참고입니다."
    )


def build_health_shorts_doc(
    root: Path,
    *,
    logos_path: Path = DEFAULT_LOGOS,
    briefing_path: Path = DEFAULT_BRIEFING,
    fortune_path: Path = DEFAULT_FORTUNE,
    weather_path: Path = DEFAULT_WEATHER,
) -> Dict[str, Any]:
    skin = get_skin({"program_skin": "tkm_health_24h"})
    logos = read_json(resolve_path(root, logos_path))
    briefing = read_json(resolve_path(root, briefing_path))
    fortune = read_json(resolve_path(root, fortune_path))
    weather = read_json(resolve_path(root, weather_path))

    cal = (
        str(briefing.get("calendar_kst") or fortune.get("calendar_kst") or "")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    bid = f"TKM-HEALTH-{cal.replace('-', '')}-SHORTS01"
    factory = DialogueLineFactory()

    segments: List[Dict[str, Any]] = [
        {
            "segment_index": 1,
            "segment_name": "opening_and_disclaimer",
            "dialogue": [
                factory.line("system_announcer", skin.disclaimer_text_ko, tags=["DISCLAIMER"], dur=10.0)
            ],
        },
        {
            "segment_index": 2,
            "segment_name": "rhythm_pacing_core",
            "dialogue": [
                factory.line(
                    "mc_myeongni",
                    myeongni_pacing_line(briefing, fortune),
                    tags=["NON_GATING", "MYEONGNI", "HYPO"],
                    evidence="commander_daily_fortune_v1_1",
                    dur=22.0,
                ),
            ],
        },
        {
            "segment_index": 3,
            "segment_name": "cognitive_brake",
            "dialogue": [
                factory.line(
                    "dr_sasang",
                    sasang_brake_line(briefing, extra="생활 리듬 채널입니다."),
                    tags=["NON_GATING", "SASANG", "HYPO"],
                    dur=16.0,
                ),
            ],
        },
        {
            "segment_index": 4,
            "segment_name": "environment_seasonal",
            "dialogue": [
                factory.line(
                    "mc_myeongni",
                    _seasonal_line(weather) if weather else "환경 데이터가 비어 있습니다. 실내 통풍만 챙기십시오.",
                    tags=["NON_GATING", "WEATHER"],
                    dur=14.0,
                ),
            ],
        },
        {
            "segment_index": 5,
            "segment_name": "logos_non_gating_anchor",
            "dialogue": [
                factory.line(
                    "dj_logos",
                    sanitize_health_audio_text(
                        "DJ Logos입니다. 마음 챙김 앵커는 관측용입니다. "
                        f"{clip(str((logos.get('golden_anchor') or {}).get('ref') or ''), 40)}"
                    ),
                    tags=["NON_GATING", "LOGOS"],
                    dur=12.0,
                ),
            ],
        },
        {
            "segment_index": 6,
            "segment_name": "closing_cta",
            "dialogue": [factory.line("system_announcer", skin.closing_cta_ko, tags=["CTA"], dur=8.0)],
        },
    ]

    doc = base_doc_shell(
        briefing_id=bid,
        calendar_kst=cal,
        program_style="health_shorts_5m",
        deployment_target="YOUTUBE_SHORTS",
        upstream_inputs={
            "logos_anchor": str(logos_path),
            "briefing": str(briefing_path),
            "fortune": str(fortune_path),
            "weather": str(weather_path),
        },
        srt_name="reports/radio_dialogue_script_health_shorts_latest.srt",
        program_skin="tkm_health_24h",
    )
    doc["segments"] = segments
    for seg in doc["segments"]:
        for d in seg.get("dialogue") or []:
            d["audio_text"] = sanitize_health_audio_text(str(d.get("audio_text") or ""))
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build TKM health 5m shorts dialogue script.")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = build_health_shorts_doc(args.root)
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
