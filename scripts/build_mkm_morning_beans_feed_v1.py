#!/usr/bin/env python3
"""Build MKM Morning Beans bounded feed ([HYPO], research_only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_mkm_personal_briefing_guardrails_v1 import (  # noqa: E402
    evaluate as guardrail_evaluate,
)
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_COMMANDER = ART / "commander_profile_v1.example.json"
DEFAULT_MACRO = ART / "trackc_macro_risk_morning_briefing_latest.json"
DEFAULT_CALENDAR = ART / "mkm_morning_beans_calendar_v1_latest.json"
DEFAULT_FAMILY_SON = ART / "family_anchor_lived_calibration_son_kangmin_v1_latest.json"
DEFAULT_DAUGHTER = ART / "daughter_2026_integrated_guide_v4_minimal_latest.json"
OUT_JSON = ART / "mkm_morning_beans_feed_v1_latest.json"
LOG_JSONL = ROOT / "reports" / "mkm_morning_beans_feed_log.jsonl"

REGIME_LABEL_KO: dict[str, str] = {
    "imf": "IMF",
    "it_bubble": "IT 버블",
    "lehman": "리먼",
    "covid": "코로나",
    "post_covid_normalization": "포스트 코로나 정상화",
    "unknown": "미분류",
}

BOUNDARY_ACK = (
    "research_only; not medical, legal, or investment advice; no live trading or "
    "Track A auto-merge; max 10 cards anti-doomscroll; Logos NON_GATING; "
    "market/BTC/KOSPI ops tokens forbidden in personal cards; "
    "Gmail-scale cross-app ingest not in v1 scope."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _guardrail_ok(title: str, body: str) -> bool:
    text = f"{title}\n\n{body}"
    errors, _warnings = guardrail_evaluate(text, strict_paragraph_bleed=False)
    return not errors


def _precheck(title: str, body: str) -> dict[str, bool]:
    ok = _guardrail_ok(title, body)
    return {"ops_stage_tokens_absent": ok, "market_debt_bleed_absent": ok}


def resolve_field(macro: dict[str, Any]) -> dict[str, Any]:
    snap = macro.get("market_snapshot") or {}
    regime_id = str(snap.get("primary_regime_id") or "unknown")
    action = macro.get("action_frame") or {}
    posture = str(action.get("label") or snap.get("decision_state") or "WATCH").upper()
    if posture not in ("WATCH", "HOLD", "REDUCE"):
        posture = "WATCH"
    return {
        "regime_id": regime_id,
        "regime_source": "regime_map",
        "regime_label_ko": REGIME_LABEL_KO.get(regime_id, regime_id),
        "operator_posture_hint": posture,
    }


def _card(
    idx: int,
    *,
    lane: str,
    epistemic_label: str,
    lens_slot: str | None,
    title_ko: str,
    body_ko: str,
    deep_link: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pre = _precheck(title_ko, body_ko)
    card: dict[str, Any] = {
        "card_id": f"card_{idx:02d}",
        "lane": lane,
        "epistemic_label": epistemic_label,
        "lens_slot": lens_slot,
        "title_ko": title_ko,
        "body_ko": body_ko,
        "guardrail_precheck": pre,
    }
    if deep_link:
        card["deep_link"] = deep_link
    return card


def _pick_calendar_events(
    cal: dict[str, Any], *, feed_date_local: str, max_events: int = 2
) -> list[dict[str, Any]]:
    blocked = {"ops_blocked_from_personal_cards", "ops_blocked"}
    allowed_rails = {"family_anchor", "personal_wellness", "learning", "place_activity"}
    events = cal.get("events_local") or []
    eligible = [
        e
        for e in events
        if e.get("rail") not in blocked and (not e.get("rail") or e.get("rail") in allowed_rails)
    ]
    same_day = [
        e for e in eligible if str(e.get("start_local", "")).startswith(feed_date_local)
    ]
    if same_day:
        return same_day[:max_events]
    upcoming = sorted(
        (e for e in eligible if str(e.get("start_local", "")) >= feed_date_local),
        key=lambda row: str(row.get("start_local", "")),
    )
    return upcoming[:max_events]


def _son_family_card(idx: int, fam: dict[str, Any], family_path: Path) -> dict[str, Any]:
    anchor_id = fam.get("anchor_id") or "family_anchor_son_kangmin_v1"
    label = (fam.get("subject") or {}).get("display_label_ko") or "아들 이강민"
    axes = fam.get("supplementary_axes") or []
    line = ""
    for axis in axes:
        if axis.get("axis") == "growth_height" and axis.get("four_lines_ko"):
            line = str(axis["four_lines_ko"][0])
            break
    if not line:
        line = (
            (fam.get("clinical_l0_parent_reported") or {}).get("primary_goal_ko")
            or "키·혈당·GH 연속성 1순위."
        )
    return _card(
        idx,
        lane="family_anchor",
        epistemic_label="FACT",
        lens_slot="myeongni",
        title_ko=f"가족 앵커 — {label}",
        body_ko=f"{anchor_id}: {line} 임상 처방·성장 단정 없음.",
        deep_link={
            "kind": "artifact",
            "path_or_route": _rel(family_path),
            "label_ko": "강민 통합 가이드",
        },
    )


def _daughter_family_card(idx: int, daughter: dict[str, Any], daughter_path: Path) -> dict[str, Any]:
    anchor_id = daughter.get("anchor_id") or "family_anchor_our_daughter_v1"
    sasang = daughter.get("block_3_sasang_lifestyle_hyo") or {}
    lines = sasang.get("four_lines_ko") or []
    line = str(lines[0]) if lines else "11:30 취침·학교 루틴 우선 [HYPO]."
    return _card(
        idx,
        lane="family_anchor",
        epistemic_label="HYPO",
        lens_slot="sasang",
        title_ko="가족 앵커 — 딸 생활 1칸",
        body_ko=f"{anchor_id}: {line} 월별 병증·처방 단정 없음.",
        deep_link={
            "kind": "artifact",
            "path_or_route": _rel(daughter_path),
            "label_ko": "딸 v4-minimal 가이드",
        },
    )


def build_cards(
    *,
    commander: dict[str, Any],
    field: dict[str, Any],
    family_son_path: Path | None,
    daughter_path: Path | None,
    calendar_path: Path | None,
    feed_date_local: str,
    max_cards: int,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    idx = 1

    regime_id = field["regime_id"]
    posture = field["operator_posture_hint"]
    cards.append(
        _card(
            idx,
            lane="field_regime",
            epistemic_label="FACT",
            lens_slot=None,
            title_ko=f"오늘의 Field — {field['regime_label_ko']}",
            body_ko=(
                f"1차 실물 레짐 {regime_id}. 운영 자세는 {posture}. "
                "이 카드는 regime_map·매크로 브리핑 기반 관측이며 매매·임상 트리거가 아닙니다."
            ),
            deep_link={
                "kind": "artifact",
                "path_or_route": "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json",
                "label_ko": "매크로 브리핑 아티팩트",
            },
        )
    )
    idx += 1

    sasang = (commander.get("sasang_reference") or {}).get("label") or "미기록"
    cards.append(
        _card(
            idx,
            lane="personal_wellness",
            epistemic_label="HYPO",
            lens_slot="sasang",
            title_ko="아침 12분 — 입력·전정 우선",
            body_ko=(
                f"{sasang}(관찰) 기준 아침 루틴: 따뜻한 수분 → 가벼운 스트레칭 → "
                "첫 작업 전 3분 호흡. 체질 단정·처방 아님 [HYPO]."
            ),
            deep_link={
                "kind": "mkmlife_route",
                "path_or_route": "/oracle-sphere?profile=commander",
                "label_ko": "mkmlife 관측 구",
            },
        )
    )
    idx += 1

    myeongni = commander.get("myeongni_fact_ref") or {}
    pillars = myeongni.get("pillars") or {}
    pillar_txt = "·".join(
        str(pillars.get(k, "?"))
        for k in ("year", "month", "day", "hour")
    )
    cards.append(
        _card(
            idx,
            lane="personal_wellness",
            epistemic_label="FACT",
            lens_slot="myeongni",
            title_ko="명리 앵커 — 사주 기둥",
            body_ko=(
                f"엔진 Fact: {pillar_txt} (일간 {myeongni.get('day_master_stem', '?')}). "
                "중기 방향 참고용이며 운명·매매·임상 단정이 아닙니다."
            ),
            deep_link={
                "kind": "artifact",
                "path_or_route": _rel(DEFAULT_COMMANDER),
                "label_ko": "commander_profile",
            },
        )
    )
    idx += 1

    if family_son_path and family_son_path.is_file() and idx <= max_cards:
        fam = _read(family_son_path)
        if fam:
            cards.append(_son_family_card(idx, fam, family_son_path))
            idx += 1

    if daughter_path and daughter_path.is_file() and idx <= max_cards:
        daughter = _read(daughter_path)
        if daughter:
            cards.append(_daughter_family_card(idx, daughter, daughter_path))
            idx += 1

    cal = _read(calendar_path) if calendar_path and calendar_path.is_file() else {}
    for ev in _pick_calendar_events(cal, feed_date_local=feed_date_local, max_events=2):
        if idx > max_cards:
            break
        rail = ev.get("rail") or "place_activity"
        lane = "place_activity" if rail == "family_anchor" else rail
        cards.append(
            _card(
                idx,
                lane=lane if lane in {
                    "field_regime",
                    "personal_wellness",
                    "family_anchor",
                    "learning",
                    "place_activity",
                    "logos_explain",
                } else "place_activity",
                epistemic_label="FACT",
                lens_slot=None,
                title_ko=f"일정 — {ev.get('title', '일정')}",
                body_ko=(
                    f"로컬 캘린더 SSOT · {ev.get('start_local', '')} · rail={rail}. "
                    "운영 MS·grant 블록은 피드에서 제외됨."
                ),
                deep_link={
                    "kind": "artifact",
                    "path_or_route": _rel(calendar_path) if calendar_path else "",
                    "label_ko": "캘린더 SSOT",
                },
            )
        )
        idx += 1

    if idx <= max_cards:
        cards.append(
            _card(
                idx,
                lane="logos_explain",
                epistemic_label="NON_GATING",
                lens_slot="logos",
                title_ko="Logos 한 줄 [NON_GATING]",
                body_ko=(
                    "거시 시태 해설 보조 — 송출·주문·임상 게이트 없음. "
                    f"오늘 Field={regime_id} 톤: 관측 우선, 확장 자제."
                ),
                deep_link={
                    "kind": "showroom_static",
                    "path_or_route": "https://jemaai.cloud/",
                    "label_ko": "쇼룸 관측판",
                },
            )
        )

    return cards[:max_cards]


def build_feed(
    *,
    commander_path: Path = DEFAULT_COMMANDER,
    macro_path: Path = DEFAULT_MACRO,
    calendar_path: Path | None = DEFAULT_CALENDAR,
    family_son_path: Path | None = DEFAULT_FAMILY_SON,
    daughter_path: Path | None = DEFAULT_DAUGHTER,
    max_cards: int = 10,
    feed_date_local: str | None = None,
) -> dict[str, Any]:
    commander = _read(commander_path)
    if not commander or commander.get("schema") != "commander_profile_v1":
        raise ValueError(f"invalid commander profile: {commander_path}")

    macro = _read(macro_path)
    field = resolve_field(macro)
    local_date = feed_date_local or date.today().isoformat()
    cards = build_cards(
        commander=commander,
        field=field,
        family_son_path=family_son_path,
        daughter_path=daughter_path,
        calendar_path=calendar_path,
        feed_date_local=local_date,
        max_cards=max_cards,
    )
    out_path = OUT_JSON

    feed_text = "\n\n".join(f"{c['title_ko']}\n{c['body_ko']}" for c in cards)
    errors, warnings = guardrail_evaluate(feed_text, strict_paragraph_bleed=False)
    guard_exit = 1 if errors else 0

    doc: dict[str, Any] = {
        "schema": "mkm_morning_beans_feed_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "feed_date_local": local_date,
        "hypothesis_tier": "B",
        "boundary_ack": BOUNDARY_ACK,
        "feed_policy": {
            "max_cards": max_cards,
            "anti_doomscroll": True,
            "session_ttl_minutes": 12,
            "illustration_mode": "artifact_thumbnail",
        },
        "field": field,
        "subject_ref": {
            "profile_kind": "commander_profile_v1",
            "profile_path": _rel(commander_path),
            "display_label": (commander.get("subject") or {}).get("display_label") or "지휘관",
        },
        "input_sources": [
            {
                "source_id": "macro_morning_briefing",
                "consent": "explicit_local",
                "rail": "none",
                "path_ref": _rel(macro_path) if macro_path.is_file() else None,
            },
            {
                "source_id": "myeongni_profile",
                "consent": "explicit_local",
                "rail": "myeongni_engine",
                "path_ref": _rel(commander_path),
            },
            {
                "source_id": "family_son_anchor",
                "consent": "explicit_local",
                "rail": "family_playbook",
                "path_ref": _rel(family_son_path) if family_son_path and family_son_path.is_file() else None,
            },
            {
                "source_id": "family_daughter_guide",
                "consent": "explicit_local",
                "rail": "family_playbook",
                "path_ref": _rel(daughter_path) if daughter_path and daughter_path.is_file() else None,
            },
        ],
        "cards": cards,
        "pipeline_summary": {
            "field": field["regime_id"],
            "lens_order": ["sasang", "myeongni", "logos"],
            "conflict_note_ko": "개인 웰니스·가족 앵커·Field 레짐 분리 — 시장 주문 레일 카드 없음.",
            "final_action": field["operator_posture_hint"],
        },
        "governance": {
            "guardrail_script": "scripts/validate_mkm_personal_briefing_guardrails_v1.py",
            "forbidden_rail_bleed": [
                "btc_kospi_ops_stage_in_personal_card",
                "patient_clinical_gating_from_myeongni_hypo",
                "gmail_purchase_to_restaurant_auto_chain",
            ],
            "track_a_auto_merge": False,
            "live_trading_trigger": False,
            "public_publish_allowed": False,
        },
        "track_c_positioning_v1": {
            "headline_ko": "아침 10장의 관측 카드 — 격벽·아티팩트·짧은 세션",
            "subline_ko": (
                "결정론 명리 Fact와 멀티렌즈 [HYPO]/[NON_GATING]을 분리한 MKM Morning Beans. "
                "뉴스 무한 스크롤·투자·임상 단정 없음."
            ),
            "contrast_note_ko": (
                "드림빈즈형 전 앱 데이터 합성 스토리 대신, 로컬 SSOT·동의 단위 입력·"
                "guardrail 스크립트·regime_map Field 주도."
            ),
        },
        "final": {
            "decision_label": "WATCH"
            if field["operator_posture_hint"] in ("WATCH", "REDUCE")
            else "HOLD",
            "card_count": len(cards),
            "cms_publish_allowed": False,
            "disclaimer_ko": (
                "본 피드는 B-track Morning Beans v1 산출물이며 "
                "실서비스·의료·투자 조언이 아닙니다."
            ),
        },
        "audit": {
            "model_route": "local_stub_no_llm",
            "evidence_path": _rel(out_path),
            "validated_at": _utc_now(),
            "guardrail_script_exit": guard_exit,
            "guardrail_errors": errors,
            "guardrail_warnings": warnings,
        },
    }

    if calendar_path and calendar_path.is_file():
        doc["input_sources"].append(
            {
                "source_id": "calendar_local",
                "consent": "explicit_local",
                "rail": "calendar_stub",
                "path_ref": _rel(calendar_path),
            }
        )

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commander-json", type=Path, default=DEFAULT_COMMANDER)
    ap.add_argument("--macro-json", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CALENDAR)
    ap.add_argument("--family-son-json", type=Path, default=DEFAULT_FAMILY_SON)
    ap.add_argument("--daughter-json", type=Path, default=DEFAULT_DAUGHTER)
    ap.add_argument("--max-cards", type=int, default=10)
    ap.add_argument("--feed-date-local", default=None)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--fail-on-guardrail", action="store_true")
    args = ap.parse_args()

    doc = build_feed(
        commander_path=args.commander_json.resolve(),
        macro_path=args.macro_json.resolve(),
        calendar_path=args.calendar_json.resolve() if args.calendar_json else None,
        family_son_path=args.family_son_json.resolve() if args.family_son_json else None,
        daughter_path=args.daughter_json.resolve() if args.daughter_json else None,
        max_cards=min(14, max(1, args.max_cards)),
        feed_date_local=args.feed_date_local,
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
    log_row = {
        "generated_at_utc": doc.get("generated_at_utc"),
        "feed_date_local": doc.get("feed_date_local"),
        "card_count": doc["final"]["card_count"],
        "regime_id": doc["field"]["regime_id"],
        "guardrail_exit": doc["audit"]["guardrail_script_exit"],
        "path": _rel(args.out_json),
    }
    with LOG_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "output_json": _rel(args.out_json),
                "card_count": doc["final"]["card_count"],
                "regime_id": doc["field"]["regime_id"],
                "guardrail_exit": doc["audit"]["guardrail_script_exit"],
            },
            ensure_ascii=False,
        )
    )

    if args.fail_on_guardrail and doc["audit"]["guardrail_script_exit"] != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
