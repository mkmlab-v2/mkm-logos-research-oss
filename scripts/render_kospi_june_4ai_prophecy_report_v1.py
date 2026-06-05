#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render commander-facing June KOSPI 4AI prophecy report (Markdown) [HYPO]."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KST = ZoneInfo("Asia/Seoul")
DEFAULT_JSON = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.md"
DEFAULT_DOC = ROOT / "reports/kospi_june2026_prophecy_document_v1.md"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_june2026_4ai_prophecy_report_latest.md"
DEFAULT_ART_DOC = ROOT / "docs/final/artifacts/kospi_june2026_prophecy_document_v1.md"
CROSSWALK_JSON = ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _last_kospi_close() -> float | None:
    if not KOSPI_CSV.is_file():
        return None
    last = None
    with KOSPI_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date", ""))[:10]
            if len(dk) != 10:
                continue
            try:
                last = (dk, float(row["Close"]))
            except (KeyError, ValueError, TypeError):
                continue
    return last[1] if last else None


def _fmt_mid(val: Any) -> str:
    try:
        return f"{float(val):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_band(pair: Any) -> str:
    if not isinstance(pair, (list, tuple)) or len(pair) < 2:
        return "—"
    try:
        lo, hi = float(pair[0]), float(pair[1])
        return f"{lo:,.0f}–{hi:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _pillars_line(pillars: Any) -> str:
    if not isinstance(pillars, dict):
        return "—"
    parts = [pillars.get("year"), pillars.get("month"), pillars.get("day"), pillars.get("hour")]
    text = " ".join(str(p) for p in parts if p)
    return text or "—"


def _agent_compact(agents: Any) -> str:
    if not isinstance(agents, list):
        return "—"
    bits: list[str] = []
    for a in agents:
        if not isinstance(a, dict):
            continue
        label = a.get("label_ko") or a.get("agent_id") or "?"
        d = a.get("direction_ko") or a.get("direction") or "—"
        bits.append(f"{label}:{d}")
    return " · ".join(bits) if bits else "—"


def _logos_crosswalk_section() -> list[str]:
    cw = _read_json(CROSSWALK_JSON)
    if cw.get("schema") != "kospi_june2026_logos_anchor_crosswalk_v1":
        return []
    anchors = cw.get("anchors") or []
    if not anchors:
        return []
    lines = [
        "## 2.5 Logos 앵커 crosswalk (`[NON_GATING]`)",
        "",
        f"- **SSOT:** `reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json` · primary topic: `{((cw.get('summary') or {}).get('primary_topic'))}`",
        f"- **GraphRAG seed hits:** {(cw.get('summary') or {}).get('graphrag_seed_hits_ssot', '—')}",
        f"- **역할:** 성경(Logos) = 해설·내러티브 앵커만 — **가격·주문 트리거 아님**",
        "",
        "| topic | weight | router overlap | graphrag ref |",
        "|-------|--------|----------------|--------------|",
    ]
    for a in anchors:
        if not isinstance(a, dict):
            continue
        overlap = ", ".join(a.get("router_overlap") or []) or "—"
        ref = str(a.get("graphrag_ref") or "—").replace("reports/", "")
        lines.append(
            f"| `{a.get('topic_id')}` | {a.get('weight', '—')} | {overlap} | `{ref}` |"
        )
    lines.extend(
        [
            "",
            f"- **gold q09:** election topic CPU eval — `docs/final/fixtures/logos_gold_query_eval_v1.json` (id `q09`)",
            "- **재현:** `py scripts/materialize_logos_gold_q09_election_router_ann_v1.py` → `build_logos_gold_query_eval_report_v1.py`",
            "",
        ]
    )
    return lines


def _channel_votes_line(blend: Any) -> str:
    if not isinstance(blend, dict):
        return "—"
    votes = blend.get("votes")
    if not isinstance(votes, dict):
        return "—"
    return f"상 {votes.get('bull', 0):.2f} / 횡 {votes.get('neutral', 0):.2f} / 하 {votes.get('bear', 0):.2f}"


def render_markdown(doc: dict[str, Any], *, calendar: dict[str, Any] | None = None) -> str:
    rows = doc.get("rows") or []
    eval_s = doc.get("eval_summary") if isinstance(doc.get("eval_summary"), dict) else {}
    exec_s = doc.get("executive_summary_ko") if isinstance(doc.get("executive_summary_ko"), dict) else {}
    blend_note = doc.get("blend_formula_note") if isinstance(doc.get("blend_formula_note"), dict) else {}
    as_of = eval_s.get("as_of_kst") or _today_kst()
    anchor = _last_kospi_close()
    anchor_s = f"≈ {anchor:,.0f}" if anchor is not None else "확인 필요"
    status = str(doc.get("status") or "WATCH")
    content_hash = str(doc.get("content_hash") or "—")

    metrics = eval_s.get("metrics") if isinstance(eval_s.get("metrics"), dict) else {}
    n_scored = eval_s.get("n_scored", 0)
    soft = metrics.get("soft_hit_rate")
    dir_hr = metrics.get("directional_hit_rate")
    missing = eval_s.get("missing_ohlcv_trading_days") or []
    vendor_inc = eval_s.get("vendor_incomplete_trading_days") or []
    cal_by_date: dict[str, dict[str, Any]] = {}
    if calendar:
        for cr in calendar.get("rows") or []:
            sd = str(cr.get("session_date") or "")
            if sd:
                cal_by_date[sd] = cr

    lines: list[str] = [
        "# 2026년 6월 코스피 일자별 예언 종합 보고서 (4AI · v2_multilens)",
        "",
        f"기준일: {as_of} | 운영 레일: B-track `[HYPO]` | 기밀 등급: research_only",
        f"해시: `{content_hash}` | 상태: **{status}** (안정 관측)",
        "",
        "## 0. 지휘관용 핵심 요약",
        "",
        f"- **전술 스탠스:** {exec_s.get('stance', '횡보·관측 우세')} — 하락 **{exec_s.get('bear_days', 0)}** / 횡보·관측 **{exec_s.get('observe_days', 0)}** / 상승 **{exec_s.get('bull_days', 0)}** ({exec_s.get('n_trading_days', len(rows))}거래일)",
        f"- **v2 정렬:** **{exec_s.get('v2_alignment_days', 0)}/{exec_s.get('n_trading_days', len(rows))}**일 일치 (rate={exec_s.get('v2_alignment_rate', '—')})",
        f"- **4AI 독립 합의:** **{exec_s.get('autonomous_consensus_days', '—')}**일 "
        f"(rate={exec_s.get('autonomous_consensus_rate', '—')}) · 가중합의 **{exec_s.get('weighted_agree_days', 0)}**일 · "
        f"채널앵커 **{exec_s.get('channel_anchor_days', 0)}**일 · KPI **{exec_s.get('coordinator_kpi_status', '—')}**",
        f"- **기준선 앵커:** 최근 실측 종가 **{anchor_s}** (yfinance CSV)",
        "- **격벽:** Track A·실매매 API 비연동 · evolution `--apply-approved` 전 자동 가중치 병합 없음",
        "",
        "> 4AI 오버레이는 8채널 v2 위 **서술·조율층**입니다. temperament sim·12AI 라우터와 **동일 런타임 아님**.",
        "",
        "## 1. 3층 융합 구조",
        "",
        "**활성 엔진 (v2):** 8채널 `v2_multilens` — 세션명리·독립3렌즈·Field·모멘텀·KOSPI 인과 앙상블",
        "",
        "**4AI 오버레이 (본 보고서 표):**",
        "",
        "| 4AI | 담당 채널 | 역할 [HYPO] |",
        "|-----|-----------|-------------|",
        "| 태양 | 모멘텀, Field | 확장·레짐 변동 |",
        "| 소양 | 세션명리, 독립명리 | 일진·중기 파동 |",
        "| 태음 | 거시, KOSPI 앙상블 | 구조·인과 융합 |",
        "| 소음 | 사상, 성경 | 강도·`[NON_GATING]` 감쇠 |",
        "",
        "**조율:** Absolute Balance Coordinator — 에이전트 일치 시 평균 점수; **충돌 시 8채널 v2 합의로 앵커** (v2_multilens 정렬)",
        "",
        f"*(구 문서 v1 식: {blend_note.get('v1_legacy_doc', '—')} — 참고용 레거시)*",
        "",
        "## 2. 4AI 조율 KPI",
        "",
    ]
    ckpi = doc.get("coordinator_kpi") if isinstance(doc.get("coordinator_kpi"), dict) else {}
    if ckpi:
        tgt = ckpi.get("targets") if isinstance(ckpi.get("targets"), dict) else {}
        lines.extend(
            [
                f"- **상태:** `{ckpi.get('status', '—')}`"
                + (f" — {', '.join(ckpi.get('notes') or [])}" if ckpi.get("notes") else ""),
                f"- **독립 합의율:** {ckpi.get('autonomous_consensus_rate', '—')} "
                f"(목표 ≥ {tgt.get('min_autonomous_consensus_rate', '—')})",
                f"- **채널 앵커율:** {ckpi.get('channel_anchor_rate', '—')} "
                f"(목표 ≤ {tgt.get('max_channel_anchor_rate', '—')})",
                f"- **v2 정렬율:** {ckpi.get('v2_alignment_rate', '—')} "
                f"(목표 ≥ {tgt.get('min_v2_alignment_rate', '—')})",
                "",
            ]
        )
    else:
        lines.append("- (KPI 블록 없음 — overlay 재실행 필요)")
        lines.append("")

    lines.extend(_logos_crosswalk_section())

    lines.extend(
        [
        "## 3. 월간 전망 (한 줄)",
        "",
        f"- **6월 거래일 {exec_s.get('n_trading_days', len(rows))}일** 중 **하락 {exec_s.get('bear_days', 0)}일** · **횡보·관측 {exec_s.get('observe_days', 0)}일** · 상승 {exec_s.get('bull_days', 0)}일",
        "- **초반(6/1–6/5):** 횡보·관측과 하락 혼재 — 데이터 결측일(6/3–6/4) 주의",
        "- **중순 이후:** 하락 우세 구간 다수; 6/11 옵션만기 전후는 횡보·관측 유지",
        "- **지수 밴드:** 아래 표 `종가 밴드`는 참고용; 실측 OHLCV와 괴리 시 evening loop로 갱신",
        "",
        "## 4. 일자별 예측 캘린더 (4AI · 22거래일)",
        "",
        "⚠️ 지수 mid·밴드는 참고용입니다. **4AI 방향** = 지휘관용; **v2** = 8채널 기술 산출.",
        "",
        "| 일자 | 요일 | 4AI | v2 | 종가 mid | 종가 밴드 | 8채널 득표 | 조율 |",
        "|------|------|-----|-----|----------|-----------|------------|------|",
        ]
    )

    for r in rows:
        sd = str(r.get("session_date") or "")
        dk = sd[5:] if len(sd) >= 10 else sd
        wd = r.get("weekday_ko") or ""
        f4 = r.get("four_ai_direction_ko") or "—"
        v2 = r.get("v2_multilens_direction_ko") or "—"
        wf = r.get("weight_field") or "—"
        note = ""
        if dk == "06-11":
            note = " ※옵션만기"
        cal_row = cal_by_date.get(sd, {})
        band_doc = cal_row.get("kospi_index_prophecy") if isinstance(cal_row.get("kospi_index_prophecy"), dict) else {}
        mid = _fmt_mid(band_doc.get("predicted_close_mid") or r.get("reference_close_mid"))
        close_band = _fmt_band(band_doc.get("predicted_close_band"))
        votes = _channel_votes_line(cal_row.get("blend"))
        lines.append(f"| {dk} | {wd}{note} | {f4} | {v2} | {mid} | {close_band} | {votes} | `{wf}` |")

    lines.extend(
        [
            "",
            "## 5. 일자별 상세 (명리·4AI)",
            "",
        ]
    )
    for r in rows:
        sd = str(r.get("session_date") or "")
        dk = sd[5:] if len(sd) >= 10 else sd
        wd = r.get("weekday_ko") or ""
        cal_row = cal_by_date.get(sd, {})
        pillars = _pillars_line(cal_row.get("pillars_session"))
        f4 = r.get("four_ai_direction_ko") or "—"
        agents = _agent_compact(r.get("four_ai_agents"))
        ab = r.get("absolute_balance") if isinstance(r.get("absolute_balance"), dict) else {}
        anchor = ab.get("anchor_reason")
        anchor_note = f" (앵커: {anchor})" if anchor else ""
        lines.append(f"### {dk} ({wd}) — {f4}{anchor_note}")
        lines.append("")
        lines.append(f"- **세션 사주:** {pillars}")
        lines.append(f"- **4AI 투표:** {agents}")
        if ab.get("channel_consensus"):
            cc = ab["channel_consensus"]
            lines.append(
                f"- **8채널 합의:** {cc.get('direction_ko', '—')} (`{cc.get('resolution_mode', '—')}`)"
            )
        lines.append("")

    lines.extend(
        [
            "",
            "## 6. 평가 및 자율진화",
            "",
            "### 6.1 누적 채점 (as-of " + str(as_of) + ")",
            "",
            f"- **n_scored:** {n_scored}",
            f"- **soft_hit_rate:** {soft if soft is not None else 'null'}",
            f"- **directional_hit_rate:** {dir_hr if dir_hr is not None else 'null'}",
        ]
    )
    if missing:
        lines.append(f"- **OHLCV 결측:** {', '.join(missing) or '—'} (행 없음)")
    if vendor_inc:
        lines.append(
            f"- **vendor_incomplete:** {', '.join(vendor_inc)} (Yahoo Close 무효 — fetch 대기·수동보정 금지)"
        )

    scored_rows = eval_s  # eval rows not embedded in 4ai json - read from separate if needed
    lines.extend(["", "| 일자 | 4AI/v2 예측 | 실제 | 판정 | 밴드 |", "|------|-------------|------|------|------|"])

    # Pull eval rows from eval file path in overlay - we need eval rows in render
    eval_path = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    eval_doc = _read_json(eval_path)
    row_by_date = {str(r.get("session_date")): r for r in doc.get("rows") or []}
    for er in eval_doc.get("rows") or []:
        sd = str(er.get("session_date") or "")
        cal_row = row_by_date.get(sd, {})
        pred = cal_row.get("four_ai_direction_ko") or er.get("predicted_direction") or "—"
        actual = er.get("actual_direction") or "—"
        outcome = er.get("outcome") or "—"
        band = "적중" if er.get("band_hit") is True else ("이탈" if er.get("band_hit") is False else "—")
        lines.append(f"| {sd[5:]} | {pred} | {actual} | {outcome} | {band} |")

    if not (eval_doc.get("rows") or []):
        lines.append("| — | (채점 없음) | — | — | — |")

    compare_path = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"
    compare_doc = _read_json(compare_path)
    lines.extend(
        [
            "",
            "### 6.2 자율진화",
            "",
            "- **조건:** n≥3 및 soft≤0.35 또는 ≥0.55 → 가중치 제안 (기본 dry-run)",
            "- **적용:** `py scripts/run_kospi_june2026_prophecy_evolution_v1.py --apply-approved` (지휘관 승인 후)",
        ]
    )
    if compare_doc.get("schema") == "kospi_june2026_weight_candidate_compare_v1":
        ac = compare_doc.get("direction_counts", {}).get("active") or {}
        cc = compare_doc.get("direction_counts", {}).get("candidate") or {}
        bt = compare_doc.get("backtest_delta") or {}
        promo = compare_doc.get("promotion_recommendation") or {}
        apply_st = compare_doc.get("weight_apply_status") if isinstance(compare_doc.get("weight_apply_status"), dict) else {}
        already_applied = bool(
            apply_st.get("candidate_already_applied") or promo.get("candidate_already_applied")
        )
        section_lines = [
            "",
            "### 6.3 가중치 후보 (shadow · active vs candidate)",
            "",
            f"- **후보 ID:** `{compare_doc.get('candidate_id')}` ({compare_doc.get('candidate_status')})",
            f"- **6월 방향 분포 — active:** {ac} · **candidate:** {cc}",
            f"- **방향 불일치 일수:** {compare_doc.get('n_direction_diffs', 0)} / {compare_doc.get('n_trading_days', 0)}",
            f"- **백테스트 soft Δ (candidate−active):** {bt.get('soft_hit_rate_delta_candidate_minus_active', '—')} "
            f"(필요 ≥ {((compare_doc.get('effective_weight_candidate_policy') or compare_doc.get('weight_candidate_policy') or {}).get('min_backtest_soft_delta_vs_active', '—'))})",
        ]
        if already_applied:
            section_lines.extend(
                [
                    f"- **적용 상태:** 완료 · `{apply_st.get('last_candidate_apply_at_utc', '—')}`",
                    f"- **승격 검토:** 불필요 (active=candidate) · blockers: —",
                    "- **다음:** June 포워드 n_scored 누적 모니터링 (§6.3b)",
                ]
            )
        else:
            section_lines.extend(
                [
                    f"- **승격 검토 가능:** {promo.get('ready_for_apply_review', False)} · blockers: {', '.join(promo.get('blockers') or []) or '—'}",
                    f"- **적용 명령(승인 후):** `{promo.get('apply_command', '—')}`",
                ]
            )
        lines.extend(section_lines)
        wf = compare_doc.get("walkforward_prefilter")
        pol = compare_doc.get("weight_candidate_policy") or {}
        if isinstance(wf, dict):
            lines.extend(
                [
                    f"- **WF 게이트:** top1 {wf.get('selection_top1_hit_rate', '—')} "
                    f"(필요 ≥ {wf.get('min_selection_top1_hit_rate', '—')}) · "
                    f"top2 포함 {wf.get('candidate_in_top2', '—')} · pass={wf.get('walkforward_gate_pass', '—')}",
                ]
            )
        if pol.get("policy_tier"):
            lines.extend([f"- **정책 tier:** `{pol.get('policy_tier')}` · 포워드 min={pol.get('june_forward_min_scored_for_promotion', '—')}"])

    shadow_panel = _read_json(ROOT / "reports/kospi_june2026_shadow_candidate_panel_latest.json")
    if shadow_panel.get("schema") == "kospi_june2026_shadow_candidate_panel_v1":
        active_fwd = shadow_panel.get("active_forward") if isinstance(shadow_panel.get("active_forward"), dict) else {}
        lines.extend(
            [
                "",
                "### 6.3f Shadow 병렬 패널 (apply arm vs research_shadow)",
                "",
                f"- **applied active:** `{shadow_panel.get('applied_active_id')}` "
                f"({shadow_panel.get('applied_active_at_utc', '—')})",
                f"- **active 포워드:** n_scored={active_fwd.get('n_scored', '—')} · "
                f"soft={((active_fwd.get('metrics') or {}).get('soft_hit_rate', '—'))}",
                f"- **SSOT:** `reports/kospi_june2026_shadow_candidate_panel_latest.json` · "
                f"log `{shadow_panel.get('panel_log', 'reports/kospi_june2026_shadow_panel_log.jsonl')}`",
                "- **auto_apply:** false · Track A·실매매 합선 금지",
            ]
        )
        for row in shadow_panel.get("shadows") or []:
            fwd = row.get("forward_eval") if isinstance(row.get("forward_eval"), dict) else {}
            cand_fwd = fwd.get("candidate") if isinstance(fwd.get("candidate"), dict) else {}
            lines.extend(
                [
                    f"- **shadow `{row.get('candidate_id')}`:** "
                    f"캘린더 방향 diff {row.get('n_calendar_direction_diffs', '—')}/{row.get('n_trading_days', '—')} · "
                    f"포워드 soft {((cand_fwd.get('metrics') or {}).get('soft_hit_rate', '—'))} "
                    f"(Δ vs active {fwd.get('soft_delta_candidate_minus_active', '—')}) · "
                    f"승격검토={((row.get('promotion_recommendation') or {}).get('ready_for_apply_review', False))}",
                ]
            )
        lb = shadow_panel.get("leaderboard_forward_soft") or []
        if lb:
            lb_txt = ", ".join(
                f"{x.get('candidate_id')}={x.get('soft_hit_rate', '—')}" for x in lb if isinstance(x, dict)
            )
            lines.extend([f"- **포워드 soft 순위:** {lb_txt}"])
        scored = shadow_panel.get("scored_day_arm_diff") if isinstance(shadow_panel.get("scored_day_arm_diff"), dict) else {}
        summ = scored.get("summary") if isinstance(scored.get("summary"), dict) else {}
        if int(scored.get("n_scored_days") or 0) > 0:
            lines.extend(
                [
                    f"- **채점일 arm diff:** {summ.get('n_days_any_shadow_direction_diff', '—')}/"
                    f"{scored.get('n_scored_days')}일 방향 불일치 · "
                    f"shadow soft 우위 {summ.get('n_days_shadow_soft_beat_active', '—')}일",
                ]
            )
            for day in scored.get("days") or []:
                if not isinstance(day, dict):
                    continue
                dk = day.get("session_date")
                arms = day.get("arms") or []
                arm_txt = ", ".join(
                    f"{a.get('arm_id')}={a.get('predicted_direction')}"
                    for a in arms
                    if isinstance(a, dict)
                )
                lines.append(
                    f"  - `{dk}` actual={day.get('actual_direction')} · {arm_txt}"
                )

    rollup = _read_json(ROOT / "reports/kospi_june2026_shadow_panel_rollup_latest.json")
    if rollup.get("schema") == "kospi_june2026_shadow_panel_rollup_v1":
        delta = rollup.get("delta_first_to_last") if isinstance(rollup.get("delta_first_to_last"), dict) else {}
        leader = rollup.get("leader_by_last_forward_soft") if isinstance(rollup.get("leader_by_last_forward_soft"), dict) else {}
        lines.extend(
            [
                "",
                "### 6.3g Shadow log rollup (포워드 추이)",
                "",
                f"- **log entries:** {rollup.get('n_log_entries', '—')} · SSOT: `reports/kospi_june2026_shadow_panel_rollup_latest.json`",
                f"- **Δ n_scored (first→last):** {delta.get('active_n_scored', '—')} · "
                f"**Δ soft:** {delta.get('active_soft_hit_rate', '—')}",
                f"- **last leader (forward soft):** `{leader.get('candidate_id', '—')}` "
                f"soft={leader.get('soft_hit_rate', '—')} ({leader.get('role', '—')})",
                "- **auto_apply:** false",
            ]
        )

    walk_path = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
    walk = _read_json(walk_path)
    if walk.get("schema") == "kospi_multilens_walkforward_backtest_v1":
        summ = walk.get("summary") if isinstance(walk.get("summary"), dict) else {}
        rec = summ.get("recommended_prefilter_variants_top2") or []
        hit = summ.get("selection_top1_hit_rate", "—")
        lines.extend(
            [
                "",
                "### 6.3d 30년 워크포워드 프리필터 (후보 압축)",
                "",
                f"- **fold 수:** {walk.get('folds', []) and len(walk.get('folds') or []) or '—'}",
                f"- **top1 selection hit-rate:** {hit}",
                f"- **추천 top2:** {', '.join([str(x) for x in rec]) or '—'}",
                "- **주의:** 이는 후보 압축용. June forward 게이트 + 인간 signoff가 최종 기준.",
            ]
        )

    btc_xcheck = _read_json(ROOT / "reports/btc_multilens_cross_check_summary_latest.json")
    if btc_xcheck.get("schema") == "btc_multilens_cross_check_summary_v1":
        l3 = btc_xcheck.get("v2_lens3_heavy") if isinstance(btc_xcheck.get("v2_lens3_heavy"), dict) else {}
        full_m = (l3.get("btc_full_window") or {}).get("metrics") if isinstance(l3.get("btc_full_window"), dict) else {}
        w140 = (l3.get("btc_140d_window") or {}).get("metrics") if isinstance(l3.get("btc_140d_window"), dict) else {}
        k140 = (l3.get("kospi_140d_reference") or {}).get("metrics") if isinstance(l3.get("kospi_140d_reference"), dict) else {}
        wf = btc_xcheck.get("btc_walkforward") if isinstance(btc_xcheck.get("btc_walkforward"), dict) else {}
        combo = btc_xcheck.get("instrument_combo_walkforward") if isinstance(btc_xcheck.get("instrument_combo_walkforward"), dict) else {}
        csv_meta = btc_xcheck.get("btc_csv") if isinstance(btc_xcheck.get("btc_csv"), dict) else {}
        lines.extend(
            [
                "",
                "### 6.3e BTC 교차 검증 (v2_lens3_heavy · shadow)",
                "",
                f"- **SSOT:** `reports/btc_multilens_cross_check_summary_latest.json` (as-of {btc_xcheck.get('generated_at_utc', '—')})",
                f"- **BTC OHLCV:** {csv_meta.get('rows', '—')}일 (Yahoo `BTC-USD`; 실질 시작 2014-09-17 근처)",
                f"- **전구간 soft/dir (BTC 수익률):** {full_m.get('soft_hit_rate', '—')} / {full_m.get('directional_hit_rate', '—')} "
                f"(n={full_m.get('n_scored', '—')})",
                f"- **140일창 — BTC:** soft {w140.get('soft_hit_rate', '—')} · **KOSPI 참조:** soft {k140.get('soft_hit_rate', '—')} "
                f"(Δ {l3.get('delta_btc_minus_kospi_soft_140d', '—')})",
                f"- **BTC WF top2:** {', '.join([str(x) for x in (wf.get('top2') or [])]) or '—'} · "
                f"lens3 family 포함: {wf.get('v2_lens3_heavy_in_top2', '—')}",
                f"- **instrument combo WF:** folds={combo.get('n_folds', '—')} · mean_test_acc={combo.get('mean_test_accuracy', '—')}",
                f"- **판정:** {btc_xcheck.get('verdict_ko', '—')}",
                "- **격벽:** June apply·Track A·실매매 **자동 합선 없음** (`research_only`)",
                "- **재현:** `powershell -File scripts/Run-BtcMultilensResearchCrossCheck_v1.ps1`",
            ]
        )

    readiness_path = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
    readiness = _read_json(readiness_path)
    if readiness.get("schema") == "kospi_june2026_promotion_readiness_v1":
        fs = readiness.get("forward_scoring") if isinstance(readiness.get("forward_scoring"), dict) else {}
        lines.extend(
            [
                "",
                "### 6.3b 승격 readiness (포워드 누적)",
                "",
                f"- **n_scored:** {fs.get('n_scored', '—')} / {fs.get('min_required', '—')} "
                f"(남음 {fs.get('remaining_to_gate', '—')} · {fs.get('progress_pct', '—')}%)",
                f"- **미채점( OHLCV 가능):** {fs.get('unscored_eligible_trading_days', '—')} · "
                f"**게이트까지 예상 거래일:** {fs.get('projected_trading_days_to_gate', '—')}",
                f"- **OHLCV 결측:** {', '.join(fs.get('missing_ohlcv') or []) or '—'} · "
                f"**vendor_incomplete:** {', '.join(fs.get('vendor_incomplete_trading_days') or []) or '—'}",
                f"- **게이트 예상일(세션):** {fs.get('projected_gate_session_date', '—')} · "
                f"월내 도달 가능: {fs.get('gate_reachable_in_month', '—')}",
                f"- **ETA:** {fs.get('eta_note_ko', '—')}",
                f"- **정책 tier:** {readiness.get('policy_tier', '—')}",
                f"- **백테스트 soft Δ 통과:** {readiness.get('gates', {}).get('backtest_soft_delta', {}).get('pass', '—')}",
                f"- **WF prefilter 통과:** {readiness.get('gates', {}).get('walkforward_prefilter', {}).get('pass', '—')}",
                f"- **프록시 forward ({readiness.get('gates', {}).get('proxy_forward_substitute', {}).get('proxy_year_month', '—')}):** "
                f"{readiness.get('gates', {}).get('proxy_forward_substitute', {}).get('actual', '—')}/"
                f"{readiness.get('gates', {}).get('proxy_forward_substitute', {}).get('required_min', '—')} · "
                f"via={readiness.get('gates', {}).get('proxy_forward_substitute', {}).get('forward_gate_via', '—')}",
                f"- **자동 게이트(인간 제외):** {readiness.get('auto_gates_pass_pending_human', '—')}",
                f"- **인간 sign-off:** {readiness.get('gates', {}).get('human_signoff', {}).get('pass', '—')} "
                f"({readiness.get('gates', {}).get('human_signoff', {}).get('signed_at_utc', '—')})",
                f"- **적용 완료:** {readiness.get('candidate_already_applied', False)}",
                f"- **판정:** {readiness.get('verdict_ko', '—')}",
            ]
        )
    shadow = compare_doc.get("shadow_horizon_contract") if compare_doc.get("schema") == "kospi_june2026_weight_candidate_compare_v1" else None
    if isinstance(shadow, dict) and shadow.get("schema") == "kospi_june2026_myeongni_horizon_shadow_v1":
        lines.extend(
            [
                "",
                "### 6.3c 명리 호라이즌 shadow (v2 그리드 · apply 별도)",
                "",
                f"- **shadow ID:** `{shadow.get('shadow_candidate_id')}` ({shadow.get('status')})",
                f"- **계약(활성):** {shadow.get('contract_horizon_active')} · **shadow 최적:** {shadow.get('shadow_horizon')}",
                f"- **soft — 계약:** {shadow.get('contract_soft_hit_rate', '—')} · shadow: {shadow.get('shadow_soft_hit_rate', '—')} "
                f"(Δ {shadow.get('soft_delta_shadow_minus_contract', '—')})",
                f"- **contract_is_best:** {shadow.get('contract_is_best')} · **promotion_ready:** {shadow.get('promotion_ready', False)}",
                f"- **근거:** `{shadow.get('evidence_path', '—')}`",
            ]
        )

    horizon_v2_path = ROOT / "reports/three_lens_horizon_empirical_eval_v2_latest.json"
    horizon_v2 = _read_json(horizon_v2_path)
    if horizon_v2.get("schema") == "three_lens_horizon_empirical_eval_v2":
        summary = horizon_v2.get("summary") if isinstance(horizon_v2.get("summary"), dict) else {}
        lines.extend(
            [
                "",
                "### 6.4 렌즈 역할-호라이즌 실증 (v2 · B-track)",
                "",
                f"- **SSOT:** `reports/three_lens_horizon_empirical_eval_v2_latest.json` (as-of {horizon_v2.get('generated_at_utc', '—')})",
                f"- **윈도우:** {horizon_v2.get('date_from', '—')} ~ {horizon_v2.get('date_to', '—')}",
                "- **역할 계약:** 성경=거시(21d)·명리=중기(10d)·사상=단기(1d) — **실증 통과 아님** (`research_only`)",
            ]
        )
        for leg_key in ("kospi", "btc"):
            leg_sum = summary.get(leg_key) if isinstance(summary.get(leg_key), dict) else {}
            if not leg_sum:
                continue
            lines.append(
                f"- **{leg_key.upper()}:** v1={leg_sum.get('v1_supported')} · v2={leg_sum.get('v2_supported')} · "
                f"명리최적={leg_sum.get('myeongni_best')} · Logos변종={leg_sum.get('logos_best_variant')}"
            )
        lines.append(
            "- **사상 강도 게이트:** `intensity_pass`=순위상관(주) · `intensity_alert_pass`=고스트레스 sweep(보조)"
        )
        lines.append(
            "- **재현:** `py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument both --date-from 2026-01-01 --date-to 2026-04-30`"
        )

    lines.extend(
        [
            "",
            "## 7. 면책 및 파이어월",
            "",
            "- 본 문서는 B-track `[HYPO]` 연구 산출이며 **Track A·실매매 트리거가 아님**.",
            "- `integration_pct`·밴드 mid는 **배선 깊이/참고 밴드**이지 적중률 증명이 아님.",
            "- 성경(Logos) 채널은 `[NON_GATING]` 보조 해설.",
            "",
            "### 파이어월",
            "",
            "```",
            "[B-track 예언] ──(격리)──▶ [Track A] & [실매매 API]",
            "  캘린더·4AI·채점·진화 (O)     LOCKED_MODE · NO_GO 유지",
            "```",
            "",
            "## 8. 재현",
            "",
            "```powershell",
            "py scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py --year-month 2026-06 --profile v2_multilens",
            "py scripts/kospi_june_4ai_prophecy_overlay_v1.py",
            "py scripts/render_kospi_june_4ai_prophecy_report_v1.py",
            "py scripts/run_kospi_june2026_weight_candidate_compare_v1.py --year-month 2026-06",
            "py scripts/backfill_macro_risk_forward_log_from_ohlcv_v1.py --date-from 2026-01-01 --date-to 2026-04-30",
            "py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument both --date-from 2026-01-01 --date-to 2026-04-30",
            "powershell -File scripts/Run-BtcMultilensResearchCrossCheck_v1.ps1",
            "pwsh -File scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase Evening -YearMonth 2026-06",
            "py scripts/build_kospi_june2026_logos_anchor_crosswalk_v1.py",
            "py scripts/materialize_logos_gold_q09_election_router_ann_v1.py",
            "py scripts/build_logos_gold_query_eval_report_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--document-output", type=Path, default=DEFAULT_DOC)
    args = ap.parse_args(argv)

    doc = _read_json(args.input_json)
    if not doc.get("rows"):
        print(f"Missing rows: {args.input_json}", file=sys.stderr)
        return 2

    calendar = _read_json(args.calendar_json) if args.calendar_json.is_file() else None
    md = render_markdown(doc, calendar=calendar)
    for out_path, art_path in (
        (args.output, DEFAULT_ART),
        (args.document_output, DEFAULT_ART_DOC),
    ):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md + "\n", encoding="utf-8")
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_text(md + "\n", encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} + {args.document_output.resolve()} "
        f"lines={len(md.splitlines())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
