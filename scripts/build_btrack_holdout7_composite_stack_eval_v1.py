#!/usr/bin/env python3
"""[HYPO] Eval holdout7 composite stacks (signed_bull + advisory / oracle upper bound)."""
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

from scripts.btrack_wrong_dir_holdout_core_v1 import HOLDOUT_7_DEFAULT, holdout_dates_from_cf
from scripts.build_btrack_holdout7_uncovered_four_probe_v1 import (
    PROBE_LAYERS,
    _prepare_rows,
    match_probe_when,
)

DEFAULT_OUT = ROOT / "reports/btrack_holdout7_composite_stack_eval_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_holdout7_composite_stack_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ALERT_1 = 0.5

ORACLE_LAYER = {
    "slug": "holdout_neutral_ovn_neg_oracle_bear",
    "action": "force_bear",
    "apply_when": {
        "holdout_only": True,
        "preliminary_bull": True,
        "predicted_neutral": True,
        "overnight_negative": True,
    },
    "rationale_ko": "04-02 연구 상한: holdout neutral+abstain+OVN음 → bear 강제(oracle; 비승격)",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _layer(slug: str) -> dict[str, Any]:
    for layer in PROBE_LAYERS:
        if layer.get("slug") == slug:
            return layer
    raise KeyError(slug)


def _probe_row_eligible(row: dict[str, Any], layer: dict[str, Any]) -> bool:
    action = str(layer.get("action") or "force_neutral").lower()
    pred = str(row.get("predicted_direction") or "").lower()
    act = str(row.get("actual_direction") or "").lower()
    neutral_miss = pred == "neutral" and act in ("bull", "bear")
    if action == "advisory_only":
        return bool(row.get("is_wrong_direction")) or neutral_miss
    if action in ("force_bear", "force_bull", "force_neutral"):
        return bool(row.get("is_wrong_direction")) or neutral_miss or action == "force_bear"
    return bool(row.get("is_wrong_direction"))


def _apply_layers(
    base_doc: dict[str, Any],
    by_date: dict[str, dict[str, Any]],
    layers: list[dict[str, Any]],
    *,
    stack_id: str,
) -> dict[str, Any]:
    out = copy.deepcopy(base_doc)
    new_rows: list[dict[str, Any]] = []
    for r in out.get("rows") or []:
        if not isinstance(r, dict):
            new_rows.append(r)
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            new_rows.append(r)
            continue
        ed = str(r.get("eval_date") or "")[:10]
        ctx = by_date.get(ed) or r
        nr = dict(r)
        advisories: list[str] = []
        for layer in layers:
            if not match_probe_when(ctx, layer.get("apply_when") or {}):
                continue
            if not _probe_row_eligible(ctx, layer):
                continue
            action = str(layer.get("action") or "force_neutral").lower()
            slug = str(layer.get("slug") or "")
            if action == "advisory_only":
                advisories.append(slug)
                continue
            if action == "force_neutral":
                nr["predicted_direction"] = "neutral"
            elif action == "force_bear":
                nr["predicted_direction"] = "bear"
            elif action == "force_bull":
                nr["predicted_direction"] = "bull"
            nr["auxiliary_applied"] = True
            nr["auxiliary_probe_slug"] = slug
        if advisories:
            nr["auxiliary_advisory_slugs"] = advisories
        nr["composite_stack_id"] = stack_id
        new_rows.append(nr)
    out["rows"] = new_rows
    out["composite_stack_id"] = stack_id
    out["research_only"] = True
    return out


def _hit(pred: str, act: str) -> bool | None:
    p, a = pred.lower(), act.lower()
    if p not in ("bull", "bear") or a not in ("bull", "bear"):
        return None
    return p == a


def _holdout7_dates() -> list[str]:
    cf_dates = holdout_dates_from_cf(CF)
    merged = list(dict.fromkeys([*HOLDOUT_7_DEFAULT, *cf_dates]))
    return merged


def _holdout7_metrics(by_date: dict[str, dict[str, Any]], preds: dict[str, str]) -> dict[str, Any]:
    hits = n_dir = 0
    per_day: list[dict[str, Any]] = []
    wrong_neutralized = neutral_abstain_miss = wrong_remaining = 0
    for ed in sorted(_holdout7_dates()):
        ctx = by_date.get(ed) or {}
        act = str(ctx.get("actual_direction") or "").lower()
        base_pred = str(ctx.get("predicted_direction") or "neutral").lower()
        pred = str(preds.get(ed) or base_pred).lower()
        was_wrong = bool(ctx.get("is_wrong_direction"))
        was_neutral_miss = bool(ctx.get("is_neutral_abstain_miss"))
        if was_wrong and pred == "neutral":
            wrong_neutralized += 1
        elif was_wrong and pred in ("bull", "bear"):
            wrong_remaining += 1
        elif was_neutral_miss and pred == "neutral":
            neutral_abstain_miss += 1
        h = _hit(pred, act)
        day: dict[str, Any] = {
            "eval_date": ed,
            "pred": pred,
            "base_pred": base_pred,
            "actual": act,
            "was_wrong_direction": was_wrong,
            "was_neutral_abstain_miss": was_neutral_miss,
        }
        if h is not None:
            n_dir += 1
            if h:
                hits += 1
            day["hit"] = h
        else:
            day["hit"] = None
        per_day.append(day)
    return {
        "n_holdout_days": len(per_day),
        "n_directional_evaluated": n_dir,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n_dir, 6) if n_dir else None,
        "wrong_dir_neutralized": wrong_neutralized,
        "wrong_dir_remaining": wrong_remaining,
        "neutral_abstain_miss_remaining": neutral_abstain_miss,
        "ops_wrong_dir_cover_rate": round(wrong_neutralized / 6, 6),
        "per_day": per_day,
    }


def _anchor_metrics(by_date: dict[str, dict[str, Any]], preds: dict[str, str]) -> dict[str, Any]:
    anchor_dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in (_load(ANCHOR_SCORE).get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
    )
    hits = n = 0
    for ed in anchor_dates:
        ctx = by_date.get(ed) or {}
        act = str(ctx.get("actual_direction") or "").lower()
        pred = str(preds.get(ed) or ctx.get("predicted_direction") or "neutral").lower()
        h = _hit(pred, act)
        if h is None:
            continue
        n += 1
        if h:
            hits += 1
    return {
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
    }


def _pipeline_eval(per_path: Path, tag: str) -> dict[str, Any]:
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
    leg = (m.get("legs") or {}).get("btc") if isinstance(m.get("legs"), dict) else {}
    if not isinstance(leg, dict):
        leg = m
    h = float(leg.get("price_directional_hit_rate") or m.get("price_directional_hit_rate") or 0)
    return {
        "status": "ok",
        "price_directional_hit_rate": h,
        "alert_1_pass": h >= ALERT_1,
        "eval_path": str(ev_out),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-pipeline-eval", action="store_true")
    args = ap.parse_args()

    if not PER_DATE.is_file():
        print(f"Missing {PER_DATE}", file=sys.stderr)
        return 2

    holdout = _holdout7_dates()
    dump = _load(DUMP) if DUMP.is_file() else {"rows": []}
    base_doc = _load(PER_DATE)
    by_date = _prepare_rows(base_doc, holdout, dump)

    stacks: list[tuple[str, list[dict[str, Any]], bool]] = [
        ("signed_bull_only", [_layer("holdout_ovn_signed_bull")], False),
        (
            "composite_ops_advisory",
            [
                _layer("holdout_ovn_signed_bull"),
                _layer("holdout_prelim_bull_pred_neutral_miss"),
            ],
            False,
        ),
        (
            "oracle_0402_bear_flip_upper_bound",
            [_layer("holdout_ovn_signed_bull"), ORACLE_LAYER],
            True,
        ),
    ]

    results: list[dict[str, Any]] = []
    for stack_id, layers, is_oracle in stacks:
        patched = _apply_layers(base_doc, by_date, layers, stack_id=stack_id)
        per_path = WORK / f"per_date_{stack_id}.json"
        WORK.mkdir(parents=True, exist_ok=True)
        per_path.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        preds = {
            str(r.get("eval_date") or "")[:10]: str(r.get("predicted_direction") or "neutral").lower()
            for r in patched.get("rows") or []
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
        h7 = _holdout7_metrics(by_date, preds)
        anchor = _anchor_metrics(by_date, preds)
        pipe = {} if args.skip_pipeline_eval else _pipeline_eval(per_path, stack_id)
        results.append(
            {
                "stack_id": stack_id,
                "research_oracle": is_oracle,
                "layers": [layer.get("slug") for layer in layers],
                "holdout7": h7,
                "frozen30d_anchor": anchor,
                "pipeline_eval_30d": pipe,
                "per_date_path": str(per_path),
            }
        )

    def _ops_rank(r: dict[str, Any]) -> tuple[int, int, float]:
        h7 = r.get("holdout7") or {}
        neutralized = int(h7.get("wrong_dir_neutralized") or 0)
        remaining = int(h7.get("wrong_dir_remaining") or 0)
        rate = h7.get("price_directional_hit_rate")
        return (neutralized, -remaining, float(rate) if rate is not None else 0.0)

    best_ops = max((r for r in results if not r.get("research_oracle")), key=_ops_rank)
    oracle = next((r for r in results if r.get("research_oracle")), None)

    report = {
        "schema": "btrack_holdout7_composite_stack_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "stacks": results,
        "verdict_ko": (
            "ops composite(signed_bull+advisory)는 holdout7 wrong_dir 6/7 중립화·04-02는 advisory만; "
            "oracle bear-flip은 04-02 상한 연구용(비승격)."
        ),
        "best_ops_stack": best_ops.get("stack_id"),
        "oracle_upper_bound_holdout7": (oracle or {}).get("holdout7"),
        "operator_lines": [
            "- [MKM-H7-COMPOSITE] research_only; auto_promote=false.",
            f"- [MKM-H7-COMPOSITE] best_ops={best_ops.get('stack_id')} "
            f"wrong_neutralized={((best_ops.get('holdout7') or {}).get('wrong_dir_neutralized'))}/6 "
            f"neutral_miss={((best_ops.get('holdout7') or {}).get('neutral_abstain_miss_remaining'))} "
            f"anchor30d={((best_ops.get('frozen30d_anchor') or {}).get('price_directional_hit_rate'))}.",
        ],
    }
    if oracle:
        report["operator_lines"].append(
            f"- [MKM-H7-COMPOSITE] oracle_upper_bound holdout7="
            f"{((oracle.get('holdout7') or {}).get('price_directional_hit_rate'))} (non-promotable)."
        )

    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
