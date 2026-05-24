#!/usr/bin/env python3
"""Mirror commander daily bundle into mkmlife public JSON (one-question / ask-one context).

P31e — preview context for mkmlife.com; not live trading.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
FAMILY_ONE_QUESTION = ROOT / "reports" / "family_anchor_one_question_context_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects" / "mkm" / "mkm-life" / "public" / "data"
DEFAULT_OUT = MKMLIFE_PUBLIC / "commander_one_question_context_v1.json"
REPORTS_MIRROR = ROOT / "reports" / "commander_one_question_context_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_context(fortune: Dict[str, Any], *, include_family: bool = False) -> Dict[str, Any]:
    world = fortune.get("world_pulse_fusion") or {}
    hypo = fortune.get("hypothesis_stream") or {}
    cond = fortune.get("user_condition") or {}
    tilt = cond.get("advisory_investment_bias_tilt") or {}
    myeongni = fortune.get("myeongni_lines") or []
    one_liner = ""
    for ln in myeongni:
        if "오늘 한 줄" in str(ln):
            one_liner = ln.replace("▸ 오늘 한 줄:", "").strip()
            break

    ctx: Dict[str, Any] = {
        "schema": "commander_one_question_context_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "preview_only": True,
        "track_a_auto_order_forbidden": True,
        "generated_at_utc": _utc_now(),
        "calendar_kst": fortune.get("calendar_kst"),
        "city_default": fortune.get("city_default"),
        "concept_ko": "지휘관 일일 융합 — 명리·세상·초론·컨디션 (mkmlife ask-one 보조 컨텍스트)",
        "hero_ko": world.get("fusion_one_liner_ko") or one_liner,
        "synthesis_ko": hypo.get("synthesis_ko"),
        "headlines_top_ko": hypo.get("headlines_top_ko") or world.get("headlines_top_ko"),
        "market_tone": hypo.get("market_tone"),
        "branches": (hypo.get("branches") or [])[:5],
        "user_condition": {
            "energy_band": cond.get("energy_band"),
            "stress_band": cond.get("stress_band"),
            "sleep_band": cond.get("sleep_band"),
            "bio_synthesis_ko": cond.get("bio_synthesis_ko"),
        },
        "advisory_investment_bias_tilt": {
            "tilt_label": tilt.get("tilt_label"),
            "tilt_ko": tilt.get("tilt_ko"),
            "research_only": tilt.get("research_only", True),
        },
        "upstream": {
            "fortune_schema": fortune.get("schema"),
            "fortune_path": "reports/commander_daily_fortune_latest.json",
        },
        "disclaimer_ko": "[가설][NON_GATING] 투자·실매매·임상 단정 없음. coding funnel 리포트와 별 축.",
    }
    if include_family and FAMILY_ONE_QUESTION.is_file():
        family = json.loads(FAMILY_ONE_QUESTION.read_text(encoding="utf-8-sig"))
        ctx["family_anchor_profile"] = {
            "profile_id": family.get("profile_id"),
            "hero_ko": family.get("hero_ko"),
            "schema": family.get("schema"),
            "artifact_path": "reports/family_anchor_one_question_context_latest.json",
            "mkmlife_public_path": "projects/mkm/mkm-life/public/data/family_anchor_one_question_context_v1.json",
            "magic_orb_query": "?profile=family",
        }
    return ctx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=DEFAULT_FORTUNE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-mkmlife-public", action="store_true", help="Only write reports/ mirror")
    ap.add_argument("--include-family-anchor", action="store_true", help="Attach family_anchor one-question block if present")
    args = ap.parse_args()

    if not args.fortune_json.is_file():
        raise SystemExit(f"missing: {args.fortune_json}")

    fortune = json.loads(args.fortune_json.read_text(encoding="utf-8-sig"))
    ctx = build_context(fortune, include_family=args.include_family_anchor)

    REPORTS_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_MIRROR.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {REPORTS_MIRROR}")

    if not args.no_mkmlife_public:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
