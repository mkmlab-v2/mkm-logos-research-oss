#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Briefing-primary vs scoring-shadow lane HR compare [HYPO][research_only]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.kospi_oos_significance_lib_v1 import metrics_from_eval_rows, significance_block

BRIEFING_LANE_ID = "briefing_primary_parallel_advisory_graphrag"
SCORING_LANE_ID = "scoring_shadow_weighted_blend_v2"

FOUR_LENS_CHANNELS = ("sasang", "myeongni_independent", "logos_non_gating")
TAIL_SIGNAL_CHANNELS = ("logos_non_gating", "field_regime")


def _outcome(pred: str, actual: str) -> str:
    if actual == "neutral" or pred == "neutral":
        return "NEUTRAL_DRAW"
    if pred == actual:
        return "HIT"
    return "FAIL"


def _majority_direction(signs: list[str]) -> str:
    bulls = sum(1 for s in signs if s == "bull")
    bears = sum(1 for s in signs if s == "bear")
    if bulls > bears:
        return "bull"
    if bears > bulls:
        return "bear"
    return "neutral"


def _channel_directions(calendar_row: dict[str, Any]) -> dict[str, str]:
    blend = calendar_row.get("blend") if isinstance(calendar_row.get("blend"), dict) else {}
    channels = blend.get("channels") if isinstance(blend.get("channels"), list) else []
    out: dict[str, str] = {}
    for ch in channels:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("channel") or "").strip()
        if not name:
            continue
        out[name] = str(ch.get("direction") or "neutral").lower()
    return out


def load_science_core_directions(jsonl_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not jsonl_path.is_file():
        return out
    for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        dk = str(row.get("session_date") or "")[:10]
        if len(dk) != 10:
            continue
        out[dk] = str(row.get("direction") or "neutral").lower()
    return out


def briefing_direction_four_lens_parallel(
    calendar_row: dict[str, Any],
    *,
    science_by_date: dict[str, str],
) -> str:
    """Equal vote: sasang · myeongni · logos · science@finance (no session pillar, no macro)."""
    dk = str(calendar_row.get("session_date") or "")
    ch = _channel_directions(calendar_row)
    signs: list[str] = []
    for key in FOUR_LENS_CHANNELS:
        if key in ch:
            signs.append(ch[key])
    sci = science_by_date.get(dk)
    if sci:
        signs.append(sci)
    if not signs:
        return "neutral"
    return _majority_direction(signs)


def briefing_direction_tail_group(
    calendar_row: dict[str, Any],
    *,
    science_by_date: dict[str, str],
) -> str:
    """Equal vote: logos + field_regime + science (tail-risk advisory group)."""
    dk = str(calendar_row.get("session_date") or "")
    ch = _channel_directions(calendar_row)
    signs: list[str] = []
    for key in TAIL_SIGNAL_CHANNELS:
        if key in ch:
            signs.append(ch[key])
    sci = science_by_date.get(dk)
    if sci:
        signs.append(sci)
    if not signs:
        return "neutral"
    return _majority_direction(signs)


def build_lane_compare_rows(
    eval_rows: list[dict[str, Any]],
    calendar_by_date: dict[str, dict[str, Any]],
    *,
    science_by_date: dict[str, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for er in eval_rows:
        if not isinstance(er, dict):
            continue
        dk = str(er.get("session_date") or "")
        if not dk:
            continue
        actual = str(er.get("actual_direction") or "neutral").lower()
        scoring_pred = str(er.get("predicted_direction") or "neutral").lower()
        prow = calendar_by_date.get(dk) or {}
        ch = _channel_directions(prow)
        four_lens = briefing_direction_four_lens_parallel(prow, science_by_date=science_by_date)
        tail_group = briefing_direction_tail_group(prow, science_by_date=science_by_date)
        out.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "scoring_shadow_predicted": scoring_pred,
                "scoring_shadow_outcome": _outcome(scoring_pred, actual),
                "briefing_four_lens_parallel": four_lens,
                "briefing_four_lens_outcome": _outcome(four_lens, actual),
                "briefing_tail_group": tail_group,
                "briefing_tail_outcome": _outcome(tail_group, actual),
                "channel_signs": {
                    "sasang": ch.get("sasang"),
                    "myeongni": ch.get("myeongni_independent"),
                    "logos": ch.get("logos_non_gating"),
                    "macro": ch.get("macro"),
                    "field": ch.get("field_regime"),
                    "science": science_by_date.get(dk),
                },
                "differs_scoring_vs_four_lens": four_lens != scoring_pred,
                "differs_scoring_vs_tail": tail_group != scoring_pred,
            }
        )
    return out


def lane_metrics_from_compare_rows(
    rows: list[dict[str, Any]], *, pred_field: str, outcome_field: str, label: str
) -> dict[str, Any]:
    eval_shaped: list[dict[str, Any]] = []
    for r in rows:
        outcome = r.get(outcome_field)
        if not outcome:
            continue
        eval_shaped.append(
            {
                "outcome": outcome,
                "predicted_direction": r.get(pred_field),
                "actual_direction": r.get("actual_direction"),
            }
        )
    m = metrics_from_eval_rows(eval_shaped)
    return {
        "label": label,
        "raw": m,
        "directional_significance": significance_block(
            label=f"{label}_directional",
            successes=float(m["hit"]),
            n=int(m["n_directional_bets"]),
        ),
        "soft_significance": significance_block(
            label=f"{label}_soft",
            successes=float(m["soft_successes"]),
            n=int(m["n_scored"]),
        ),
    }


def build_lane_compare_report(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    *,
    science_jsonl: Path,
    year_month: str = "2026-06",
) -> dict[str, Any]:
    eval_rows = eval_doc.get("rows") if isinstance(eval_doc.get("rows"), list) else []
    cal_rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    calendar_by_date = {
        str(r.get("session_date")): r for r in cal_rows if isinstance(r, dict) and r.get("session_date")
    }
    science_by_date = load_science_core_directions(science_jsonl)
    compare_rows = build_lane_compare_rows(eval_rows, calendar_by_date, science_by_date=science_by_date)

    scoring_metrics = lane_metrics_from_compare_rows(
        compare_rows,
        pred_field="scoring_shadow_predicted",
        outcome_field="scoring_shadow_outcome",
        label="scoring_shadow",
    )
    four_lens_metrics = lane_metrics_from_compare_rows(
        compare_rows,
        pred_field="briefing_four_lens_parallel",
        outcome_field="briefing_four_lens_outcome",
        label="briefing_four_lens_parallel",
    )
    tail_metrics = lane_metrics_from_compare_rows(
        compare_rows,
        pred_field="briefing_tail_group",
        outcome_field="briefing_tail_outcome",
        label="briefing_tail_group",
    )

    s_soft = scoring_metrics["raw"].get("soft_hit_rate")
    f_soft = four_lens_metrics["raw"].get("soft_hit_rate")
    t_soft = tail_metrics["raw"].get("soft_hit_rate")
    delta_four = round((f_soft or 0) - (s_soft or 0), 4) if s_soft is not None and f_soft is not None else None
    delta_tail = round((t_soft or 0) - (s_soft or 0), 4) if s_soft is not None and t_soft is not None else None

    n_diff_four = sum(1 for r in compare_rows if r.get("differs_scoring_vs_four_lens"))
    n_diff_tail = sum(1 for r in compare_rows if r.get("differs_scoring_vs_tail"))

    headline_ko = (
        f"scoring soft {s_soft} · briefing_4l soft {f_soft} (Δ{delta_four}) · tail_group soft {t_soft} (Δ{delta_tail}) "
        f"— direction_merge 금지 · 승격 없음"
    )

    return {
        "schema": "kospi_briefing_vs_scoring_lane_compare_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "direction_merge_forbidden": True,
        "year_month": year_month,
        "as_of_kst": eval_doc.get("as_of_kst"),
        "briefing_lane_id": BRIEFING_LANE_ID,
        "scoring_lane_id": SCORING_LANE_ID,
        "scoring_model_id": "v2_lens3_heavy",
        "briefing_rules": {
            "four_lens_parallel_majority": {
                "channels": list(FOUR_LENS_CHANNELS) + ["science@finance_per_date"],
                "note_ko": "인문3+Science 동일가중 다수결 — session_myeongni·macro 제외",
            },
            "tail_group_majority": {
                "channels": list(TAIL_SIGNAL_CHANNELS) + ["science@finance_per_date"],
                "note_ko": "logos+field+science 동일가중 — 급락일 bear 신호 그룹",
            },
        },
        "science_core_jsonl": str(science_jsonl).replace("\\", "/"),
        "lanes": {
            "scoring_shadow": scoring_metrics,
            "briefing_four_lens_parallel": four_lens_metrics,
            "briefing_tail_group": tail_metrics,
        },
        "delta_soft_vs_scoring": {
            "briefing_four_lens_parallel": delta_four,
            "briefing_tail_group": delta_tail,
        },
        "n_days_direction_differs_from_scoring": {
            "briefing_four_lens_parallel": n_diff_four,
            "briefing_tail_group": n_diff_tail,
        },
        "rows": compare_rows,
        "headline_ko": headline_ko,
        "verdict_ko": (
            "브리핑 프록시(4렌즈·tail)와 scoring_shadow HR 분리 보고. "
            "merge·Track A 승격 금지. tail_group이 scoring보다 나으면 조건부 shadow holdout PoC만."
        ),
        "do_not_confuse_ko": (
            "본 아티팩트는 parallel_advisory GraphRAG 브리핑 본선의 일별 방향 프록시이며, "
            "채점 본선(v2_lens3_heavy weighted blend)과 혼동·자동 merge 금지."
        ),
    }
