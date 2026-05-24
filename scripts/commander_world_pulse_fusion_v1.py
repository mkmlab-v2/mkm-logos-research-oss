#!/usr/bin/env python3
"""World pulse + '찰나의 나라' bridge — personal fortune × macro/news/KOSPI [HYPO][NON_GATING].

Reads existing B-track / Track C artifacts only (no live trading triggers).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ART = ROOT / "docs" / "final" / "artifacts"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
        if 0 <= x <= 1:
            return f"{x * 100:.1f}%"
        return f"{x:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pre_news_rows(workspace: Path) -> List[Dict[str, Any]]:
    doc = _read_json(workspace / "docs" / "final" / "artifacts" / "pre_news_shadow_input_latest.json")
    rows = doc.get("rows") or []
    return [r for r in rows if isinstance(r, dict) and str(r.get("headline") or "").strip()]


def _news_headlines_top(
    news: Dict[str, Any],
    *,
    workspace: Path = ROOT,
    max_n: int = 3,
) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    stream = news.get("news_stream_outputs") or {}
    digest = str(stream.get("digest") or "").strip()
    if digest:
        out.append(digest[:220])
        seen.add(digest[:80])
    for row in _pre_news_rows(workspace):
        h = str(row.get("headline") or "").strip()[:220]
        key = h[:80]
        if h and key not in seen:
            out.append(h)
            seen.add(key)
        if len(out) >= max_n:
            break
    ext = _read_json(workspace / "docs" / "final" / "artifacts" / "external_news_feed_latest.json")
    for item in (ext.get("items") or ext.get("headlines") or [])[: max_n * 2]:
        if isinstance(item, str):
            h = item.strip()[:220]
        elif isinstance(item, dict):
            h = str(item.get("headline") or item.get("title") or "").strip()[:220]
        else:
            continue
        key = h[:80]
        if h and key not in seen:
            out.append(h)
            seen.add(key)
        if len(out) >= max_n:
            break
    return out[:max_n]


def _news_headline(news: Dict[str, Any], *, workspace: Path = ROOT) -> str:
    tops = _news_headlines_top(news, workspace=workspace, max_n=1)
    return tops[0] if tops else ""


def _kospi_summary(kospi: Dict[str, Any], dual: Dict[str, Any]) -> Dict[str, Any]:
    action = str(kospi.get("today_action") or "—")
    conf = kospi.get("confidence_0_100")
    n = kospi.get("dual_leg_kospi_n_evaluated")
    hr = kospi.get("dual_leg_kospi_hit_rate")
    leg = ((dual.get("legs") or {}).get("kospi") or {}) if dual else {}
    if n is None:
        n = leg.get("n_evaluated")
    if hr is None:
        hr = leg.get("hit_rate")
    return {
        "today_action": action,
        "confidence_0_100": conf,
        "hit_rate": hr,
        "n_evaluated": n,
        "trackc_decision": kospi.get("trackc_api_decision_state"),
        "fallback_signal": kospi.get("fallback_signal"),
    }


def _macro_summary(macro: Dict[str, Any]) -> Dict[str, Any]:
    snap = macro.get("market_snapshot") or {}
    frame = macro.get("action_frame") or {}
    risks = macro.get("top_risk_signals") or []
    top = risks[0].get("name") if risks and isinstance(risks[0], dict) else ""
    return {
        "decision_state": snap.get("decision_state") or frame.get("label") or "—",
        "risk_warning_level": snap.get("risk_warning_level") or "—",
        "primary_regime_id": snap.get("primary_regime_id") or "—",
        "operator_posture": snap.get("recommended_operator_posture") or frame.get("operator_action") or "—",
        "asset_scope": snap.get("asset_scope") or "—",
        "top_risk_signal": top,
    }


def build_world_pulse(*, workspace: Path = ROOT) -> Dict[str, Any]:
    art = workspace / "docs" / "final" / "artifacts"
    kospi = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    news = _read_json(art / "news_independent_lens_latest.json")
    macro = _read_json(art / "trackc_macro_risk_morning_briefing_latest.json")
    dual = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")

    headline = _news_headline(news, workspace=workspace)
    headlines_top = _news_headlines_top(news, workspace=workspace, max_n=3)
    k = _kospi_summary(kospi, dual)
    m = _macro_summary(macro)

    news_conf = (news.get("scores") or {}).get("confidence")
    news_dir = (news.get("scores") or {}).get("direction_score")

    lines: List[str] = []
    if headlines_top:
        lines.append("  세상 헤드라인 Top:")
        for i, h in enumerate(headlines_top, start=1):
            lines.append(f"    {i}. {h[:180]}")
    elif headline:
        lines.append(f"  세상 한 줄: {headline}")
    else:
        lines.append("  세상 한 줄: (뉴스 피드 미갱신 — pre_news·news 렌즈 체인 참고)")

    try:
        from scripts.commander_market_session_calendar_v1 import krx_session_status  # noqa: WPS433

        krx_cal = krx_session_status()
        if not krx_cal.get("trading_today"):
            lines.append(f"  코스피·장면: 휴장 — {krx_cal.get('label_ko', '휴장')} · 액션 HOLD(휴장) 권장 [internal]")
            k = {**k, "today_action": "HOLD"}
        else:
            conf_s = k.get("confidence_0_100")
            conf_part = f" · 신뢰 {conf_s}/100" if conf_s is not None else ""
            hr_part = ""
            if k.get("hit_rate") is not None and k.get("n_evaluated"):
                hr_part = f" · B-track 적중 {_fmt_pct(k['hit_rate'])} (n={k['n_evaluated']})"
            elif k.get("n_evaluated") in (0, None) and k.get("hit_rate") is None:
                hr_part = " · 적중 통계 없음(관측만)"
            lines.append(
                f"  코스피·장면: {k['today_action']}{conf_part}{hr_part} [internal·관측]"
            )
    except Exception:
        conf_s = k.get("confidence_0_100")
        conf_part = f" · 신뢰 {conf_s}/100" if conf_s is not None else ""
        lines.append(f"  코스피·장면: {k.get('today_action')}{conf_part} [internal·관측]")

    regime = str(m.get("primary_regime_id") or "—").replace("_", " ")
    lines.append(
        f"  거시·세계경제: {m['decision_state']} · 리스크 {m['risk_warning_level']} · "
        f"판(場) {regime} · 자세 {m['operator_posture']} ({m['asset_scope']}) [가설]"
    )
    if m.get("top_risk_signal"):
        lines.append(f"  거시 신호(1순위): {m['top_risk_signal']} [관측]")
    if news_conf is not None:
        lines.append(
            f"  뉴스 렌즈: 방향점수 {news_dir} · 신뢰 {news_conf} — 키워드 틸트만, 매매 아님"
        )

    lines.append(
        "  경계: 투자·실매매·임상 단정 없음 · 관측·가이드 전용 [NON_GATING][가설]"
    )

    try:
        from commander_telegram_rag_viz_bridge_v1 import append_rag_viz_to_body_lines  # noqa: WPS433

        append_rag_viz_to_body_lines(lines, workspace=workspace)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"  (RAG·그래프 브리지 생략: {str(exc)[:80]})")

    return {
        "schema": "commander_world_pulse_fusion_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "concept_ko": "찰나의 나라 — 오늘의 나(명리)와 오늘의 판(뉴스·코스피·거시)을 겹쳐 보는 융합 가이드",
        "headline_ko": headline,
        "headlines_top_ko": headlines_top,
        "kospi": k,
        "macro": m,
        "news": {
            "direction_score": news_dir,
            "confidence": news_conf,
            "headline_count": (news.get("news_stream_outputs") or {}).get("headline_count"),
        },
        "evidence_paths": [
            str(art / "internal_kospi_morning_brief_onepager_latest.json"),
            str(art / "news_independent_lens_latest.json"),
            str(art / "trackc_macro_risk_morning_briefing_latest.json"),
            str(art / "trackc_prophecy_dual_leg_brief_latest.json"),
        ],
        "body_lines": lines,
    }


def _clean_myeongni_snippet(line: str) -> str:
    s = (line or "").strip()
    for prefix in ("▸ 오늘 한 줄:", "오늘 한 줄:", "▸ "):
        if s.startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    return s


def build_fusion_one_liner(
    myeongni_one_liner: str,
    world: Dict[str, Any],
) -> str:
    """Cross-layer narrative (pedagogical, not prediction)."""
    personal = _clean_myeongni_snippet(myeongni_one_liner)
    if len(personal) > 120:
        personal = personal[:117] + "…"
    k_action = ((world.get("kospi") or {}).get("today_action")) or "—"
    headline = (world.get("headline_ko") or "").strip()
    macro_state = ((world.get("macro") or {}).get("decision_state")) or "—"
    parts = []
    if personal:
        parts.append(f"나: {personal}")
    parts.append(f"판: 장면 {k_action} · 거시 {macro_state}")
    if headline:
        short_h = headline[:60] + ("…" if len(headline) > 60 else "")
        parts.append(f"세상: {short_h}")
    parts.append("→ 말·결정은 짧게, 관측·페이싱 우선 [가설]")
    return " · ".join(parts)


def append_world_pulse_telegram(
    telegram_lines: List[str],
    *,
    myeongni_lines: List[str],
    workspace: Path = ROOT,
) -> Dict[str, Any]:
    world = build_world_pulse(workspace=workspace)
    one_liner = ""
    for ln in myeongni_lines:
        if "오늘 한 줄" in ln:
            one_liner = ln.strip()
            break
    fusion = build_fusion_one_liner(one_liner, world)
    world["fusion_one_liner_ko"] = fusion

    telegram_lines.extend(
        [
            "",
            "▸ 찰나의 나라 (세상×나) [가설]",
            f"  융합 한 줄: {fusion}",
            *(world.get("body_lines") or []),
        ]
    )
    return world
