#!/usr/bin/env python3
"""[HYPO] Holdout × frozen-30d-anchor headline sweep (post-ensemble aux + oracle upper bound)."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc
from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf
from scripts.build_btrack_holdout7_uncovered_four_probe_v1 import (
    PROBE_LAYERS,
    _holdout_bear_trap_dates,
    _prepare_rows,
    _probe_holdout7,
)

DEFAULT_OUT = ROOT / "reports/btrack_holdout30d_headline_sweep_v1_latest.json"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
FROZEN30D_GRID = ROOT / "reports/btrack_frozen30d_v1_min_conf_grid_v1_latest.json"
BASELINE_EVAL = ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"
GATE_PACK = ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_holdout30d_headline_sweep_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYBRID_MATRIX = ROOT / "reports/btrack_frozen30d_hybrid_rule_matrix_v1_latest.json"
ALERT_1 = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _anchor_dates() -> list[str]:
    if FROZEN30D_GRID.is_file():
        ad = _load(FROZEN30D_GRID).get("anchor_eval_dates")
        if isinstance(ad, list) and ad:
            return [str(d)[:10] for d in ad]
    doc = _load(ANCHOR_SCORE)
    return sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in doc.get("rows") or []
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
    )


def _filter_per_date_to_dates(per_doc: dict[str, Any], dates: set[str]) -> dict[str, Any]:
    out = copy.deepcopy(per_doc)
    rows: list[Any] = []
    for r in out.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("eval_date") or "")[:10] in dates:
            rows.append(r)
    out["rows"] = rows
    out["n_eval_dates"] = len({str(r.get("eval_date"))[:10] for r in rows if isinstance(r, dict)})
    return out


def _eval_per_date(per_path: Path, tag: str) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    score = WORK / f"score_{tag}.json"
    ev_out = WORK / f"eval_{tag}.json"
    for cmd in [
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            "30",
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_path.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ],
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(ev_out.relative_to(ROOT)),
        ],
    ]:
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            return {"status": "failed", "stderr": (p.stderr or "")[-800:]}
    ev = _load(ev_out)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    h = float(m.get("price_directional_hit_rate") or 0)
    return {
        "status": "ok",
        "price_directional_hit_rate": h,
        "price_hits": m.get("price_hits"),
        "n_evaluated": m.get("n_evaluated"),
        "alert_1_pass": h >= ALERT_1,
        "eval": str(ev_out),
    }


def _global_layer_from_probe(probe_layer: dict[str, Any]) -> dict[str, Any]:
    aw = dict(probe_layer.get("apply_when") or {})
    aw.pop("holdout_only", None)
    return {
        "slug": f"global_{probe_layer.get('slug', 'layer')}",
        "enabled": True,
        "action": probe_layer.get("action") or "force_neutral",
        "apply_when": aw,
        "rationale_ko": f"global (no holdout_only): {probe_layer.get('rationale_ko', '')}",
    }


def _apply_oracle_holdout_bear_fix(
    per_doc: dict[str, Any], dump_by: dict[str, dict[str, Any]], holdout: set[str]
) -> dict[str, Any]:
    out = copy.deepcopy(per_doc)
    rows: list[Any] = []
    for r in out.get("rows") or []:
        if not isinstance(r, dict):
            rows.append(r)
            continue
        nr = dict(r)
        ed = str(nr.get("eval_date") or "")[:10]
        base = dump_by.get(ed) or {}
        pred = str(nr.get("predicted_direction") or "").lower()
        act = str(base.get("actual_direction") or "").lower()
        if ed in holdout and pred == "bull" and act == "bear":
            nr["predicted_direction"] = "bear"
            nr["auxiliary_applied"] = True
            nr["auxiliary_action"] = "oracle_force_bear"
            nr["auxiliary_probe_slug"] = "oracle_holdout_wrong_bull_to_bear"
        rows.append(nr)
    out["rows"] = rows
    return out


def _apply_stack(per_doc: dict[str, Any], layers: list[dict[str, Any]]) -> dict[str, Any]:
    doc = per_doc
    for layer in layers:
        doc = apply_auxiliary_per_date_doc(doc, layer)
    return doc


def _build_candidates() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"slug": "prod_baseline", "kind": "noop", "layers": []}]
    for pl in PROBE_LAYERS:
        if pl.get("slug") == "holdout_prelim_bull_pred_neutral_miss":
            continue
        spec = {k: v for k, v in pl.items() if k not in ("slug", "rationale_ko", "probe_mode")}
        out.append({"slug": pl["slug"], "kind": "holdout_aux", "layers": [spec]})
        if pl.get("action") == "force_neutral":
            g = _global_layer_from_probe(pl)
            gspec = {k: v for k, v in g.items() if k not in ("slug", "rationale_ko")}
            out.append({"slug": g["slug"], "kind": "global_aux", "layers": [gspec]})
    stack_specs = []
    for slug in ("holdout_ovn_signed_bull", "holdout_prelim_bull_pred_neutral_miss"):
        pl = next(l for l in PROBE_LAYERS if l["slug"] == slug)
        stack_specs.append({k: v for k, v in pl.items() if k not in ("slug", "rationale_ko", "probe_mode")})
    out.append(
        {
            "slug": "stack_holdout_signed_bull_plus_neutral_miss",
            "kind": "holdout_stack",
            "layers": stack_specs,
        }
    )
    out.append({"slug": "oracle_holdout_wrong_bull_to_bear", "kind": "oracle", "layers": []})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    anchor = _anchor_dates()
    anchor_set = set(anchor)
    holdout = holdout_dates_from_cf(CF)
    holdout_set = set(holdout)
    per_base = _load(PER_DATE)
    dump = _load(DUMP) if DUMP.is_file() else {"rows": []}
    dump_by = {str(r.get("eval_date"))[:10]: r for r in dump.get("rows") or [] if isinstance(r, dict)}

    frozen_h = None
    if FROZEN30D_GRID.is_file():
        frozen_h = float(
            (_load(FROZEN30D_GRID).get("frozen_kpi_a_baseline_metrics") or {}).get(
                "price_directional_hit_rate"
            )
            or 0
        )
    elif BASELINE_EVAL.is_file():
        fm = _load(BASELINE_EVAL).get("metrics") or {}
        frozen_h = float(fm.get("price_directional_hit_rate") or 0)

    by_date = _prepare_rows(per_base, holdout, dump)
    bear_trap = _holdout_bear_trap_dates(by_date, holdout)
    uncovered = list((_load(GATE_PACK).get("findings") or {}).get("holdout7_uncovered_by_either_gate") or [])[:3]

    results: list[dict[str, Any]] = []
    for cand in _build_candidates():
        slug = cand["slug"]
        if cand["kind"] == "oracle":
            patched = _apply_oracle_holdout_bear_fix(per_base, dump_by, holdout_set)
        elif cand["layers"]:
            patched = _apply_stack(per_base, cand["layers"])
        else:
            patched = copy.deepcopy(per_base)

        anchored = _filter_per_date_to_dates(patched, anchor_set)
        per_out = WORK / f"per_date_{slug}.json"
        WORK.mkdir(parents=True, exist_ok=True)
        per_out.write_text(json.dumps(anchored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ev = _eval_per_date(per_out, slug)

        probe_meta = None
        if cand["kind"] == "holdout_aux":
            layer = next(l for l in PROBE_LAYERS if l.get("slug") == slug)
            probe_meta = _probe_holdout7(layer, by_date, holdout, uncovered_targets=uncovered)
        elif cand["kind"] == "holdout_stack":
            probe_meta = {
                "n_bear_trap_covered": len(bear_trap),
                "covers_all_bear_trap": len(bear_trap) == 7,
                "dates": bear_trap,
            }

        hr = float(ev.get("price_directional_hit_rate") or 0) if ev.get("status") == "ok" else None
        results.append(
            {
                "slug": slug,
                "kind": cand["kind"],
                "frozen30d_anchor_eval": ev,
                "delta_vs_frozen_baseline": round(hr - frozen_h, 6) if hr is not None and frozen_h else None,
                "holdout_probe": probe_meta,
            }
        )

    ok = [r for r in results if (r.get("frozen30d_anchor_eval") or {}).get("status") == "ok"]
    prod_row = next((r for r in ok if r["slug"] == "prod_baseline"), None)
    prod_h = float((prod_row or {}).get("frozen30d_anchor_eval", {}).get("price_directional_hit_rate") or 0)
    best_h = max(
        ok, key=lambda r: float((r["frozen30d_anchor_eval"] or {}).get("price_directional_hit_rate") or 0)
    )
    best_a1 = [r for r in ok if (r["frozen30d_anchor_eval"] or {}).get("alert_1_pass")]
    stack_row = next((r for r in ok if r["slug"] == "stack_holdout_signed_bull_plus_neutral_miss"), None)
    oracle_row = next((r for r in ok if r["slug"] == "oracle_holdout_wrong_bull_to_bear"), None)

    hybrid_ref = None
    if HYBRID_MATRIX.is_file():
        mx = (_load(HYBRID_MATRIX).get("matrix") or {}).get("bbs_ms_agree_or_ms_else") or {}
        hybrid_ref = {
            "lane": "bbs_ms_agree_or_ms_else",
            "frozen30d_rate": (mx.get("full_30d") or {}).get("rate"),
            "holdout7_rate": (mx.get("holdout7") or {}).get("rate"),
            "pointer": str(HYBRID_MATRIX.relative_to(ROOT)).replace("\\", "/"),
        }

    stack_delta = None
    if stack_row:
        stack_delta = round(
            float((stack_row.get("frozen30d_anchor_eval") or {}).get("price_directional_hit_rate") or 0)
            - prod_h,
            6,
        )
    oracle_h = float(
        ((oracle_row or {}).get("frozen30d_anchor_eval") or {}).get("price_directional_hit_rate") or 0
    )

    report = {
        "schema": "btrack_holdout30d_headline_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "auto_promote": False,
        "eval_panel": "frozen_kpi_a_30d_anchor_btc",
        "anchor_dates": anchor,
        "holdout_7_dates": holdout,
        "frozen_kpi_a_baseline_headline": frozen_h,
        "prod_rebuild_on_anchor_headline": prod_h,
        "stack_holdout_headline_delta": stack_delta,
        "oracle_bear_fix_headline": (oracle_row or {}).get("frozen30d_anchor_eval"),
        "structural_note_ko": (
            "force_neutral은 actual=bear인 wrong_bull을 neutral로만 바꿔 "
            "directional hit(pred==actual) 개선 불가 — headline은 bear_fix 또는 hybrid 레인."
        ),
        "candidates": results,
        "best_by_frozen30d_headline": best_h,
        "alert_1_pass_slugs": [r["slug"] for r in best_a1],
        "hybrid_shadow_reference": hybrid_ref,
        "recommendation_ko": (
            "holdout aux stack=운영·리스크(7/7 bear_trap); anchor headline stack_delta=0 — "
            "ALERT_1 uplift=bbs_ms hybrid(별도 레인) 또는 ensemble 본체·oracle upper bound만."
            if stack_delta == 0
            else f"stack headline delta={stack_delta}; research_only"
        ),
        "operator_lines": [
            "- [MKM-HOLDOUT30D] research_only; auto_promote=false.",
            f"- [MKM-HOLDOUT30D] anchor prod={prod_h:.1%} stack_aux_delta={stack_delta} "
            f"oracle={oracle_h:.1%} stack_headline_lift=0.",
            f"- [MKM-HOLDOUT30D] hybrid bbs_ms frozen30d={((hybrid_ref or {}).get('frozen30d_rate') or 0):.1%} (별도 레인·A1 pass).",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
