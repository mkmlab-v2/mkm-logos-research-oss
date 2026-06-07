#!/usr/bin/env python3
"""Emit showroom_macro_horizon_2030_slice_v1 JSON from logos_macro_horizon_2030_scenario_v1 (read-only, no trade signals)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCE = ROOT / "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json"

_RATES_Q = "gp_2026_h2_fed_funds_upper_cut_ge_25bp_vs_2026q2"
_INFLATION_Q = "gp_2026_h2_kostat_cpi_yoy_below_2_any_month"
_LIQUIDITY_SIGNAL = "market_liquidity_stress"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _find_question(questions: list[dict[str, Any]], qid: str) -> dict[str, Any] | None:
    for row in questions:
        if row.get("question_id") == qid:
            return row
    return None


def _pct_display(p: float) -> str:
    return f"{round(p * 100)}%"


def _build_badges(doc: dict[str, Any]) -> list[dict[str, Any]]:
    questions = doc.get("macro_prophecy_questions") or []
    badges: list[dict[str, Any]] = []

    rates = _find_question(questions, _RATES_Q)
    if rates and rates.get("probability_0_1") is not None:
        badges.append(
            {
                "badge_id": "rates_path",
                "label_ko": "금리 경로 (Fed)",
                "value_display": _pct_display(float(rates["probability_0_1"])),
                "value_kind": "registry_p",
                "source_question_id": _RATES_Q,
                "non_gating": True,
            }
        )

    infl = _find_question(questions, _INFLATION_Q)
    if infl and infl.get("probability_0_1") is not None:
        badges.append(
            {
                "badge_id": "inflation_patch",
                "label_ko": "물가 패치 (KR CPI)",
                "value_display": _pct_display(float(infl["probability_0_1"])),
                "value_kind": "registry_p",
                "source_question_id": _INFLATION_Q,
                "non_gating": True,
            }
        )

    top_signals = (doc.get("macro_forward_anchor") or {}).get("top_risk_signals") or []
    liq = next((s for s in top_signals if s.get("name") == _LIQUIDITY_SIGNAL), None)
    if liq and liq.get("score") is not None:
        badges.append(
            {
                "badge_id": "liquidity_stress",
                "label_ko": "유동성 스트레스",
                "value_display": f"score {round(float(liq['score']), 3)}",
                "value_kind": "risk_signal",
                "non_gating": True,
            }
        )

    if len(badges) < 3:
        weights = (doc.get("scenario_probability_weights") or {}).get("global") or {}
        if weights.get("base") is not None and weights.get("stress") is not None:
            badges.append(
                {
                    "badge_id": "global_path_mix",
                    "label_ko": "글로벌 Base/Stress",
                    "value_display": f"{round(float(weights['base']) * 100)}/{round(float(weights['stress']) * 100)}",
                    "value_kind": "heuristic_weight",
                    "non_gating": True,
                }
            )

    return badges[:6]


def _build_phase_bands(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for phase in doc.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        pid = phase.get("phase_id")
        label = phase.get("label_ko")
        if not pid or not label:
            continue
        row: dict[str, Any] = {"phase_id": str(pid), "label_ko": str(label)}
        focus = phase.get("focus")
        if isinstance(focus, list) and focus:
            row["focus"] = [str(x) for x in focus[:4]]
        out.append(row)
    return out[:8]


def build_slice(doc: dict[str, Any], *, stale_hours: int = 24) -> dict[str, Any]:
    if doc.get("schema") != "logos_macro_horizon_2030_scenario_v1":
        raise ValueError("source schema must be logos_macro_horizon_2030_scenario_v1")

    now = _utc_now()
    gen = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    stale = (now + timedelta(hours=stale_hours)).replace(microsecond=0)
    stale_s = stale.isoformat().replace("+00:00", "Z")

    field = doc.get("field_primary") or {}
    weights = doc.get("scenario_probability_weights") or {}
    btc_w = (weights.get("by_axis") or {}).get("btc") or {}
    tri_btc = ((doc.get("tri_axis_scenarios") or {}).get("btc") or {})
    base_sc = tri_btc.get("base_scenario") or {}

    logos_overlay = doc.get("logos_chronology_overlay") or {}
    conflict = doc.get("conflict_resolver") or {}
    final_action = conflict.get("final_action") or field.get("decision_state") or "WATCH"

    badges = _build_badges(doc)
    if len(badges) < 3:
        raise ValueError("macro_badges: expected at least 3 badge rows from source")

    base_w = float(btc_w.get("base", 0.27))
    stress_w = float(btc_w.get("stress", 0.73))

    return {
        "schema_version": "showroom_macro_horizon_2030_slice_v1",
        "generated_at_utc": gen,
        "stale_after_utc": stale_s,
        "hypo_banner": "[HYPO] Macro horizon 2030 read-only map (narrative_template; not calibrated joint distribution)",
        "summary_one_line": (
            f"BTC-USD 2026–2030 scenario map · Field={field.get('regime_id', '—')} "
            f"{final_action} · base/stress {round(base_w * 100)}/{round(stress_w * 100)} heuristic · not investment advice."
        )[:500],
        "source_ref": {
            "path": "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json",
            "schema": "logos_macro_horizon_2030_scenario_v1",
            "generated_at_utc": str(doc.get("generated_at_utc") or gen),
            "scenario_kind": str(doc.get("scenario_kind") or "narrative_template"),
        },
        "no_trade_signals": True,
        "disclaimer_ref": "jemaai_showroom_v1",
        "final_action": str(final_action),
        "field_primary": {
            "regime_id": str(field.get("regime_id") or "unknown"),
            "decision_state": str(field.get("decision_state") or "WATCH"),
            "risk_warning_level": str(field.get("risk_warning_level") or "elevated"),
        },
        "macro_badges": badges,
        "btc_path": {
            "axis_id": "BTC-USD",
            "base_weight": base_w,
            "stress_weight": stress_w,
            "operator_posture": str(base_sc.get("operator_posture") or "watch_tighten"),
            "not_calibrated": True,
        },
        "phase_bands": _build_phase_bands(doc),
        "logos_era_overlay": {
            "secondary_label_ko": str(logos_overlay.get("secondary_label_ko") or "—"),
            "secondary_era_id": str(logos_overlay.get("secondary_era_id") or ""),
            "non_gating": True,
        },
        "boundary_ack": (
            "Showroom slice only; not Track A, live trading, MS/B2B headline, or price forecast."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", default="", help="Monorepo root")
    ap.add_argument(
        "--source",
        default="docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json",
        help="Source scenario JSON (repo-relative)",
    )
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json",
        help="Output slice JSON (repo-relative)",
    )
    ap.add_argument("--stale-hours", type=int, default=24)
    args = ap.parse_args()

    workspace = Path(args.workspace_root or os.environ.get("MKM_WORKSPACE_ROOT") or ROOT).resolve()
    source_path = workspace / args.source.replace("/", os.sep)
    out_path = workspace / args.out.replace("/", os.sep)

    if not source_path.is_file():
        print(
            f"build_showroom_macro_horizon_2030_slice_v1: missing source {source_path.relative_to(workspace)}",
            flush=True,
        )
        return 2

    doc = json.loads(source_path.read_text(encoding="utf-8"))
    try:
        snapshot = build_slice(doc, stale_hours=args.stale_hours)
    except ValueError as exc:
        print(f"build_showroom_macro_horizon_2030_slice_v1: {exc}", flush=True)
        return 3

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(workspace)}", flush=True)

    schema_path = workspace / "docs/final/schemas/showroom_macro_horizon_2030_slice_v1.schema.json"
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:
        return 0

    if schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=snapshot, schema=schema)
        except Exception as exc:  # pragma: no cover
            print(f"jsonschema validate failed: {exc}", flush=True)
            return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
