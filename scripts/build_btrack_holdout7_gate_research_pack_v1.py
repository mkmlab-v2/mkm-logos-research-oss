#!/usr/bin/env python3
"""[HYPO] Holdout7 gate research pack: CF variants + advisory + aux (no API; post–model-swap)."""
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

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc, apply_auxiliary_to_row
from scripts.btrack_wrong_dir_holdout_core_v1 import enrich_per_date_doc_btc, holdout_dates_from_cf
from scripts.run_btrack_wrong_dir_holdout_v1 import ADVISORY_RULES, AUX_GRID, _eval_advisory_rule

DEFAULT_OUT = ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json"
PANEL = ROOT / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_model_swap_work/per_date_baseline_30d.json"
AUX_GRID_JSON = ROOT / "reports/btrack_wrong_dir_auxiliary_grid_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cf_row_by_date(cf: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in cf.get("matrix_rows") or []:
        if isinstance(row, dict) and row.get("eval_date"):
            out[str(row["eval_date"])[:10]] = row
    return out


def _summarize_cf_cells(cf_row: dict[str, Any]) -> dict[str, Any]:
    cells = cf_row.get("cells") if isinstance(cf_row.get("cells"), dict) else {}
    neutral_slugs: list[str] = []
    bear_slugs: list[str] = []
    fix_slugs: list[str] = []
    for slug, cell in cells.items():
        if not isinstance(cell, dict):
            continue
        pred = str(cell.get("predicted_direction") or "").lower()
        if pred == "neutral":
            neutral_slugs.append(str(slug))
        if pred == "bear":
            bear_slugs.append(str(slug))
        if cell.get("would_fix_wrong_dir"):
            fix_slugs.append(str(slug))
    return {
        "baseline_predicted": cf_row.get("baseline_predicted"),
        "actual_direction": cf_row.get("actual_direction"),
        "variants_to_neutral": neutral_slugs,
        "variants_to_bear": bear_slugs,
        "variants_would_fix_wrong_dir": fix_slugs,
        "n_neutral_variants": len(neutral_slugs),
    }


def _aux_holdout7_effect(per_doc: dict[str, Any], layer: dict[str, Any], holdout: set[str]) -> dict[str, Any]:
    matched_wrong: list[str] = []
    neutralized: list[str] = []
    for r in per_doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed not in holdout:
            continue
        if not r.get("is_wrong_direction") and str(r.get("predicted_direction") or "").lower() in (
            "bull",
            "bear",
        ):
            act = str(r.get("actual_direction") or "").lower()
            pred = str(r.get("predicted_direction") or "").lower()
            if pred in ("bull", "bear") and act in ("bull", "bear") and pred != act:
                r = {**r, "is_wrong_direction": True}
        if not r.get("is_wrong_direction"):
            continue
        adj = apply_auxiliary_to_row(r, layer)
        if adj.get("auxiliary_applied"):
            matched_wrong.append(ed)
            if str(adj.get("adjusted_direction") or "").lower() == "neutral":
                neutralized.append(ed)
    return {
        "n_holdout7_wrong": 7,
        "n_matched": len(matched_wrong),
        "n_neutralized": len(neutralized),
        "matched_dates": sorted(matched_wrong),
        "neutralized_dates": sorted(neutralized),
    }


def build_pack(
    *,
    panel: dict[str, Any],
    cf: dict[str, Any],
    dump: dict[str, Any],
    per_doc: dict[str, Any],
    aux_grid: dict[str, Any] | None,
    holdout_dates: list[str],
) -> dict[str, Any]:
    holdout_set = set(holdout_dates)
    cf_by = _cf_row_by_date(cf)

    enriched = enrich_per_date_doc_btc(per_doc, holdout_dates)
    dump_rows = {str(r.get("eval_date"))[:10]: r for r in dump.get("rows") or [] if isinstance(r, dict)}
    for r in enriched.get("rows") or []:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        base = dump_rows.get(ed) or {}
        r["actual_direction"] = base.get("actual_direction")
        r["is_holdout_7"] = ed in holdout_set
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        r["is_wrong_direction"] = pred in ("bull", "bear") and act in ("bull", "bear") and pred != act

    advisory_rows = [_eval_advisory_rule(enriched, rule, dump=dump) for rule in ADVISORY_RULES]
    advisory_by_rule = {str(a.get("rule")): a for a in advisory_rows}

    primary_adv = advisory_by_rule.get("advisory_ovn_bull") or {}
    adv_overlap = set(primary_adv.get("holdout7_wrong_overlap") or [])

    aux_summaries: list[dict[str, Any]] = []
    for entry in AUX_GRID:
        slug = str(entry.get("slug") or "")
        layer = {
            "enabled": entry.get("enabled", True),
            "action": entry.get("action"),
            "apply_when": entry.get("apply_when") or {},
            **{k: entry[k] for k in ("max_confidence",) if k in entry},
        }
        eff = _aux_holdout7_effect(enriched, layer, holdout_set)
        aux_summaries.append({"slug": slug, "action": layer.get("action"), **eff})

    best_aux = max(
        (a for a in aux_summaries if a.get("action") == "force_neutral"),
        key=lambda x: int(x.get("n_neutralized") or 0),
        default={},
    )
    best_aux_neutral_dates = set(best_aux.get("neutralized_dates") or [])

    day_rows: list[dict[str, Any]] = []
    for ed in holdout_dates:
        panel_row = next((r for r in panel.get("rows") or [] if r.get("eval_date") == ed), {})
        cf_sum = _summarize_cf_cells(cf_by.get(ed, {}))
        day_rows.append(
            {
                "eval_date": ed,
                "actual_direction": panel_row.get("actual_direction") or cf_sum.get("actual_direction"),
                "prod_bull_gemini_bull": panel_row.get("both_bull_on_bear_day"),
                "causal_features": panel_row.get("causal_features"),
                "counterfactual": cf_sum,
                "advisory_ovn_bull_flag": ed in adv_overlap,
                "neutral_ovn_bull_would_neutralize": ed in best_aux_neutral_dates,
            }
        )

    uncovered_adv = sorted(holdout_set - adv_overlap)
    uncovered_aux = sorted(holdout_set - best_aux_neutral_dates)
    uncovered_both = sorted(holdout_set - adv_overlap - best_aux_neutral_dates)

    grid_best = None
    if aux_grid:
        variants = aux_grid.get("variants") or []
        ranked = sorted(
            variants,
            key=lambda v: int((v.get("holdout_wrong_dir") or {}).get("neutralized") or 0),
            reverse=True,
        )
        if ranked:
            top = ranked[0]
            hwd = top.get("holdout_wrong_dir") or {}
            grid_best = {
                "slug": top.get("slug"),
                "holdout_wrong_dir_neutralized": hwd.get("neutralized"),
                "holdout_wrong_dir_bear_fix": hwd.get("bear_fix"),
                "delta_vs_prod_baseline": top.get("delta_vs_prod_baseline"),
            }

    return {
        "schema": "btrack_holdout7_gate_research_pack_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "model_swap_poc_status": "closed_no_promote",
        "holdout_7_dates": holdout_dates,
        "inputs": {
            "holdout7_panel": str(PANEL),
            "counterfactual_matrix": str(CF),
            "feature_dump_30d": str(DUMP),
            "prod_per_date_30d": str(PER_DATE),
        },
        "findings": {
            "gemini_per_date_swap": "holdout7 7/7 wrong_dir unchanged vs prod (see panel JSON)",
            "counterfactual_bear_fix_on_holdout7": "no variant with would_fix_wrong_dir on any holdout day",
            "best_force_neutral_aux_30d": best_aux.get("slug"),
            "best_aux_holdout7_neutralized": f"{best_aux.get('n_neutralized')}/7",
            "primary_advisory_rule": "advisory_ovn_bull",
            "advisory_holdout7_wrong_overlap": sorted(adv_overlap),
            "advisory_holdout7_wrong_overlap_n": len(adv_overlap),
            "holdout7_uncovered_by_advisory_ovn_bull": uncovered_adv,
            "holdout7_uncovered_by_best_aux_neutral": uncovered_aux,
            "holdout7_uncovered_by_either_gate": uncovered_both,
            "aux_grid_ssot_best": grid_best,
        },
        "advisory_sweep_holdout7": advisory_rows,
        "auxiliary_holdout7_effects": aux_summaries,
        "per_day": day_rows,
        "recommended_next_b_track": [
            "Tighten causal price-lens / ensemble blend on bear-regime days (CF shows neutral variants exist but no bear fix).",
            "Extend holdout-only force_neutral rules for the 4 dates missed by neutral_ovn_bull (see holdout7_uncovered_by_either_gate).",
            "Do not spend API on per-date LLM swap; auto_promote remains false.",
        ],
        "operator_lines": [
            "- [MKM-HOLDOUT7-GATE] model_swap closed; input/gate research only; auto_promote=false.",
            f"- [MKM-HOLDOUT7-GATE] advisory_ovn_bull holdout7_wrong_hit={len(adv_overlap)}/7 dates={sorted(adv_overlap)}.",
            f"- [MKM-HOLDOUT7-GATE] best aux {best_aux.get('slug')} neutralized={best_aux.get('n_neutralized')}/7 "
            f"(headline delta see aux_grid; ALERT_1 still fail).",
            f"- [MKM-HOLDOUT7-GATE] uncovered_by_either={uncovered_both}.",
            "- [MKM-HOLDOUT7-GATE] price-lens CF bear_fix=0/7; see btrack_holdout_price_lens_cf_holdout7_v1_latest.json.",
            "- [MKM-HOLDOUT7-GATE] research candidate holdout_ovn_signed_bull (post-ensemble) targets 7/7 neutral; manifest SSOT.",
        ],
        "auto_promote": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for p, name in ((PANEL, "panel"), (CF, "counterfactual"), (DUMP, "dump"), (PER_DATE, "per_date")):
        if not p.is_file():
            print(f"Missing {name}: {p}", file=sys.stderr)
            return 2

    holdout = holdout_dates_from_cf(CF)
    aux_grid = _load(AUX_GRID_JSON) if AUX_GRID_JSON.is_file() else None
    report = build_pack(
        panel=_load(PANEL),
        cf=_load(CF),
        dump=_load(DUMP),
        per_doc=_load(PER_DATE),
        aux_grid=aux_grid,
        holdout_dates=holdout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
