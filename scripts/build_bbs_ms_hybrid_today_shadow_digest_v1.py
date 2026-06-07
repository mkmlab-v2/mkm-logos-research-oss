#!/usr/bin/env python3
"""[HYPO] Today-line digest: frozen KPI headline vs BBS+MS shadow (no live routing)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_bbs_ms_hybrid_today_shadow_digest_v1_latest.json"
SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
FROZEN_EVAL = ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"
SHADOW = ROOT / "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json"
MS_DRIFT = ROOT / "reports/btrack_ms_anchor_vs_latest_hybrid_v1_latest.json"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _headline_from_hypothesis(hypo: dict[str, Any]) -> tuple[str | None, str | None]:
    pred = hypo.get("prediction") if isinstance(hypo.get("prediction"), dict) else {}
    direction = pred.get("direction") or hypo.get("direction")
    ed = pred.get("eval_date") or hypo.get("eval_date")
    return (str(ed)[:10] if ed else None, str(direction).lower() if direction else None)


def _latest_btc_eval_date(score: dict[str, Any]) -> str | None:
    rows = score.get("rows") or score.get("evaluations") or []
    dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() not in ("btc", ""):
            continue
        ed = str(row.get("eval_date") or row.get("date") or "")[:10]
        if ed:
            dates.append(ed)
    return max(dates) if dates else None


def _headline_dir(score: dict[str, Any], ed: str) -> str | None:
    for row in score.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("eval_date") or "")[:10] != ed:
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        d = row.get("predicted_direction") or row.get("direction")
        return str(d).lower() if d else None
    hypo = _load(HYPO)
    for row in hypo.get("forecasts") or hypo.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("eval_date") or row.get("date") or "")[:10] != ed:
            continue
        d = row.get("predicted_direction") or row.get("direction")
        return str(d).lower() if d else None
    return None


def _bbs_shadow_for_date(ed: str) -> dict[str, Any] | None:
    for row in _load(DAILY_DIFF).get("per_day") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("eval_date") or "")[:10] != ed:
            continue
        leg = str(row.get("legacy_v1") or "").lower()
        m16 = str(row.get("m016_v1") or "").lower()
        ms = str(row.get("legacy_ms") or "neutral").lower()
        resolved = leg if leg == "bull" and m16 == "bear" else m16
        if resolved in ("bull", "bear") and resolved == ms:
            hybrid = resolved
        elif ms in ("bull", "bear"):
            hybrid = ms
        else:
            hybrid = resolved
        return {
            "legacy_v1": leg,
            "m016_v1": m16,
            "bbs_resolved_v1": resolved,
            "ms": ms,
            "bbs_ms_hybrid": hybrid,
            "actual": row.get("actual"),
        }
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = _load(SCORE)
    hypo = _load(HYPO)
    ed_h, dir_h = _headline_from_hypothesis(hypo)
    ed = _latest_btc_eval_date(score) or ed_h or str(score.get("eval_date") or "")[:10] or None
    frozen = (_load(FROZEN_EVAL).get("metrics") or {}).get("price_directional_hit_rate")
    shadow_lane = _load(SHADOW)

    headline = _headline_dir(score, ed) if ed else dir_h
    if not headline:
        headline = dir_h
    shadow_row = _bbs_shadow_for_date(ed) if ed else None
    ms_drift = _load(MS_DRIFT)

    report = {
        "schema": "btrack_bbs_ms_hybrid_today_shadow_digest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "operator_use": "reference_only_not_order_trigger",
        "eval_date": ed,
        "headline_operational": {
            "lane": "frozen_kpi_a_ensemble_min_conf_0.18",
            "predicted_direction": headline,
            "frozen_30d_hit_rate": frozen,
        },
        "shadow_candidate": {
            "lane": "bbs_ms_hybrid_frozen30d_v1",
            "metrics_30d": (shadow_lane.get("metrics") or {}),
            "today_row": shadow_row,
            "agrees_with_headline": (
                headline is not None
                and shadow_row is not None
                and str(shadow_row.get("bbs_ms_hybrid")).lower() == headline
            ),
        },
        "constraints": [
            "do_not_replace_frozen_kpi_headline",
            "no_prophecy_to_live_auto_promotion",
            "90d_learn_audit_freeze",
        ],
        "ms_lens_drift_watch": (
            {
                "pointer": str(MS_DRIFT.relative_to(ROOT)).replace("\\", "/"),
                "anchor_ms_hybrid_rate": ms_drift.get("anchor_ms_hybrid_rate"),
                "latest_ms_hybrid_rate": ms_drift.get("latest_ms_hybrid_rate"),
                "ms_direction_diff_days": ms_drift.get("ms_direction_diff_days"),
                "note_ko": "MS per_date anchor vs latest; WATCH only [HYPO], not live trigger.",
            }
            if ms_drift
            else None
        ),
        "operator_lines": [],
    }
    op = report["operator_lines"]
    op.append("- [MKM-BBS-SHADOW] research_only; WATCH_HYBRID_SHADOW_LANE; auto_promote=false.")
    if ed and headline:
        agree = report["shadow_candidate"].get("agrees_with_headline")
        op.append(
            f"- [MKM-BBS-SHADOW] eval_date={ed} headline={headline} "
            f"shadow_agrees={agree}."
        )
    if ms_drift:
        op.append(
            f"- [MKM-BBS-SHADOW] ms_drift anchor={float(ms_drift.get('anchor_ms_hybrid_rate') or 0):.1%} "
            f"latest={float(ms_drift.get('latest_ms_hybrid_rate') or 0):.1%} "
            f"diff_days={ms_drift.get('ms_direction_diff_days')}."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"eval_date={ed} headline={headline} shadow={shadow_row.get('bbs_ms_hybrid') if shadow_row else None}")
    for line in report.get("operator_lines") or []:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
