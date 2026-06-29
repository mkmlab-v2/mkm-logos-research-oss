#!/usr/bin/env python3
"""Evening insight for hero board FAIL slots + optional Azure reflect [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_daily_hero_board_lib_v1 import slot_ids, utc_now  # noqa: E402
from scripts.kospi_hero_shock_gate_shadow_lib_v1 import score_shadow_day  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/btrack_daily_hero_board_eval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_daily_hero_board_evening_insight_v1_latest.json"
ADVISORY_BRIEF = ROOT / "reports/mkm_parallel_advisory_brief_v1_latest.json"
LANE_ROUTING = ROOT / "docs/final/artifacts/kospi_prophecy_lane_routing_v1_latest.json"

SYSTEM = """You are MKM B-track hero board analyst (research_only). JSON only:
{"reflection_ko":"2-3 sentences Korean","slot_lessons":[{"slot_id":"","lesson":""}],"send_gate":"HOLD"}
No buy/sell advice."""


def _llm_reflect(payload: dict[str, Any], *, billing: str, timeout_sec: int) -> dict[str, Any]:
    from scripts.news_neutralizer_llm_v1 import llm_json, load_workspace_dotenv

    load_workspace_dotenv()
    user = json.dumps({"hero_board_miss": payload}, ensure_ascii=False)
    parsed, raw, resolved, model_label = llm_json(
        billing=billing,
        system=SYSTEM,
        user=user,
        timeout=timeout_sec,
        flash_model=os.environ.get("MKM_HERO_BOARD_GEMINI_MODEL", "gemini-2.5-flash"),
        pro_model=os.environ.get("MKM_HERO_BOARD_GEMINI_MODEL", "gemini-2.5-flash"),
        azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
    )
    if not isinstance(parsed, dict):
        parsed = {"reflection_ko": (raw or "")[:600], "send_gate": "HOLD", "parse_fallback": True}
    parsed.setdefault("send_gate", "HOLD")
    parsed["billing_resolved"] = resolved
    parsed["model_label"] = model_label
    return parsed


def build_insight(eval_doc: dict[str, Any], session_date: str) -> dict[str, Any]:
    row = next((r for r in eval_doc.get("rows") or [] if r.get("session_date") == session_date), None)
    if not row:
        return {"ok": False, "reason": "no_eval_row"}

    fails: list[dict[str, Any]] = []
    for sid in slot_ids():
        sc = (row.get("slots") or {}).get(sid) or {}
        if sc.get("scorable") and sc.get("outcome") == "FAIL":
            fails.append({"slot_id": sid, "score": sc})

    if not fails:
        return {"ok": True, "triggered": False, "reason": "no_fail_slots"}

    lessons = []
    for f in fails:
        sid = f["slot_id"]
        sc = f["score"]
        if sid == "kospi_direction" and sc.get("band_hit"):
            lessons.append(f"{sid}: direction FAIL but band_hit — level/direction split")
        elif sc.get("proxy_note"):
            lessons.append(f"{sid}: {sc['proxy_note']}")
        else:
            lessons.append(f"{sid}: FAIL on {session_date}")

    doc: dict[str, Any] = {
        "schema": "btrack_daily_hero_board_evening_insight_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "generated_at_utc": utc_now(),
        "session_date": session_date,
        "triggered": True,
        "fail_count": len(fails),
        "fail_slots": fails,
        "structured_lessons": lessons,
        "briefing_primary_pointer": "reports/mkm_parallel_advisory_brief_v1_latest.json",
        "lane_routing_contract": "docs/final/artifacts/kospi_prophecy_lane_routing_v1_latest.json",
        "do_not_confuse_ko": (
            "kospi_direction FAIL/HIT=scoring_shadow(weighted_blend). "
            "통찰 본선=parallel_advisory GraphRAG brief — 별도 레일."
        ),
    }

    if ADVISORY_BRIEF.is_file():
        try:
            brief = json.loads(ADVISORY_BRIEF.read_text(encoding="utf-8-sig"))
            doc["parallel_advisory_summary"] = {
                "session_anchor": brief.get("session_anchor"),
                "advisory_ko": (brief.get("advisory_ko") or "")[:800],
                "active_lenses": brief.get("active_lenses"),
                "conflict_surface": brief.get("conflict_surface"),
            }
        except json.JSONDecodeError:
            doc["parallel_advisory_summary"] = {"error": "brief_json_parse_failed"}

    kospi_fail = next((f for f in fails if f.get("slot_id") == "kospi_direction"), None)
    if kospi_fail:
        kospi_sc = kospi_fail.get("score") or {}
        shock_pred = ((row.get("slots") or {}).get("macro_news_shock") or {})
        foreign_pred = ((row.get("slots") or {}).get("foreign_flow") or {})
        shadow = score_shadow_day(
            session_date=session_date,
            active_direction=str(kospi_sc.get("predicted_direction") or "neutral"),
            actual_direction=str(kospi_sc.get("actual_direction") or "neutral"),
            shock_pred=shock_pred,
            foreign_flow_pred=foreign_pred,
            policy=None,
        )
        doc["hero_shock_gate_shadow"] = shadow
        if shadow.get("softened_active_fail"):
            doc["structured_lessons"].append(
                "hero_shock_gate_shadow: active FAIL -> shadow NEUTRAL_DRAW (macro_news_shock gate)"
            )

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", required=True)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--billing", default=os.environ.get("MKM_HERO_BOARD_BILLING", "auto"))
    ap.add_argument("--timeout-sec", type=int, default=90)
    args = ap.parse_args()

    ev_path = args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json
    eval_doc = json.loads(ev_path.read_text(encoding="utf-8-sig"))
    doc = build_insight(eval_doc, args.session_date.strip()[:10])
    if not doc.get("triggered"):
        print(json.dumps(doc, ensure_ascii=False))
        return 0

    if not args.skip_llm:
        try:
            doc["llm_reflect"] = _llm_reflect(
                {"session_date": doc["session_date"], "fails": doc["fail_slots"], "lessons": doc["structured_lessons"]},
                billing=args.billing,
                timeout_sec=args.timeout_sec,
            )
        except Exception as e:
            doc["llm_error"] = str(e)

    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "fail_count": doc["fail_count"], "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
