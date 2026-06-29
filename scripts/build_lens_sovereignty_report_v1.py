#!/usr/bin/env python3
"""Build Lens Sovereignty Report v1 / v1.1 — market verdict [HYPO][research_only].

v1: WF daily KOSPI ablation only.
v1.1: adds role-contract horizon eval (sasang intensity / myeongni mid grid / logos macro).
Pack 0-B and weather prophecy rails stay isolated from market verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_BLUEPRINT = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1.json"
DEFAULT_WF = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
DEFAULT_COMPARE = ROOT / "docs/final/artifacts/kospi_lens_ablation_snapshot_vs_walkforward_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_latest.json"
DEFAULT_HORIZON = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json"
DEFAULT_BLUEPRINT_V1_1 = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1_1.json"
DEFAULT_OUT_V1_1 = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_1_latest.json"
DEFAULT_BLUEPRINT_V1_2 = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1_2.json"
DEFAULT_OUT_V1_2 = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_2_latest.json"
DEFAULT_SUPP_RAILS = ROOT / "docs/final/artifacts/lens_sovereignty_supplementary_rails_v1_2_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = list(doc.get("ranked_arms") or doc.get("arms") or [])
    return {str(r.get("arm_id")): r for r in rows if r.get("arm_id")}


def _metrics(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    m = row.get("metrics")
    return m if isinstance(m, dict) else {}


def _baseline_metrics_from_closes(
    eval_dates: list[str],
    closes: dict[str, float],
    *,
    neutral_bps: float,
) -> dict[str, dict[str, Any]]:
    from scripts.run_kospi_multilens_blend_backtest_v1 import _score_series

    def preds(const: str) -> dict[str, str]:
        return {d: const for d in eval_dates}

    bull = _score_series(preds("bull"), closes=closes, neutral_bps=neutral_bps)
    bear = _score_series(preds("bear"), closes=closes, neutral_bps=neutral_bps)
    n = int(bull.get("n_scored") or 0)
    coin = {
        "n_scored": n,
        "soft_hit_rate": 0.5 if n else None,
        "directional_hit_rate": round(
            sum(1 for d in eval_dates if d in closes) / max(n, 1) * 0.5, 4
        )
        if n
        else None,
        "note": "theoretical coin-flip soft_hit=0.5; directional undefined for random",
    }
    return {
        "always_bull_baseline": bull,
        "always_bear_baseline": bear,
        "coin_flip_baseline": coin,
    }


def _is_v1_1_blueprint(blueprint: dict[str, Any]) -> bool:
    schema = str(blueprint.get("schema") or "")
    return schema == "lens_sovereignty_blueprint_v1_1" or "V1-1" in str(
        blueprint.get("blueprint_id") or ""
    )


def _is_v1_2_blueprint(blueprint: dict[str, Any]) -> bool:
    schema = str(blueprint.get("schema") or "")
    return schema == "lens_sovereignty_blueprint_v1_2" or "V1-2" in str(
        blueprint.get("blueprint_id") or ""
    )


def _schema_version(blueprint: dict[str, Any]) -> str:
    if _is_v1_2_blueprint(blueprint):
        return "v1_2"
    if _is_v1_1_blueprint(blueprint):
        return "v1_1"
    return "v1"


def _weather_prophecy_rail(*, blueprint: dict[str, Any]) -> dict[str, Any]:
    rail = (blueprint.get("rail_separation") or {}).get("weather_prophecy") or {}
    rel = rail.get("optional_artifact")
    out: dict[str, Any] = {
        "forbidden_in_market_verdict": True,
        "note": rail.get("note"),
    }
    if not rel:
        out["artifact"] = {"present": False}
        return out
    path = ROOT / str(rel)
    if not path.is_file():
        out["artifact"] = {"path": str(path), "present": False}
        return out
    doc = _load_json(path)
    out["artifact"] = {
        "path": str(path),
        "present": True,
        "brier_score": doc.get("brier_score") or doc.get("mean_brier"),
        "rows": doc.get("rows") or doc.get("n_scored"),
    }
    return out


def _load_horizon_kospi_leg(horizon_doc: dict[str, Any]) -> dict[str, Any] | None:
    schema = str(horizon_doc.get("schema") or "")
    if schema == "three_lens_horizon_empirical_eval_v2_leg":
        return horizon_doc
    legs = horizon_doc.get("legs")
    if isinstance(legs, dict) and isinstance(legs.get("kospi"), dict):
        return legs["kospi"]
    return None


def _role_section_from_horizon_leg(
    leg: dict[str, Any],
    *,
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    contracts = blueprint.get("role_contracts") or {}
    v1_eval = leg.get("v1_direction_eval") or {}
    align = v1_eval.get("alignment_verdict") or {}
    per_lens = align.get("per_lens") or {}
    sasang_int = leg.get("sasang_intensity_eval") or {}
    myeongni_grid = leg.get("myeongni_horizon_grid") or {}
    logos_eval = leg.get("logos_per_date_eval") or {}

    def _pass_for(lens_key: str, gate: str) -> bool | None:
        if lens_key == "sasang" and gate == "intensity_pass":
            return bool(sasang_int.get("intensity_pass")) if sasang_int else None
        if lens_key == "myeongni" and gate == "contract_is_best":
            if not myeongni_grid:
                return None
            return bool(myeongni_grid.get("contract_is_best"))
        if lens_key == "logos":
            logos_row = per_lens.get("logos") or {}
            if logos_row.get("alignment_pass") is True:
                return True
            v2c = leg.get("v2_composite") or {}
            if v2c.get("hypothesis_supported_v2") is True:
                return True
            if logos_row or v2c:
                return False
            return None
        return None

    role_rows: dict[str, Any] = {}
    for lens_key in ("sasang", "myeongni", "logos"):
        spec = contracts.get(lens_key) or {}
        gate = str(spec.get("pass_gate") or "")
        passed = _pass_for(lens_key, gate.split()[0] if gate else "")
        role_rows[lens_key] = {
            "operational_role": spec.get("operational_role"),
            "eval_task": spec.get("eval_task"),
            "contract_pass": passed,
        }

    role_rows["sasang"].update(
        {
            "intensity_horizon_days": sasang_int.get("intensity_horizon_days"),
            "spearman_rank_corr": sasang_int.get("spearman_rank_corr"),
            "intensity_pass": sasang_int.get("intensity_pass"),
            "n_pairs": sasang_int.get("n_pairs"),
            "direction_horizon_alignment": per_lens.get("sasang"),
        }
    )
    role_rows["myeongni"].update(
        {
            "contract_horizon": myeongni_grid.get("contract_horizon"),
            "contract_soft_hit_rate": myeongni_grid.get("contract_soft_hit_rate"),
            "best_horizon": myeongni_grid.get("best_horizon"),
            "best_soft_hit_rate": myeongni_grid.get("best_soft_hit_rate"),
            "contract_is_best": myeongni_grid.get("contract_is_best"),
            "contract_horizon_rank": myeongni_grid.get("contract_horizon_rank"),
            "n_eval_dates": myeongni_grid.get("n_eval_dates"),
            "direction_horizon_alignment": per_lens.get("myeongni"),
        }
    )
    role_rows["logos"].update(
        {
            "best_variant_by_macro_soft": logos_eval.get("best_variant_by_macro_soft"),
            "variants": logos_eval.get("variants"),
            "direction_horizon_alignment": per_lens.get("logos"),
            "v2_composite": leg.get("v2_composite"),
        }
    )

    return {
        "schema": "lens_sovereignty_role_contract_eval_v1_1",
        "horizon_eval_source": "three_lens_horizon_empirical_eval_v2",
        "n_eval_dates": v1_eval.get("n_eval_dates"),
        "v1_alignment_hypothesis_supported": align.get("hypothesis_supported"),
        "roles": role_rows,
    }


def _decide_role_verdict(
    role_section: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    min_pass = int(policy.get("min_role_passes_for_aligned", 2))
    roles = role_section.get("roles") or {}
    passed = [k for k, v in roles.items() if isinstance(v, dict) and v.get("contract_pass") is True]
    lines = [f"role contract passes ({len(passed)}/3): {passed or 'none'}"]

    if len(passed) >= min_pass:
        return "ROLE_ALIGNED", lines, passed
    if len(passed) == 1:
        return "ROLE_PARTIAL", lines, passed
    return "ROLE_FAIL", lines, passed


def _pack0b_rail(*, blueprint: dict[str, Any]) -> dict[str, Any]:
    rail = (blueprint.get("rail_separation") or {}).get("pack0b_lora") or {}
    out: dict[str, Any] = {
        "forbidden_in_market_verdict": True,
        "reports": {},
    }
    for key in ("smoke_report", "final_report"):
        rel = rail.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if not path.is_file():
            out["reports"][key] = {"path": str(path), "present": False}
            continue
        doc = _load_json(path)
        out["reports"][key] = {
            "path": str(path),
            "present": True,
            "parse_ok_rate": doc.get("parse_ok_rate"),
            "alignment_pass_rate_raw": doc.get("alignment_pass_rate"),
            "rows": doc.get("rows"),
        }
    return out


def _decide_verdict(
    *,
    best_lens_soft: float | None,
    regime_soft: float | None,
    policy: dict[str, Any],
) -> tuple[str, list[str]]:
    baseline = float(policy.get("baseline_soft_hit_rate", 0.5))
    trash_pp = float(policy.get("trash_if_best_lens_wf_lte_baseline_plus_pp", 0.005))
    modify_pp = float(policy.get("modify_if_regime_wf_gte_best_lens_minus_pp", 0.002))
    lines: list[str] = []

    if best_lens_soft is None:
        return "MODIFY", ["missing best lens WF metric"]

    if best_lens_soft <= baseline + trash_pp:
        lines.append(
            f"best_lens_wf soft_hit {best_lens_soft:.4f} <= baseline+{trash_pp:.3f} "
            f"({baseline + trash_pp:.4f})"
        )
        return "TRASH", lines

    if regime_soft is not None and regime_soft >= best_lens_soft - modify_pp:
        lines.append(
            f"regime_only_wf {regime_soft:.4f} >= best_lens {best_lens_soft:.4f} - {modify_pp:.3f}"
        )
        return "MODIFY", lines

    lines.append(
        f"best_lens_wf {best_lens_soft:.4f} > baseline+{trash_pp:.3f}; "
        "regime-only does not dominate"
    )
    return "KEEP", lines


def build_report(
    *,
    blueprint: dict[str, Any],
    walkforward: dict[str, Any],
    compare: dict[str, Any] | None,
    baselines: dict[str, dict[str, Any]],
    horizon_leg: dict[str, Any] | None = None,
    supplementary_rails: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = blueprint.get("verdict_policy") or {}
    lens_arm_ids = list((blueprint.get("evaluation_arms") or {}).get("lens_arms") or [])
    arms = _arm_map(walkforward)

    wf_rows: list[dict[str, Any]] = []
    for arm_id in lens_arm_ids:
        row = arms.get(arm_id)
        m = _metrics(row)
        wf_rows.append(
            {
                "arm_id": arm_id,
                "soft_hit_rate_wf": m.get("soft_hit_rate"),
                "directional_hit_rate_wf": m.get("directional_hit_rate"),
                "n_scored_wf": m.get("n_scored"),
                "pred_neutral_rate": row.get("pred_neutral_rate") if row else None,
            }
        )

    baseline_rows = [
        {"arm_id": k, **v} for k, v in baselines.items()
    ]

    lens_only = [r for r in wf_rows if r.get("soft_hit_rate_wf") is not None]
    best_lens = max(lens_only, key=lambda r: float(r["soft_hit_rate_wf"])) if lens_only else None
    regime_row = next((r for r in wf_rows if r["arm_id"] == "regime_only_map"), None)

    best_soft = float(best_lens["soft_hit_rate_wf"]) if best_lens else None
    regime_soft = (
        float(regime_row["soft_hit_rate_wf"]) if regime_row and regime_row.get("soft_hit_rate_wf") is not None else None
    )
    verdict, verdict_lines = _decide_verdict(
        best_lens_soft=best_soft,
        regime_soft=regime_soft,
        policy=policy,
    )

    window = walkforward.get("window") if isinstance(walkforward.get("window"), dict) else {}
    ver = _schema_version(blueprint)
    v1_1 = ver in ("v1_1", "v1_2")
    v1_2 = ver == "v1_2"

    report: dict[str, Any] = {
        "schema": (
            "lens_sovereignty_report_v1_2"
            if v1_2
            else "lens_sovereignty_report_v1_1"
            if v1_1
            else "lens_sovereignty_report_v1"
        ),
        "generated_at_utc": _utc_now(),
        "blueprint_id": blueprint.get("blueprint_id"),
        "hypothesis_tier": blueprint.get("hypothesis_tier"),
        "research_only": True,
        "track_wall": blueprint.get("track_wall"),
        "headline_ssot": (
            "walkforward_plus_role_contract_plus_supplementary"
            if v1_2
            else "walkforward_plus_role_contract"
            if v1_1
            else "walkforward_only"
        ),
        "methodology_split": blueprint.get("methodology_split") if v1_1 else None,
        "window": window,
        "walkforward_source": str(DEFAULT_WF),
        "snapshot_vs_walkforward_source": str(DEFAULT_COMPARE) if compare else None,
        "daily_kospi_wf": {
            "verdict": verdict,
            "verdict_lines": verdict_lines,
            "baseline_arms_wf": baseline_rows,
            "lens_arms_wf": wf_rows,
            "best_lens_arm_wf": best_lens,
            "regime_only_arm_wf": regime_row,
            "note": "All arms flattened to next-day KOSPI direction — falsification layer only",
        },
        "baseline_arms_wf": baseline_rows,
        "lens_arms_wf": wf_rows,
        "best_lens_arm_wf": best_lens,
        "regime_only_arm_wf": regime_row,
        "narrative_temporal_axis_verdict": verdict,
        "verdict_lines": verdict_lines,
        "verdict_policy_applied": policy,
        "snapshot_vs_walkforward_verdict_lines": (
            (compare or {}).get("verdict_lines") or []
        ),
        "pack0b_rail": _pack0b_rail(blueprint=blueprint),
        "promotion_ready": False,
        "note": (
            "v1.2: daily WF + role-contract + supplementary rails (sentiment/weather/chronology). "
            "Pack 0-B isolated."
            if v1_2
            else "v1.1: daily WF + role-contract eval reported separately. "
            "Pack 0-B / weather prophecy isolated in rails."
            if v1_1
            else "Market verdict uses WF soft_hit_rate only. "
            "Pack 0-B alignment_pass_rate is isolated in pack0b_rail."
        ),
    }

    if v1_1:
        role_policy = blueprint.get("role_verdict_policy") or {}
        if horizon_leg:
            role_section = _role_section_from_horizon_leg(horizon_leg, blueprint=blueprint)
            role_verdict, role_lines, _role_passed = _decide_role_verdict(
                role_section, policy=role_policy
            )
            report["role_contract_eval"] = role_section
            report["role_contract_verdict"] = role_verdict
            report["role_verdict_lines"] = role_lines
            report["role_verdict_policy_applied"] = role_policy
            report["horizon_eval_source"] = str(
                (blueprint.get("data_provenance") or {}).get("horizon_eval_ssot")
                or DEFAULT_HORIZON
            )
        else:
            report["role_contract_eval"] = None
            report["role_contract_verdict"] = "ROLE_MISSING"
            report["role_verdict_lines"] = [
                "horizon eval artifact missing — run run_three_lens_horizon_empirical_eval_v2"
            ]
        report["weather_prophecy_rail"] = _weather_prophecy_rail(blueprint=blueprint)

    if v1_2 and supplementary_rails:
        report["supplementary_rails_v1_2"] = supplementary_rails
        report["supplementary_verdict"] = supplementary_rails.get("supplementary_verdict")
        report["supplementary_passes"] = supplementary_rails.get("supplementary_passes")
        if isinstance(report.get("role_contract_eval"), dict):
            roles = report["role_contract_eval"].get("roles") or {}
            sr = supplementary_rails.get("rails") or {}
            if isinstance(roles.get("sasang"), dict) and isinstance(sr.get("sasang_sentiment"), dict):
                roles["sasang"]["supplementary_sentiment"] = sr["sasang_sentiment"]
            if isinstance(roles.get("myeongni"), dict) and isinstance(sr.get("myeongni_weather_prophecy"), dict):
                roles["myeongni"]["supplementary_weather"] = sr["myeongni_weather_prophecy"]
            if isinstance(roles.get("logos"), dict) and isinstance(sr.get("logos_chronology"), dict):
                roles["logos"]["supplementary_chronology"] = sr["logos_chronology"]

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blueprint", type=Path, default=DEFAULT_BLUEPRINT)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--horizon-json", type=Path, default=None)
    ap.add_argument("--supplementary-rails-json", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    args = ap.parse_args()

    if not args.blueprint.is_file():
        print(f"missing blueprint: {args.blueprint}", file=sys.stderr)
        return 1
    if not args.walkforward_json.is_file():
        print(f"missing walkforward ablation: {args.walkforward_json}", file=sys.stderr)
        return 1

    blueprint = _load_json(args.blueprint)
    ver = _schema_version(blueprint)
    v1_1 = ver in ("v1_1", "v1_2")
    v1_2 = ver == "v1_2"
    if args.out is None:
        expected = (blueprint.get("expected_outputs") or {}).get("report_path")
        if expected:
            args.out = ROOT / str(expected)
        elif v1_2:
            args.out = DEFAULT_OUT_V1_2
        elif v1_1:
            args.out = DEFAULT_OUT_V1_1
        else:
            args.out = DEFAULT_OUT

    walkforward = _load_json(args.walkforward_json)
    compare = _load_json(args.compare_json) if args.compare_json.is_file() else None

    horizon_leg: dict[str, Any] | None = None
    if v1_1:
        horizon_path = args.horizon_json
        if horizon_path is None:
            rel = (blueprint.get("data_provenance") or {}).get("horizon_eval_ssot")
            horizon_path = ROOT / str(rel) if rel else DEFAULT_HORIZON
        if horizon_path.is_file():
            horizon_doc = _load_json(horizon_path)
            horizon_leg = _load_horizon_kospi_leg(horizon_doc)

    supplementary_rails: dict[str, Any] | None = None
    if v1_2:
        sup_path = args.supplementary_rails_json
        if sup_path is None:
            rel = (blueprint.get("data_provenance") or {}).get("supplementary_rails_ssot")
            sup_path = ROOT / str(rel) if rel else DEFAULT_SUPP_RAILS
        if sup_path.is_file():
            supplementary_rails = _load_json(sup_path)

    from scripts.run_kospi_multilens_blend_backtest_v1 import (
        EVOLUTION_RULES,
        KOSPI_CSV,
        _load_closes,
        _load_panel,
        _read_json,
    )

    panel_path = ROOT / str(
        (blueprint.get("data_provenance") or {}).get("panel_csv")
        or "reports/btrack_session_myeongni_panel_full_window_v1.csv"
    )
    panel = _load_panel(panel_path)
    closes = _load_closes(KOSPI_CSV)
    window = walkforward.get("window") if isinstance(walkforward.get("window"), dict) else {}
    date_from = str(window.get("date_from") or "1996-12-11")
    date_to = str(window.get("date_to") or "2026-06-05")
    eval_dates = sorted(d for d in panel if date_from <= d <= date_to and d in closes)

    rules = _read_json(EVOLUTION_RULES)
    neutral_bps = float(walkforward.get("neutral_bps") or args.neutral_bps)
    baselines = _baseline_metrics_from_closes(eval_dates, closes, neutral_bps=neutral_bps)

    report = build_report(
        blueprint=blueprint,
        walkforward=walkforward,
        compare=compare,
        baselines=baselines,
        horizon_leg=horizon_leg,
        supplementary_rails=supplementary_rails,
    )
    report["data_coverage"] = {
        "panel_rows_in_window": len([d for d in panel if date_from <= d <= date_to]),
        "wf_scored_from_ablation": window.get("n_calendar_days"),
        "ohlcv_joined_eval_dates": len(eval_dates),
        "kospi_csv": str(KOSPI_CSV),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary: dict[str, Any] = {
        "ok": True,
        "out": str(args.out),
        "schema": report.get("schema"),
        "daily_wf_verdict": report["narrative_temporal_axis_verdict"],
        "best_lens": report.get("best_lens_arm_wf"),
    }
    if v1_1:
        summary["role_contract_verdict"] = report.get("role_contract_verdict")
    if v1_2:
        summary["supplementary_verdict"] = report.get("supplementary_verdict")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
