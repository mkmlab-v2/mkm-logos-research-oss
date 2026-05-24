#!/usr/bin/env python3
"""Unified advanced Telegram briefing — max structured info + sealed predictions [HYPO].

Morning SSOT for evening score + evolution rail.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
KST = ZoneInfo("Asia/Seoul")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
TELEGRAM_MAX = 4096


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt_pct(v: Any) -> str:
    try:
        if v is None:
            return "n/a"
        x = float(v)
        if 0 <= x <= 1:
            return f"{x * 100:.1f}%"
        return f"{x:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _briefing_id(calendar_kst: str, predictions: List[Dict[str, Any]]) -> str:
    payload = json.dumps({"d": calendar_kst, "p": predictions}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _extract_predictions(
    fortune: Dict[str, Any],
    *,
    brief: Dict[str, Any],
    hypo_artifact: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Structured claims to score at evening (directional + behavioral)."""
    preds: List[Dict[str, Any]] = []
    stream = fortune.get("hypothesis_stream") or {}
    for br in stream.get("branches") or []:
        if not isinstance(br, dict):
            continue
        preds.append(
            {
                "prediction_id": f"branch:{br.get('branch_id')}",
                "kind": "behavioral_hypothesis",
                "claim_ko": br.get("predicted_bias_ko"),
                "confidence": br.get("confidence"),
                "score_against": ["kospi_direction", "behavioral_proxy"],
            }
        )

    k_action = str((fortune.get("world_pulse_fusion") or {}).get("kospi", {}).get("today_action") or brief.get("today_action") or "—")
    preds.append(
        {
            "prediction_id": "market_posture:kospi_morning",
            "kind": "market_direction_hypo",
            "claim_ko": f"장전 코스피 관측 액션 {k_action} (internal brief)",
            "direction_proxy": k_action,
            "confidence": "mid",
            "score_against": ["kospi_close_direction"],
        }
    )

    pred = (hypo_artifact.get("prediction") or {})
    if pred.get("direction"):
        inst = str(pred.get("instrument") or "").upper()
        against = ["btc_close_direction"] if "BTC" in inst else ["kospi_close_direction", "btc_close_direction"]
        preds.append(
            {
                "prediction_id": "btrack:hypothesis_prophecy",
                "kind": "btrack_price_hypo",
                "claim_ko": f"B-track 가설 {pred.get('instrument')} {pred.get('direction')}",
                "direction_proxy": pred.get("direction"),
                "confidence": pred.get("confidence"),
                "score_against": against,
            }
        )

    preds.append(
        {
            "prediction_id": "market_posture:nasdaq_prior",
            "kind": "nasdaq_session_hypo",
            "claim_ko": "전일 미 증시 나스닥 방향 — 익일 07:50 정산 [HYPO]",
            "direction_proxy": "WATCH",
            "confidence": "mid",
            "score_against": ["nasdaq_close_direction"],
            "evening_score": "pending_until_morning",
        }
    )

    synthesis = stream.get("synthesis_ko")
    if synthesis:
        preds.append(
            {
                "prediction_id": "synthesis:day",
                "kind": "narrative_hypothesis",
                "claim_ko": synthesis,
                "confidence": "mid",
                "score_against": ["kospi_direction"],
            }
        )
    return preds


def build_advanced_briefing_doc(
    workspace: Path = ROOT,
    *,
    fortune_path: Path = DEFAULT_FORTUNE,
) -> Dict[str, Any]:
    fortune = _read_json(fortune_path)
    art = workspace / "docs" / "final" / "artifacts"
    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    dual = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    hypo_art = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    hit = _read_json(art / "prophecy_hit_rate_eval_latest.json")
    news = _read_json(art / "news_independent_lens_latest.json")
    macro = _read_json(art / "trackc_macro_risk_morning_briefing_latest.json")

    cal = str(fortune.get("calendar_kst") or datetime.now(KST).strftime("%Y-%m-%d"))
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    world = fortune.get("world_pulse_fusion") or {}
    stream = fortune.get("hypothesis_stream") or {}
    cond = fortune.get("user_condition") or {}
    tilt = cond.get("advisory_investment_bias_tilt") or {}

    predictions = _extract_predictions(fortune, brief=brief, hypo_artifact=hypo_art)
    bid = _briefing_id(cal, predictions)

    market_seal: Dict[str, Any] = {}
    try:
        from scripts.multi_asset_market_adapter_v1 import fetch_market_seal  # noqa: WPS433

        market_seal = fetch_market_seal()
    except Exception as exc:  # pragma: no cover
        market_seal = {"seal_error": str(exc)[:120]}

    kospi_leg = (dual.get("legs") or {}).get("kospi") or {}
    btc_leg = (dual.get("legs") or {}).get("btc") or {}
    pooled = hit.get("metrics") or {}

    return {
        "schema": "commander_telegram_advanced_briefing_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "briefing_id": bid,
        "calendar_kst": cal,
        "generated_at_utc": _utc_now(),
        "generated_at_kst": now_kst,
        "fortune_path": str(fortune_path),
        "predictions": predictions,
        "n_predictions": len(predictions),
        "evening_score_scheduled": True,
        "market_seal": market_seal,
        "evening_score_note_ko": f"저녁 채점 briefing_id={bid} · KOSPI 당일·BTC 12h·NASDAQ 익일07:50",
        "sources": {
            "fortune": str(fortune_path),
            "kospi_brief": str(art / "internal_kospi_morning_brief_onepager_latest.json"),
            "dual_leg": str(art / "trackc_prophecy_dual_leg_brief_latest.json"),
        },
        "world_pulse": world,
        "hypothesis_stream": stream,
        "user_condition": cond,
        "market_observation": {
            "kospi_action": brief.get("today_action"),
            "kospi_confidence_0_100": brief.get("confidence_0_100"),
            "kospi_hit_rate_7d": brief.get("dual_leg_kospi_hit_rate") or kospi_leg.get("hit_rate"),
            "btc_hit_rate_7d": btc_leg.get("hit_rate"),
            "pooled_hit_rate": pooled.get("price_directional_hit_rate"),
            "macro_decision": (macro.get("market_snapshot") or {}).get("decision_state"),
            "news_confidence": (news.get("scores") or {}).get("confidence"),
        },
        "advisory_tilt": tilt,
        "telegram_sections": _build_telegram_sections(
            fortune,
            brief,
            dual,
            hypo_art,
            hit,
            bid=bid,
            now_kst=now_kst,
            market_seal=market_seal,
            workspace=workspace,
        ),
    }


def _today_three_actions(fortune: Dict[str, Any], cond: Dict[str, Any]) -> List[str]:
    """Actionable day openers from condition bands + hypothesis stream (non-clinical)."""
    actions: List[str] = []
    stress = str(cond.get("stress_band") or "").lower()
    energy = str(cond.get("energy_band") or "").lower()
    bio = str(cond.get("bio_synthesis_ko") or "")
    stream = fortune.get("hypothesis_stream") or {}
    market_tone = str(stream.get("market_tone") or "").lower()
    branches = stream.get("branches") or []
    has_sangwan = "상관" in bio or any(
        "상관" in str(br.get("trigger_ko") or "") for br in branches if isinstance(br, dict)
    )
    has_soeum = "소음" in bio or any("소음" in str(ln) for ln in fortune.get("mkm_ai_lines") or [])

    if stress in ("high", "elevated") or has_sangwan:
        actions.append("말·회의·기획은 핵심 1줄만 — 나머지 저녁 재검토")
    if energy in ("low", "mid") or has_soeum:
        actions.append("회복·페이싱 — 온수·식후 10~15분 보행·마이크로 투두(25+5)")
    if market_tone == "caution":
        actions.append("관측 우선 — 즉답·추격 결정 한 박자 지연")

    if not actions:
        actions = [
            "Fact-Lock·검증 마감 우선",
            "식후 스탠딩·짧은 보행",
            "핵심 1건 완료 후 다음",
        ]
    return actions[:3]


def _build_telegram_sections(
    fortune: Dict[str, Any],
    brief: Dict[str, Any],
    dual: Dict[str, Any],
    hypo_art: Dict[str, Any],
    hit: Dict[str, Any],
    *,
    bid: str,
    now_kst: str,
    market_seal: Optional[Dict[str, Any]] = None,
    workspace: Path = ROOT,
) -> List[str]:
    lines: List[str] = []
    world = fortune.get("world_pulse_fusion") or {}
    stream = fortune.get("hypothesis_stream") or {}
    cond = fortune.get("user_condition") or {}
    tilt = cond.get("advisory_investment_bias_tilt") or {}

    lines.extend(
        [
            f"📊 MKM 통합 장전 브리핑 · {now_kst}",
            f"briefing_id={bid} · [HYPO][NON_GATING]",
            "경계: 실매매·Track A 자동합선 없음 · 예측=가설·저녁 채점",
            "",
            "━━ I. 찰나의 나라 (세상×나) ━━",
            f"  융합: {world.get('fusion_one_liner_ko', '—')}",
        ]
    )
    for h in (world.get("headlines_top_ko") or [])[:3]:
        lines.append(f"  · 헤드라인: {str(h)[:160]}")
    for bl in (world.get("body_lines") or [])[:5]:
        lines.append(f"  {bl}")

    ms = market_seal or {}
    nas = ms.get("nasdaq_prior_session") or {}
    btc = ms.get("btc_usd") or {}
    kospi_seal = ms.get("kospi") or {}
    krx_sess = ms.get("krx_session") or {}
    banner = str(ms.get("session_banner_ko") or "").strip()
    lines.extend(
        [
            "",
            "━━ I-b. 거시·세계경제 밴드 ━━",
        ]
    )
    if banner:
        lines.append(f"  세션: {banner}")
    elif krx_sess.get("label_ko"):
        lines.append(f"  세션: 코스피 {krx_sess.get('label_ko')}")
    if not kospi_seal.get("trading_today", True):
        lines.append(
            f"  코스피: {kospi_seal.get('status_ko', '휴장')} — 당일 시세·적중 채점 없음 · 장전액션 HOLD(휴장)"
        )
    else:
        lines.append(
            f"  코스피 당일: {kospi_seal.get('direction', '—')} "
            f"({kospi_seal.get('return_pct', 'n/a')}%)"
        )
    lines.extend(
        [
            f"  BTC-USD seal: {btc.get('price', 'n/a')}",
            f"  NASDAQ prior: {nas.get('session_date', '—')} · {nas.get('direction', 'n/a')} "
            f"({nas.get('return_pct', 'n/a')}%)",
            f"  ({str(nas.get('note') or '')[:100]})",
            "  20:30 채점: KOSPI·BTC / NASDAQ→익일07:50",
        ]
    )

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from commander_telegram_rag_viz_bridge_v1 import (  # noqa: WPS433
            build_cross_lens_telegram_lines,
            build_sphere_rag_viz_telegram_lines,
        )

        lines.extend(
            ["", "━━ I-c. cross-lens RAG 융합 [HYPO] ━━", *build_cross_lens_telegram_lines(workspace)]
        )
        lines.extend(
            [
                "",
                "━━ I-d. 4RAG·그래프 (포인터·쇼룸) ━━",
                *build_sphere_rag_viz_telegram_lines(workspace),
            ]
        )
    except Exception as exc:  # noqa: BLE001
        lines.append(f"  (RAG·Viz 브리지 생략: {str(exc)[:100]})")

    lines.extend(["", "━━ II. 오늘 초론·예측 분기 ━━", f"  {stream.get('synthesis_ko', '—')}"])
    for i, br in enumerate(stream.get("branches") or [], start=1):
        lines.append(
            f"  P{i} [{br.get('confidence','—')}] {br.get('trigger_ko','')} "
            f"→ {br.get('predicted_bias_ko','')}"
        )

    lines.extend(["", "━━ III. 개인 일운 (압축) ━━"])
    for block_title, key, cap in (
        ("명리", "myeongni_lines", 5),
        ("4AI", "mkm_ai_lines", 6),
    ):
        block = fortune.get(key) or []
        if block:
            lines.append(f"  [{block_title}]")
            for ln in block[:cap]:
                s = str(ln).strip()
                if s:
                    lines.append(f"    {s[:160]}")

    tg = fortune.get("telegram_append_lines") or []
    skip_markers = ("찰나의 나라", "초론 스트림", "컨디션·바이어스", "개인 일운 (명리)", "개인 일운 (MKM")
    for raw in tg:
        ln = str(raw).strip()
        if not ln or any(m in ln for m in skip_markers):
            continue
        if "라이프" in ln or "성경 앵커" in ln:
            lines.append(f"  {ln[:180]}")

    lines.extend(
        [
            "",
            "━━ IV. 컨디션·바이어스 틸트 ━━",
            f"  밴드 sleep/energy/stress: {cond.get('sleep_band')}/{cond.get('energy_band')}/{cond.get('stress_band')}",
            f"  바이오: {cond.get('bio_synthesis_ko', '—')}",
            f"  투자틸트(참고): {tilt.get('tilt_ko', '—')}",
            "",
            "━━ IV-b. 오늘 3액션 [가설·생활참고] ━━",
        ]
    )
    for i, act in enumerate(_today_three_actions(fortune, cond), start=1):
        lines.append(f"  {i}. {act}")
    lines.extend(
        [
            "",
            "━━ V. 시장·예언 관측 (internal) ━━",
            f"  코스피 Final: {brief.get('today_action')} · 확신 {brief.get('confidence_0_100')}/100",
        ]
    )
    kospi_leg = (dual.get("legs") or {}).get("kospi") or {}
    btc_leg = (dual.get("legs") or {}).get("btc") or {}
    pooled = hit.get("metrics") or {}
    lines.append(f"  KOSPI 7d 적중 {_fmt_pct(kospi_leg.get('hit_rate'))} (n={kospi_leg.get('n_evaluated')})")
    lines.append(f"  BTC 7d 적중 {_fmt_pct(btc_leg.get('hit_rate'))} (n={btc_leg.get('n_evaluated')})")
    lines.append(f"  통합 {_fmt_pct(pooled.get('price_directional_hit_rate'))} (n={pooled.get('n_evaluated')})")
    pred = hypo_art.get("prediction") or {}
    lines.append(f"  B-track 가설: {pred.get('instrument')} {pred.get('direction')} conf={pred.get('confidence')}")

    lines.extend(
        [
            "",
            "━━ VI. 저녁 ━━",
            f"  20:30 채점 · id={bid} · [HYPO]",
        ]
    )
    return lines


def build_telegram_text(doc: Dict[str, Any], *, max_len: int = TELEGRAM_MAX) -> str:
    text = "\n".join(doc.get("telegram_sections") or []).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 24] + "\n…(4096자 초과·일부 생략)"


def archive_morning_briefing(doc: Dict[str, Any], workspace: Path = ROOT) -> Path:
    cal = str(doc.get("calendar_kst") or datetime.now(KST).strftime("%Y-%m-%d"))
    out_dir = workspace / "reports" / "briefing_log"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{cal}_morning_briefing_v1.json"
    envelope = {
        "schema": "commander_morning_briefing_archive_v1",
        "calendar_kst": cal,
        "archived_at_utc": _utc_now(),
        "briefing": doc,
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = workspace / "reports" / "commander_morning_briefing_latest.json"
    latest.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=DEFAULT_FORTUNE)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports" / "commander_advanced_briefing_latest.json")
    ap.add_argument("--archive", action="store_true", default=True)
    ap.add_argument("--stdout-text", action="store_true")
    args = ap.parse_args()

    doc = build_advanced_briefing_doc(fortune_path=args.fortune_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.archive:
        archive_morning_briefing(doc)
    print(f"WROTE: {args.out_json} predictions={doc.get('n_predictions')}")
    if args.stdout_text:
        print(build_telegram_text(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
