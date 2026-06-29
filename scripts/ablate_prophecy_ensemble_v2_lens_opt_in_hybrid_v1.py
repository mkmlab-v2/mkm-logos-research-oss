#!/usr/bin/env python3
"""[HYPO] Ensemble v2 lens-only opt-in hybrid ablation (B-track, research_only).

Keeps v1 frozen-hypothesis score directions for price hit + instrument WF;
feeds v2 per-date directions only as lens WF source signal (opt-in field).

Does not mutate Track A, Primary score JSON, or live trading hooks.
"""

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
LENS_WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"
HIT_EVAL = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
GATES_EVAL = ROOT / "scripts/eval_prophecy_promotion_gates_v1.py"

DEFAULT_V1_SCORE = ROOT / "reports/btrack_prophecy_score_ensemble_v2_baseline_v1_latest.json"
DEFAULT_V2_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_V1_LENS = ROOT / "reports/prophecy_per_date_combo_walkforward_ensemble_v2_baseline_v1_latest.json"
DEFAULT_V2_LENS = ROOT / "reports/prophecy_per_date_combo_walkforward_ensemble_v2_lane_v1_latest.json"
DEFAULT_V1_INST = ROOT / "reports/prophecy_instrument_combo_walkforward_ensemble_v2_baseline_v1_latest.json"
DEFAULT_V1_GATES = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_baseline_v1_latest.json"
DEFAULT_V2_GATES = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_lane_v1_latest.json"
DEFAULT_PRIMARY_HIT = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"

HYBRID_SCORE = ROOT / "reports/btrack_prophecy_score_ensemble_v2_lens_opt_in_hybrid_v1_latest.json"
HYBRID_LENS = ROOT / "reports/prophecy_per_date_combo_walkforward_ensemble_v2_lens_opt_in_hybrid_v1_latest.json"
HYBRID_GATES = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_lens_opt_in_hybrid_v1_latest.json"
HYBRID_HIT = ROOT / "reports/prophecy_hit_rate_eval_ensemble_v2_lens_opt_in_hybrid_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_hybrid_ablation_v1_latest.json"

OPT_IN_FIELD = "ensemble_v2_lens_opt_in_direction"
SCHEMA = "prophecy_ensemble_v2_lens_opt_in_hybrid_ablation_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _v2_direction_map(v2_doc: dict[str, Any]) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for row in v2_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        inst = str(row.get("instrument") or "").strip().lower()
        d = str(row.get("predicted_direction") or "").strip().lower()
        if ed and inst and d in ("bull", "bear", "neutral"):
            out[(ed, inst)] = d
    return out


def _patch_v1_score_with_v2_lens_opt_in(
    v1_score: dict[str, Any],
    v2_map: dict[tuple[str, str], str],
) -> dict[str, Any]:
    doc = copy.deepcopy(v1_score)
    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise ValueError("v1 score missing rows")
    patched = 0
    missing = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        inst = str(row.get("instrument") or "").strip().lower()
        key = (ed, inst)
        v2_dir = v2_map.get(key)
        if v2_dir is None:
            missing += 1
            continue
        row[OPT_IN_FIELD] = v2_dir
        patched += 1
    meta = doc.setdefault("inputs", {})
    if isinstance(meta, dict):
        meta["ensemble_v2_lens_opt_in"] = {
            "field": OPT_IN_FIELD,
            "patched_rows": patched,
            "missing_v2_lookup_rows": missing,
            "note": "predicted_direction unchanged (v1); v2 used lens-only",
        }
    return doc


def _lane_from_artifacts(
    *,
    lane_id: str,
    lens_path: Path,
    score_path: Path,
    gates_path: Path,
    hit_path: Path | None = None,
) -> dict[str, Any]:
    lens = _load(lens_path) or {}
    gates = _load(gates_path) or {}
    agg = lens.get("aggregate") if isinstance(lens.get("aggregate"), dict) else {}
    hit_doc = _load(hit_path) if hit_path and hit_path.is_file() else None
    if hit_doc is None and lane_id == "v1_baseline_frozen":
        hit_doc = _load(DEFAULT_PRIMARY_HIT)
    pooled_hit = None
    if isinstance(hit_doc, dict):
        metrics = hit_doc.get("metrics") if isinstance(hit_doc.get("metrics"), dict) else {}
        pooled_hit = metrics.get("price_directional_hit_rate")
    return {
        "lane_id": lane_id,
        "lens_walkforward_json": str(lens_path),
        "score_json": str(score_path),
        "gates_json": str(gates_path),
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "combined_all_passed": gates.get("combined_all_passed"),
        "pooled_price_hit_rate": pooled_hit,
        "lens_strict_gate_passed": _gate_passed(gates, "per_date_lens", "lens_wf_mean_test_accuracy"),
    }


def _gate_passed(gates: dict[str, Any], track: str, gate_id: str) -> bool | None:
    tr = gates.get("tracks") or {}
    block = tr.get(track) if isinstance(tr, dict) else None
    if not isinstance(block, dict):
        return None
    for g in block.get("gates") or []:
        if isinstance(g, dict) and g.get("gate_id") == gate_id:
            return bool(g.get("passed"))
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1-score-json", type=Path, default=DEFAULT_V1_SCORE)
    ap.add_argument("--v2-directions-json", type=Path, default=DEFAULT_V2_DIRS)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--btc-csv", type=Path, default=ROOT / "research/market_data/btc_daily_external_yf.csv")
    ap.add_argument("--hybrid-score-out", type=Path, default=HYBRID_SCORE)
    ap.add_argument("--hybrid-lens-out", type=Path, default=HYBRID_LENS)
    ap.add_argument("--hybrid-gates-out", type=Path, default=HYBRID_GATES)
    ap.add_argument("--hybrid-hit-out", type=Path, default=HYBRID_HIT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-hybrid-run", action="store_true", help="Only patch score + write ablation pointers.")
    args = ap.parse_args(argv)

    v1_score = _load(args.v1_score_json)
    v2_dirs = _load(args.v2_directions_json)
    if not v1_score:
        print(f"missing v1 score: {args.v1_score_json}", file=sys.stderr)
        return 2
    if not v2_dirs:
        print(f"missing v2 directions: {args.v2_directions_json}", file=sys.stderr)
        return 2

    v2_map = _v2_direction_map(v2_dirs)
    if not v2_map:
        print("empty v2 direction map", file=sys.stderr)
        return 2

    hybrid_score = _patch_v1_score_with_v2_lens_opt_in(v1_score, v2_map)
    args.hybrid_score_out.parent.mkdir(parents=True, exist_ok=True)
    args.hybrid_score_out.write_text(json.dumps(hybrid_score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_hybrid_run:
        rc = _run(
            [
                sys.executable,
                str(LENS_WF),
                "--score-json",
                str(args.hybrid_score_out),
                "--btc-csv",
                str(args.btc_csv),
                "--n-folds",
                str(args.n_folds),
                "--include-source-direction-signal",
                "--include-expanded-prior-features",
                "--source-direction-field",
                OPT_IN_FIELD,
                "--output",
                str(args.hybrid_lens_out),
            ]
        )
        if rc != 0:
            return rc

        rc = _run(
            [
                sys.executable,
                str(HIT_EVAL),
                "--run-mode",
                "price",
                "--score-json",
                str(args.v1_score_json),
                "--headline-instrument",
                "auto",
                "--output",
                str(args.hybrid_hit_out),
            ]
        )
        if rc != 0:
            return rc

        rc = _run(
            [
                sys.executable,
                str(GATES_EVAL),
                "--promotion-track-mode",
                "dual",
                "--lens-walkforward-json",
                str(args.hybrid_lens_out),
                "--instrument-walkforward-json",
                str(DEFAULT_V1_INST),
                "--score-json",
                str(args.v1_score_json),
                "--output",
                str(args.hybrid_gates_out),
                "--calibration-note",
                "ensemble_v2_lens_opt_in_hybrid_v1",
            ]
        )
        if rc != 0:
            return rc

    lanes = [
        _lane_from_artifacts(
            lane_id="v1_baseline_frozen",
            lens_path=DEFAULT_V1_LENS,
            score_path=args.v1_score_json,
            gates_path=DEFAULT_V1_GATES,
            hit_path=DEFAULT_PRIMARY_HIT,
        ),
        _lane_from_artifacts(
            lane_id="v2_full_lane",
            lens_path=DEFAULT_V2_LENS,
            score_path=ROOT / "reports/btrack_prophecy_score_ensemble_v2_lane_v1_latest.json",
            gates_path=DEFAULT_V2_GATES,
        ),
    ]
    if args.hybrid_lens_out.is_file():
        lanes.append(
            _lane_from_artifacts(
                lane_id="hybrid_v1_score_v2_lens_opt_in",
                lens_path=args.hybrid_lens_out,
                score_path=args.v1_score_json,
                gates_path=args.hybrid_gates_out,
                hit_path=args.hybrid_hit_out,
            )
        )

    hybrid_lane = next((l for l in lanes if l["lane_id"] == "hybrid_v1_score_v2_lens_opt_in"), None)
    v1_lane = lanes[0]
    v2_lane = next((l for l in lanes if l["lane_id"] == "v2_full_lane"), None)
    v2_structural_hit = _load(ROOT / "reports/prophecy_hit_rate_eval_dual_v2_structural_v1_latest.json")
    v2_full_pooled_hit = None
    if isinstance(v2_structural_hit, dict):
        metrics = v2_structural_hit.get("metrics") if isinstance(v2_structural_hit.get("metrics"), dict) else {}
        v2_full_pooled_hit = metrics.get("price_directional_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "protocol": {
            "score_direction": "v1 frozen hypothesis (unchanged predicted_direction)",
            "lens_source_signal": f"v2 via {OPT_IN_FIELD}",
            "instrument_wf": "v1 baseline (unchanged)",
            "price_hit_eval": "v1 score panel",
        },
        "hybrid_score_json": str(args.hybrid_score_out),
        "lanes": lanes,
        "compare": {
            "v1_lens_mean": v1_lane.get("mean_test_accuracy"),
            "v2_full_lens_mean": v2_lane.get("mean_test_accuracy") if v2_lane else None,
            "hybrid_lens_mean": hybrid_lane.get("mean_test_accuracy") if hybrid_lane else None,
            "v1_pooled_hit": v1_lane.get("pooled_price_hit_rate"),
            "hybrid_pooled_hit": hybrid_lane.get("pooled_price_hit_rate") if hybrid_lane else None,
            "v2_full_pooled_hit": v2_full_pooled_hit,
            "hybrid_vs_v1_lens_pp": round(
                float(hybrid_lane["mean_test_accuracy"]) - float(v1_lane["mean_test_accuracy"]), 6
            )
            if hybrid_lane
            and hybrid_lane.get("mean_test_accuracy") is not None
            and v1_lane.get("mean_test_accuracy") is not None
            else None,
            "hybrid_vs_v2_full_lens_pp": round(
                float(hybrid_lane["mean_test_accuracy"]) - float(v2_lane["mean_test_accuracy"]), 6
            )
            if hybrid_lane
            and v2_lane
            and hybrid_lane.get("mean_test_accuracy") is not None
            and v2_lane.get("mean_test_accuracy") is not None
            else None,
        },
        "verdict_ko": [
            "Primary predicted_direction = v1 유지 → price hit 붕괴 방지",
            "v2는 lens WF source signal만 opt-in",
            "Track A·Primary score 자동 merge 금지",
        ],
        "reproduce": (
            f"py scripts/ablate_prophecy_ensemble_v2_lens_opt_in_hybrid_v1.py "
            f"--n-folds {args.n_folds}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output} hybrid_lens={out['compare'].get('hybrid_lens_mean')} "
        f"v1_hit={out['compare'].get('hybrid_pooled_hit')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
