#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI 4AI-core overlay on v2_multilens calendar [HYPO][research_only].

Maps 8-channel blend rows to MKM 4AI core (태양/소양/태음/소음) agent votes,
then Absolute Balance Coordinator resolves conflict → daily direction narrative.

NOT a separate 4-agent LLM runtime. NOT Track A / live trading.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CAL = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"

FOUR_AI = ("taeyang", "soyang", "taeeum", "soeum")
FOUR_AI_KO = {
    "taeyang": "태양",
    "soyang": "소양",
    "taeeum": "태음",
    "soeum": "소음",
}

# Channel → 4AI agent ownership (pedagogical map [HYPO])
CHANNEL_AGENT: dict[str, str] = {
    "momentum_overlay": "taeyang",
    "field_regime": "taeyang",
    "session_myeongni": "soyang",
    "myeongni_independent": "soyang",
    "macro": "taeeum",
    "ensemble_kospi_causal": "taeeum",
    "sasang": "soeum",
    "logos_non_gating": "soeum",
}

DIR_SCORE = {"bull": 1.0, "bear": -1.0, "neutral": 0.0, "sideways": 0.0}

AUTONOMOUS_RESOLUTION_MODES = frozenset(
    {
        "balance_bull",
        "balance_bear",
        "balance_observe",
        "four_ai_weighted_agree",
        "four_ai_channel_soft",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dir_ko(direction: str) -> str:
    return {
        "bull": "상승",
        "bear": "하락",
        "neutral": "횡보·관측",
        "sideways": "횡보·관측",
    }.get(direction, direction)


def _agent_vote_from_channels(channels: list[dict[str, Any]], agent_id: str) -> dict[str, Any]:
    hits = [c for c in channels if CHANNEL_AGENT.get(str(c.get("channel"))) == agent_id]
    if not hits:
        return {"agent_id": agent_id, "direction": "neutral", "score": 0.0, "channels": []}
    num = 0.0
    den = 0.0
    detail: list[dict[str, Any]] = []
    for c in hits:
        w = float(c.get("weight") or 0.0)
        d = str(c.get("direction") or "neutral")
        num += w * DIR_SCORE.get(d, 0.0)
        den += w
        detail.append({"channel": c.get("channel"), "direction": d, "weight": w})
    score = num / den if den else 0.0
    if score > 0.12:
        direction = "bull"
    elif score < -0.12:
        direction = "bear"
    else:
        direction = "neutral"
    return {
        "agent_id": agent_id,
        "label_ko": FOUR_AI_KO[agent_id],
        "direction": direction,
        "direction_ko": _dir_ko(direction),
        "score": round(score, 4),
        "channels": detail,
    }


def _channel_consensus(
    channels: list[dict[str, Any]],
    *,
    blend_policy: dict[str, Any],
) -> dict[str, Any]:
    from scripts.kospi_june2026_multilens_blend_v1 import _resolve_winner

    votes = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
    for ch in channels:
        direction = str(ch.get("direction") or "neutral")
        if direction not in votes:
            direction = "neutral"
        votes[direction] += float(ch.get("weight") or 0.0)
    total_w = sum(votes.values()) or 1.0
    winner, resolution_mode = _resolve_winner(votes, total_w=total_w, policy=blend_policy)
    return {
        "direction": winner,
        "direction_ko": _dir_ko(winner),
        "resolution_mode": resolution_mode,
        "vote_totals": {k: round(v, 4) for k, v in votes.items()},
        "total_weight": round(total_w, 4),
    }


def _coordinator(
    agents: list[dict[str, Any]],
    *,
    channels: list[dict[str, Any]],
    blend_policy: dict[str, Any],
    conflict_threshold: float = 0.75,
    mean_direction_threshold: float = 0.12,
) -> dict[str, Any]:
    """Absolute Balance: agent synthesis when unified; else anchor to 8-channel v2 consensus."""
    scores = [float(a.get("score") or 0.0) for a in agents]
    mean = sum(scores) / len(scores) if scores else 0.0
    var = sum((s - mean) ** 2 for s in scores) / len(scores) if scores else 0.0
    conflict = math.sqrt(var)
    bulls = sum(1 for a in agents if a.get("direction") == "bull")
    bears = sum(1 for a in agents if a.get("direction") == "bear")
    neutrals = sum(1 for a in agents if a.get("direction") == "neutral")

    channel = _channel_consensus(channels, blend_policy=blend_policy)
    channel_dir = str(channel["direction"])

    agent_conflict = bool(bulls and bears) or conflict >= conflict_threshold
    if mean > mean_direction_threshold:
        agent_dir = "bull"
    elif mean < -mean_direction_threshold:
        agent_dir = "bear"
    else:
        agent_dir = "neutral"

    if agent_conflict:
        if agent_dir != "neutral" and agent_dir == channel_dir:
            final = agent_dir
            mode = "four_ai_weighted_agree"
            anchor_reason = "bull_bear_split" if (bulls and bears) else "high_dispersion"
        else:
            final = channel_dir
            mode = "four_ai_channel_anchor"
            anchor_reason = "bull_bear_split" if (bulls and bears) else "high_dispersion"
    elif agent_dir != "neutral":
        final = agent_dir
        mode = f"balance_{agent_dir}"
        anchor_reason = None
    else:
        final = channel_dir if channel_dir != "neutral" else "neutral"
        mode = "balance_observe" if final == "neutral" else "four_ai_channel_soft"
        anchor_reason = None

    aligned_with_channel = final == channel_dir

    return {
        "mode": "Absolute_Balance_Coordinator_Mode",
        "conflict_score": round(conflict, 4),
        "conflict_threshold": conflict_threshold,
        "agent_mean_score": round(mean, 4),
        "agent_vote_split": {"bull": bulls, "bear": bears, "neutral": neutrals},
        "channel_consensus": channel,
        "coordinator_direction": final,
        "coordinator_direction_ko": _dir_ko(final),
        "resolution_mode": mode,
        "anchor_reason": anchor_reason,
        "aligned_with_v2_channel": aligned_with_channel,
    }


def _load_blend_policy(evolution_path: Path | None) -> dict[str, Any]:
    doc = _read_json(evolution_path) if evolution_path and evolution_path.is_file() else {}
    policy = doc.get("blend_policy_v2")
    return policy if isinstance(policy, dict) else {}


def _load_coordinator_policy(evolution_path: Path | None) -> dict[str, Any]:
    doc = _read_json(evolution_path) if evolution_path and evolution_path.is_file() else {}
    pol = doc.get("four_ai_coordinator_policy")
    if isinstance(pol, dict):
        return pol
    return {
        "conflict_threshold": 0.75,
        "mean_direction_threshold": 0.12,
    }


def compute_four_ai_coordinator_kpi(
    rows: list[dict[str, Any]],
    *,
    targets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """KPI for 4AI autonomous consensus vs channel anchor (overlay health)."""
    n = len(rows)
    if n == 0:
        return {"n_trading_days": 0, "status": "NODATA"}

    anchor_days = 0
    weighted_agree_days = 0
    autonomous_days = 0
    v2_aligned = 0
    by_mode: dict[str, int] = {}

    for row in rows:
        ab = row.get("absolute_balance") if isinstance(row.get("absolute_balance"), dict) else {}
        mode = str(ab.get("resolution_mode") or row.get("weight_field") or "")
        by_mode[mode] = by_mode.get(mode, 0) + 1
        if mode == "four_ai_channel_anchor":
            anchor_days += 1
        if mode == "four_ai_weighted_agree":
            weighted_agree_days += 1
        if mode in AUTONOMOUS_RESOLUTION_MODES:
            autonomous_days += 1
        if row.get("v2_aligned") is True:
            v2_aligned += 1

    autonomous_rate = round(autonomous_days / n, 4)
    anchor_rate = round(anchor_days / n, 4)
    v2_alignment_rate = round(v2_aligned / n, 4)

    tgt = targets if isinstance(targets, dict) else {}
    min_auto = float(tgt.get("min_autonomous_consensus_rate", 0.20))
    min_v2 = float(tgt.get("min_v2_alignment_rate", 1.0))
    max_anchor = float(tgt.get("max_channel_anchor_rate", 0.80))

    status = "on_track"
    notes: list[str] = []
    if v2_alignment_rate < min_v2:
        status = "blocked"
        notes.append("v2_alignment_below_gate")
    elif autonomous_rate < min_auto:
        status = "watch"
        notes.append("autonomous_consensus_below_target")
    if anchor_rate > max_anchor:
        if status == "on_track":
            status = "watch"
        notes.append("channel_anchor_above_target")

    return {
        "n_trading_days": n,
        "autonomous_consensus_days": autonomous_days,
        "autonomous_consensus_rate": autonomous_rate,
        "weighted_agree_days": weighted_agree_days,
        "channel_anchor_days": anchor_days,
        "channel_anchor_rate": anchor_rate,
        "v2_alignment_days": v2_aligned,
        "v2_alignment_rate": v2_alignment_rate,
        "resolution_mode_counts": by_mode,
        "targets": {
            "min_autonomous_consensus_rate": min_auto,
            "min_v2_alignment_rate": min_v2,
            "max_channel_anchor_rate": max_anchor,
        },
        "status": status,
        "notes": notes,
    }


def build_4ai_report(
    calendar: dict[str, Any],
    *,
    eval_doc: dict[str, Any] | None = None,
    blend_policy: dict[str, Any] | None = None,
    coordinator_policy: dict[str, Any] | None = None,
    conflict_threshold: float = 0.75,
    mean_direction_threshold: float = 0.12,
) -> dict[str, Any]:
    policy = blend_policy if isinstance(blend_policy, dict) else {}
    coord_pol = coordinator_policy if isinstance(coordinator_policy, dict) else _load_coordinator_policy(
        DEFAULT_EVOLUTION
    )
    lock_v2_calendar = bool(coord_pol.get("lock_coordinator_to_v2_calendar"))
    rows_out: list[dict[str, Any]] = []
    for row in calendar.get("rows") or []:
        blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
        channels = blend.get("channels") if isinstance(blend.get("channels"), list) else []
        agents = [_agent_vote_from_channels(channels, aid) for aid in FOUR_AI]
        coord = _coordinator(
            agents,
            channels=channels,
            blend_policy=policy,
            conflict_threshold=conflict_threshold,
            mean_direction_threshold=mean_direction_threshold,
        )
        v2_dir = str(row.get("predicted_direction") or "neutral")
        four_ai_dir = coord["coordinator_direction"]
        resolution_mode = coord["resolution_mode"]
        if lock_v2_calendar and four_ai_dir != v2_dir:
            four_ai_dir = v2_dir
            resolution_mode = "four_ai_v2_calendar_lock"
        band = row.get("kospi_index_prophecy") if isinstance(row.get("kospi_index_prophecy"), dict) else {}
        abs_balance = dict(coord)
        if lock_v2_calendar:
            abs_balance["v2_calendar_lock_applied"] = four_ai_dir != coord["coordinator_direction"]
        rows_out.append(
            {
                "session_date": row.get("session_date"),
                "weekday_ko": row.get("weekday_ko"),
                "v2_multilens_direction": v2_dir,
                "v2_multilens_direction_ko": _dir_ko(v2_dir),
                "four_ai_agents": agents,
                "absolute_balance": abs_balance,
                "four_ai_direction": four_ai_dir,
                "four_ai_direction_ko": _dir_ko(four_ai_dir),
                "weight_field": resolution_mode,
                "v2_aligned": four_ai_dir == v2_dir,
                "reference_close_mid": band.get("predicted_close_mid"),
                "pillars_session": row.get("pillars_session"),
            }
        )

    payload = json.dumps(rows_out, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    eval_summary = None
    if eval_doc:
        eval_summary = {
            "as_of_kst": eval_doc.get("as_of_kst"),
            "n_scored": eval_doc.get("n_scored"),
            "metrics": eval_doc.get("metrics"),
            "missing_ohlcv_trading_days": eval_doc.get("missing_ohlcv_trading_days"),
        }

    kpi_targets = (
        coord_pol.get("kpi_targets") if isinstance(coord_pol.get("kpi_targets"), dict) else None
    )
    coordinator_kpi = compute_four_ai_coordinator_kpi(rows_out, targets=kpi_targets)

    n_anchor = coordinator_kpi["channel_anchor_days"]
    n_weighted = coordinator_kpi["weighted_agree_days"]
    n_autonomous = coordinator_kpi["autonomous_consensus_days"]
    n_observe = sum(1 for r in rows_out if r["four_ai_direction"] == "neutral")
    n_aligned = coordinator_kpi["v2_alignment_days"]
    n_bear = sum(1 for r in rows_out if r["four_ai_direction"] == "bear")
    n_bull = sum(1 for r in rows_out if r["four_ai_direction"] == "bull")

    return {
        "schema": "kospi_june_4ai_prophecy_report_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "year_month": calendar.get("year_month") or "2026-06",
        "multilens_profile": calendar.get("multilens_profile") or "v2_multilens",
        "four_ai_contract": "4AI_core + Absolute_Balance_Coordinator_Mode (overlay; not 5th lens)",
        "naming_firewall_ko": "본 4AI 오버레이는 temperament sim·12AI 라우터·실매매 4에이전트와 동일 런타임 아님.",
        "content_hash": digest,
        "status": "WATCH",
        "executive_summary_ko": {
            "stance": (
                "횡보·관측 우세"
                if n_observe >= len(rows_out) // 2
                else ("하락 우세" if n_bear > n_bull else "상승 우세" if n_bull > n_bear else "방향 분산")
            ),
            "channel_anchor_days": n_anchor,
            "weighted_agree_days": n_weighted,
            "autonomous_consensus_days": n_autonomous,
            "autonomous_consensus_rate": coordinator_kpi.get("autonomous_consensus_rate"),
            "observe_days": n_observe,
            "bear_days": n_bear,
            "bull_days": n_bull,
            "v2_alignment_days": n_aligned,
            "v2_alignment_rate": coordinator_kpi.get("v2_alignment_rate"),
            "coordinator_kpi_status": coordinator_kpi.get("status"),
            "n_trading_days": len(rows_out),
            "note": "충돌 시 가중평균·채널 일치면 four_ai_weighted_agree; 불일치만 channel_anchor.",
        },
        "coordinator_kpi": coordinator_kpi,
        "blend_formula_note": {
            "v1_legacy_doc": "0.55*myeongni + 0.25*momentum + 0.20*logos (구 보고서용)",
            "v2_active": "8-channel v2_multilens (see calendar blend.weights)",
            "four_ai_overlay": "channel→agent map + Absolute Balance (unified→agent mean; conflict→channel anchor)",
        },
        "coordinator_policy": {
            "conflict_threshold": conflict_threshold,
            "mean_direction_threshold": mean_direction_threshold,
            "blend_policy_v2": policy,
        },
        "eval_summary": eval_summary,
        "calendar_source": calendar.get("year_month"),
        "rows": rows_out,
        "replay": {
            "calendar": "py scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py --year-month 2026-06 --profile v2_multilens",
            "overlay": "py scripts/kospi_june_4ai_prophecy_overlay_v1.py",
            "evening_loop": "pwsh -File scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase Evening -YearMonth 2026-06",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--evolution-json", type=Path, default=DEFAULT_EVOLUTION)
    ap.add_argument("--conflict-threshold", type=float, default=0.75)
    ap.add_argument("--mean-direction-threshold", type=float, default=0.12)
    args = ap.parse_args(argv)

    cal = _read_json(args.calendar_json)
    if not cal.get("rows"):
        print(f"Missing calendar rows: {args.calendar_json}", file=sys.stderr)
        return 2

    eval_doc = _read_json(args.eval_json) if args.eval_json.is_file() else None
    blend_policy = _load_blend_policy(args.evolution_json)
    coord_policy = _load_coordinator_policy(args.evolution_json)
    conflict_threshold = float(
        coord_policy.get("conflict_threshold", args.conflict_threshold)
    )
    mean_direction_threshold = float(
        coord_policy.get("mean_direction_threshold", args.mean_direction_threshold)
    )
    doc = build_4ai_report(
        cal,
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=coord_policy,
        conflict_threshold=conflict_threshold,
        mean_direction_threshold=mean_direction_threshold,
    )

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")

    es = doc["executive_summary_ko"]
    print(
        f"WROTE: {args.output.resolve()} rows={len(doc['rows'])} "
        f"bear={es.get('bear_days')} neutral={es.get('observe_days')} "
        f"v2_align={es.get('v2_alignment_days')}/{es.get('n_trading_days')} "
        f"hash={doc['content_hash']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
