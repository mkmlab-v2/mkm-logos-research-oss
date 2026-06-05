#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI shadow weight panel — parallel compare vs applied active [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar  # noqa: E402
from scripts.run_kospi_june2026_weight_candidate_compare_v1 import (  # noqa: E402
    BACKTEST_DEFAULT,
    EVOLUTION_RULES,
    HORIZON_V2_DEFAULT,
    WALKFORWARD_DEFAULT,
    compare_candidates,
    _row_direction_map,
)

DEFAULT_PANEL = ROOT / "reports/kospi_june2026_shadow_candidate_panel_latest.json"
DEFAULT_LOG = ROOT / "reports/kospi_june2026_shadow_panel_log.jsonl"

_CANDIDATE_SLUG: dict[str, str] = {
    "v2_lens3_heavy_4ai_current": "lens3_4ai",
    "v2_default_4ai_current": "default_4ai",
    "v2_field_momentum_4ai_legacy_hold": "field_momentum",
    "v2_lens3_heavy": "lens3_heavy",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_kst() -> str:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_slug(candidate_id: str) -> str:
    if candidate_id in _CANDIDATE_SLUG:
        return _CANDIDATE_SLUG[candidate_id]
    slug = re.sub(r"[^a-z0-9]+", "_", candidate_id.lower()).strip("_")
    return slug or "unknown"


def _compare_out_path(candidate_id: str) -> Path:
    return ROOT / f"reports/kospi_june2026_shadow_compare_{_candidate_slug(candidate_id)}_latest.json"


def _resolve_shadow_candidate_ids(rules: dict[str, Any]) -> list[str]:
    panel_policy = rules.get("shadow_panel_policy")
    if isinstance(panel_policy, dict) and panel_policy.get("enabled") is False:
        return []
    if isinstance(panel_policy, dict):
        raw_ids = panel_policy.get("candidate_ids")
        if isinstance(raw_ids, list) and raw_ids:
            applied = str(
                rules.get("last_candidate_apply_id")
                or (rules.get("weight_candidate_policy") or {}).get("active_candidate_id")
                or ""
            )
            return [str(x) for x in raw_ids if str(x) != applied]

    applied = str(rules.get("last_candidate_apply_id") or rules.get("weight_candidate_policy", {}).get("active_candidate_id") or "")
    candidates = rules.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict):
        return []
    out: list[str] = []
    for cid, entry in candidates.items():
        if cid == applied:
            continue
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status")) == "research_shadow":
            out.append(cid)
    return sorted(out)


def _metric_soft(doc: dict[str, Any] | None) -> float | None:
    if not isinstance(doc, dict):
        return None
    metrics = doc.get("metrics")
    if not isinstance(metrics, dict):
        return None
    val = metrics.get("soft_hit_rate")
    return float(val) if val is not None else None


def _active_forward_from_eval(eval_doc: dict[str, Any] | None, *, year_month: str) -> dict[str, Any] | None:
    if not isinstance(eval_doc, dict) or eval_doc.get("schema") != "kospi_june2026_daily_prophecy_eval_v1":
        return None
    ym = str(eval_doc.get("year_month") or "")
    if ym and ym != year_month:
        return None
    return {
        "n_scored": eval_doc.get("n_scored"),
        "metrics": eval_doc.get("metrics"),
        "missing_ohlcv_trading_days": eval_doc.get("missing_ohlcv_trading_days"),
        "as_of_kst": eval_doc.get("as_of_kst"),
        "source": "kospi_june2026_daily_prophecy_eval_latest",
    }


def _summarize_shadow(
    compare_doc: dict[str, Any],
    *,
    compare_path: Path,
    active_fwd_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fwd = compare_doc.get("june_forward_eval") if isinstance(compare_doc.get("june_forward_eval"), dict) else {}
    active_fwd = active_fwd_override if active_fwd_override else (fwd.get("active") if isinstance(fwd.get("active"), dict) else {})
    cand_fwd = fwd.get("candidate") if isinstance(fwd.get("candidate"), dict) else {}
    active_soft = _metric_soft(active_fwd)
    cand_soft = _metric_soft(cand_fwd)
    soft_delta: float | None = None
    if active_soft is not None and cand_soft is not None:
        soft_delta = round(cand_soft - active_soft, 6)

    promo = compare_doc.get("promotion_recommendation") if isinstance(compare_doc.get("promotion_recommendation"), dict) else {}
    wf = compare_doc.get("walkforward_prefilter")
    bt = compare_doc.get("backtest_delta") if isinstance(compare_doc.get("backtest_delta"), dict) else {}

    scored_diffs: list[dict[str, Any]] = []
    n_scored = int(active_fwd.get("n_scored") or 0)
    if n_scored > 0:
        diff_dates = {str(d.get("session_date")) for d in (compare_doc.get("direction_diffs") or []) if d.get("session_date")}
        scored_diffs = [
            d for d in (compare_doc.get("direction_diffs") or []) if str(d.get("session_date")) in diff_dates
        ][:n_scored]

    return {
        "candidate_id": compare_doc.get("candidate_id"),
        "candidate_status": compare_doc.get("candidate_status"),
        "candidate_note_ko": compare_doc.get("candidate_note_ko"),
        "compare_artifact": str(compare_path.relative_to(ROOT)).replace("\\", "/"),
        "n_calendar_direction_diffs": compare_doc.get("n_direction_diffs"),
        "n_trading_days": compare_doc.get("n_trading_days"),
        "direction_counts": compare_doc.get("direction_counts"),
        "forward_eval": {
            "active": active_fwd,
            "candidate": cand_fwd,
            "soft_delta_candidate_minus_active": soft_delta,
        },
        "forward_direction_diffs_on_scored_window": scored_diffs,
        "backtest_delta": bt,
        "walkforward_prefilter": wf,
        "promotion_recommendation": {
            "ready_for_apply_review": promo.get("ready_for_apply_review"),
            "blockers": promo.get("blockers"),
        },
    }


def _build_scored_day_arm_diff(
    *,
    applied_id: str,
    shadow_ids: list[str],
    year_month: str,
    eval_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: WPS433

    empty: dict[str, Any] = {
        "schema": "kospi_june2026_scored_day_arm_diff_v1",
        "n_scored_days": 0,
        "days": [],
        "summary": {
            "n_days_any_shadow_direction_diff": 0,
            "n_days_shadow_soft_beat_active": 0,
        },
    }
    if not isinstance(eval_doc, dict) or eval_doc.get("schema") != "kospi_june2026_daily_prophecy_eval_v1":
        return empty
    scored_rows = [r for r in (eval_doc.get("rows") or []) if r.get("session_date")]
    if not scored_rows:
        return empty

    active_cal = build_calendar(year_month=year_month, skip_panel=True, profile="v2_multilens")
    active_map = _row_direction_map(active_cal)
    shadow_maps: dict[str, dict[str, str]] = {}
    for cid in shadow_ids:
        shadow_maps[cid] = _row_direction_map(
            build_calendar(
                year_month=year_month,
                skip_panel=True,
                profile="v2_multilens",
                weights_candidate_id=cid,
            )
        )

    days: list[dict[str, Any]] = []
    n_any_diff = 0
    n_shadow_beat = 0
    for row in scored_rows:
        dk = str(row.get("session_date"))
        actual = str(row.get("actual_direction") or "neutral")
        active_dir = active_map.get(dk, "neutral")
        active_outcome = str(row.get("outcome") or _outcome(active_dir, actual))
        arms: list[dict[str, Any]] = [
            {
                "arm_id": applied_id,
                "role": "applied_active",
                "predicted_direction": active_dir,
                "outcome": active_outcome,
            }
        ]
        any_diff = False
        for cid in shadow_ids:
            shadow_dir = shadow_maps.get(cid, {}).get(dk, "neutral")
            shadow_outcome = _outcome(shadow_dir, actual)
            diff = shadow_dir != active_dir
            any_diff = any_diff or diff
            arms.append(
                {
                    "arm_id": cid,
                    "role": "research_shadow",
                    "predicted_direction": shadow_dir,
                    "outcome": shadow_outcome,
                    "direction_diff_vs_active": diff,
                }
            )
        if any_diff:
            n_any_diff += 1
        active_soft = 1.0 if active_outcome == "HIT" else (0.5 if active_outcome == "NEUTRAL_DRAW" else 0.0)
        best_shadow_soft = max(
            (
                1.0 if a["outcome"] == "HIT" else (0.5 if a["outcome"] == "NEUTRAL_DRAW" else 0.0)
                for a in arms
                if a.get("role") == "research_shadow"
            ),
            default=0.0,
        )
        if best_shadow_soft > active_soft:
            n_shadow_beat += 1
        days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "daily_return_pct": row.get("daily_return_pct"),
                "arms": arms,
                "any_shadow_direction_diff": any_diff,
            }
        )

    return {
        "schema": "kospi_june2026_scored_day_arm_diff_v1",
        "n_scored_days": len(days),
        "days": days,
        "summary": {
            "n_days_any_shadow_direction_diff": n_any_diff,
            "n_days_shadow_soft_beat_active": n_shadow_beat,
        },
    }


def build_shadow_panel(
    *,
    rules: dict[str, Any],
    year_month: str = "2026-06",
    shadow_ids: list[str] | None = None,
    backtest_doc: dict[str, Any] | None = None,
    horizon_v2_doc: dict[str, Any] | None = None,
    walkforward_doc: dict[str, Any] | None = None,
    eval_doc: dict[str, Any] | None = None,
    write_compare_artifacts: bool = True,
) -> dict[str, Any]:
    applied_id = str(
        rules.get("last_candidate_apply_id")
        or (rules.get("weight_candidate_policy") or {}).get("active_candidate_id")
        or "v2_lens3_heavy"
    )
    ids = shadow_ids if shadow_ids is not None else _resolve_shadow_candidate_ids(rules)
    candidates = rules.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict):
        candidates = {}

    unknown = [cid for cid in ids if cid not in candidates]
    if unknown:
        raise ValueError(f"Unknown shadow candidate ids: {unknown}")

    active_fwd = _active_forward_from_eval(eval_doc, year_month=year_month) or {}

    shadows: list[dict[str, Any]] = []
    for cid in ids:
        compare_doc = compare_candidates(
            rules=rules,
            year_month=year_month,
            candidate_id=cid,
            backtest_doc=backtest_doc,
            horizon_v2_doc=horizon_v2_doc,
            walkforward_doc=walkforward_doc,
            eval_doc=eval_doc,
        )
        out_path = _compare_out_path(cid)
        if write_compare_artifacts:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(compare_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shadows.append(
            _summarize_shadow(
                compare_doc,
                compare_path=out_path,
                active_fwd_override=active_fwd or None,
            )
        )

    if not active_fwd:
        active_compare = compare_candidates(
            rules=rules,
            year_month=year_month,
            candidate_id=applied_id,
            backtest_doc=backtest_doc,
            horizon_v2_doc=horizon_v2_doc,
            walkforward_doc=walkforward_doc,
            eval_doc=eval_doc,
        )
        active_fwd = (active_compare.get("june_forward_eval") or {}).get("active") or {}

    leaderboard: list[dict[str, Any]] = [
        {
            "candidate_id": applied_id,
            "role": "applied_active",
            "n_scored": active_fwd.get("n_scored"),
            "soft_hit_rate": _metric_soft(active_fwd),
        }
    ]
    for row in shadows:
        cand_fwd = (row.get("forward_eval") or {}).get("candidate") or {}
        leaderboard.append(
            {
                "candidate_id": row.get("candidate_id"),
                "role": "research_shadow",
                "n_scored": cand_fwd.get("n_scored"),
                "soft_hit_rate": _metric_soft(cand_fwd),
                "soft_delta_vs_active": (row.get("forward_eval") or {}).get("soft_delta_candidate_minus_active"),
            }
        )
    leaderboard.sort(
        key=lambda x: (x.get("soft_hit_rate") is None, -(float(x.get("soft_hit_rate") or -1))),
    )

    panel_policy = rules.get("shadow_panel_policy") if isinstance(rules.get("shadow_panel_policy"), dict) else {}

    scored_day_arm_diff = _build_scored_day_arm_diff(
        applied_id=applied_id,
        shadow_ids=ids,
        year_month=year_month,
        eval_doc=eval_doc,
    )

    return {
        "schema": "kospi_june2026_shadow_candidate_panel_v1",
        "generated_at_utc": _utc_now(),
        "session_date_kst": _today_kst(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": year_month,
        "applied_active_id": applied_id,
        "applied_active_at_utc": rules.get("last_candidate_apply_at_utc"),
        "shadow_candidate_ids": ids,
        "active_forward": active_fwd,
        "shadows": shadows,
        "leaderboard_forward_soft": leaderboard,
        "scored_day_arm_diff": scored_day_arm_diff,
        "rollup_artifact": "reports/kospi_june2026_shadow_panel_rollup_latest.json",
        "panel_artifact": str(DEFAULT_PANEL.relative_to(ROOT)).replace("\\", "/"),
        "panel_log": str(DEFAULT_LOG.relative_to(ROOT)).replace("\\", "/"),
        "note_ko": str(
            panel_policy.get("note_ko")
            or "apply arm 대비 shadow 3후보 병렬 diff·포워드 누적. auto apply·Track A·실매매 합선 금지."
        ),
    }


def _append_panel_log(panel: dict[str, Any], log_path: Path) -> None:
    session_kst = panel.get("session_date_kst")
    if log_path.is_file() and session_kst:
        try:
            last_line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
            last_entry = json.loads(last_line)
            if last_entry.get("session_date_kst") == session_kst:
                return
        except (IndexError, json.JSONDecodeError, OSError):
            pass
    entry = {
        "schema": "kospi_june2026_shadow_panel_log_v1",
        "logged_at_utc": panel.get("generated_at_utc"),
        "session_date_kst": panel.get("session_date_kst"),
        "applied_active_id": panel.get("applied_active_id"),
        "active_n_scored": (panel.get("active_forward") or {}).get("n_scored"),
        "active_soft_hit_rate": _metric_soft(panel.get("active_forward") or {}),
        "shadows": [
            {
                "candidate_id": s.get("candidate_id"),
                "n_calendar_direction_diffs": s.get("n_calendar_direction_diffs"),
                "soft_hit_rate": _metric_soft((s.get("forward_eval") or {}).get("candidate") or {}),
                "soft_delta_vs_active": (s.get("forward_eval") or {}).get("soft_delta_candidate_minus_active"),
            }
            for s in (panel.get("shadows") or [])
        ],
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", type=str, default="2026-06")
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION_RULES)
    ap.add_argument("--backtest-json", type=Path, default=BACKTEST_DEFAULT)
    ap.add_argument("--horizon-v2-json", type=Path, default=HORIZON_V2_DEFAULT)
    ap.add_argument("--walkforward-json", type=Path, default=WALKFORWARD_DEFAULT)
    ap.add_argument("--eval-json", type=Path, default=ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json")
    ap.add_argument("--output", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--no-log-append", action="store_true")
    ap.add_argument("--candidate-id", action="append", dest="candidate_ids", default=None)
    args = ap.parse_args(argv)

    rules = _read_json(args.rules_json)
    if not rules:
        raise SystemExit(f"Missing evolution rules: {args.rules_json}")

    backtest_doc = _read_json(args.backtest_json) if args.backtest_json.is_file() else None
    horizon_v2_doc = _read_json(args.horizon_v2_json) if args.horizon_v2_json.is_file() else None
    walkforward_doc = _read_json(args.walkforward_json) if args.walkforward_json.is_file() else None
    eval_doc = _read_json(args.eval_json) if args.eval_json.is_file() else None

    panel = build_shadow_panel(
        rules=rules,
        year_month=args.year_month,
        shadow_ids=args.candidate_ids,
        backtest_doc=backtest_doc,
        horizon_v2_doc=horizon_v2_doc,
        walkforward_doc=walkforward_doc,
        eval_doc=eval_doc,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.no_log_append:
        _append_panel_log(panel, args.log_jsonl)

    n_shadows = len(panel.get("shadows") or [])
    n_scored = (panel.get("active_forward") or {}).get("n_scored")
    print(
        f"WROTE: {args.output.resolve()} shadows={n_shadows} "
        f"applied={panel.get('applied_active_id')} active_n_scored={n_scored}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
