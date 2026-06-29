#!/usr/bin/env python3
"""[HYPO] Sweep min-confidence for ensemble v2 lens-only opt-in hybrid (B-track).

Gates v2 source signal by row confidence; below threshold falls back to v1
predicted_direction. Score panel (price hit) stays v1 throughout.

research_only — no Track A merge.
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
DEFAULT_V1_SCORE = ROOT / "reports/btrack_prophecy_score_ensemble_v2_baseline_v1_latest.json"
DEFAULT_V2_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1_latest.json"
DEFAULT_SWEEP_DIR = ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1"
OPT_IN_FIELD = "ensemble_v2_lens_opt_in_direction"
SCHEMA = "prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1"
LENS_STRICT = 0.55
BASELINE_HYBRID_LENS = 0.513889
V1_LENS = 0.486111
V2_FULL_LENS = 0.555556
V1_POOLED_HIT = 0.45


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


def _v2_rows_by_key(v2_doc: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in v2_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        inst = str(row.get("instrument") or "").strip().lower()
        if ed and inst:
            out[(ed, inst)] = row
    return out


def _patch_hybrid_score(
    v1_score: dict[str, Any],
    v2_by_key: dict[tuple[str, str], dict[str, Any]],
    *,
    min_confidence: float,
) -> tuple[dict[str, Any], dict[str, int]]:
    doc = copy.deepcopy(v1_score)
    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise ValueError("v1 score missing rows")
    stats = {"v2_applied": 0, "v1_fallback": 0, "missing_v2": 0}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        inst = str(row.get("instrument") or "").strip().lower()
        v1_dir = str(row.get("predicted_direction") or "").strip().lower()
        v2_row = v2_by_key.get((ed, inst))
        if v2_row is None:
            stats["missing_v2"] += 1
            row[OPT_IN_FIELD] = v1_dir
            stats["v1_fallback"] += 1
            continue
        conf = float(v2_row.get("confidence") or 0.0)
        v2_dir = str(v2_row.get("predicted_direction") or "").strip().lower()
        if conf >= min_confidence and v2_dir in ("bull", "bear", "neutral"):
            row[OPT_IN_FIELD] = v2_dir
            stats["v2_applied"] += 1
        else:
            row[OPT_IN_FIELD] = v1_dir
            stats["v1_fallback"] += 1
    meta = doc.setdefault("inputs", {})
    if isinstance(meta, dict):
        meta["ensemble_v2_lens_opt_in_sweep"] = {
            "min_confidence": min_confidence,
            "field": OPT_IN_FIELD,
            **stats,
        }
    return doc, stats


def _run_lens_wf(score_path: Path, lens_out: Path, *, n_folds: int, btc_csv: Path) -> dict[str, Any] | None:
    cmd = [
        sys.executable,
        str(LENS_WF),
        "--score-json",
        str(score_path),
        "--btc-csv",
        str(btc_csv),
        "--n-folds",
        str(n_folds),
        "--include-source-direction-signal",
        "--include-expanded-prior-features",
        "--source-direction-field",
        OPT_IN_FIELD,
        "--output",
        str(lens_out),
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        return None
    doc = _load(lens_out)
    if not doc:
        return None
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    return {
        "exit_code": rc,
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
        "fraction_test_beats_always_bull": agg.get("fraction_test_beats_always_bull"),
        "lens_json": str(lens_out),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confidence-grid", default="0,0.08,0.1,0.12,0.15,0.18,0.2,0.25,0.3")
    ap.add_argument("--v1-score-json", type=Path, default=DEFAULT_V1_SCORE)
    ap.add_argument("--v2-directions-json", type=Path, default=DEFAULT_V2_DIRS)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--sweep-dir", type=Path, default=DEFAULT_SWEEP_DIR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    v1_score = _load(args.v1_score_json)
    v2_dirs = _load(args.v2_directions_json)
    if not v1_score or not v2_dirs:
        print("missing v1 score or v2 directions", file=sys.stderr)
        return 2

    v2_by_key = _v2_rows_by_key(v2_dirs)
    grid = [float(x.strip()) for x in str(args.confidence_grid).split(",") if x.strip()]
    args.sweep_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_key = (-1.0, -1.0)
    first_strict_pass: dict[str, Any] | None = None

    for conf in grid:
        slug = str(conf).replace(".", "p")
        score_path = args.sweep_dir / f"hybrid_score_conf_{slug}.json"
        lens_path = args.sweep_dir / f"lens_wf_conf_{slug}.json"
        hybrid_score, stats = _patch_hybrid_score(v1_score, v2_by_key, min_confidence=conf)
        score_path.write_text(json.dumps(hybrid_score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        wf = _run_lens_wf(score_path, lens_path, n_folds=args.n_folds, btc_csv=args.btc_csv)
        if wf is None:
            print(f"conf>={conf} lens WF failed", file=sys.stderr)
            return 1
        lm = wf.get("mean_test_accuracy")
        strict_pass = lm is not None and float(lm) >= LENS_STRICT
        row = {
            "min_confidence": conf,
            "v2_applied_rows": stats["v2_applied"],
            "v1_fallback_rows": stats["v1_fallback"],
            "missing_v2_rows": stats["missing_v2"],
            "lens_mean_test_accuracy": lm,
            "lens_stdev_test_accuracy": wf.get("stdev_test_accuracy"),
            "lens_strict_gate_passed": strict_pass,
            "pooled_price_hit_unchanged_v1": V1_POOLED_HIT,
            "hybrid_score_json": str(score_path),
            "lens_walkforward_json": str(lens_path),
            **wf,
        }
        rows.append(row)
        print(
            f"conf>={conf} lens={lm} v2_rows={stats['v2_applied']} strict={strict_pass}",
            file=sys.stderr,
        )
        if strict_pass and first_strict_pass is None:
            first_strict_pass = row
        if lm is not None:
            key = (float(lm), float(stats["v2_applied"]))
            if key > best_key:
                best_key = key
                best = row

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "protocol": {
            "neutral_bps": 2.0,
            "recent_trading_days": 180,
            "n_folds": args.n_folds,
            "price_hit_fixed_v1": V1_POOLED_HIT,
            "opt_in_field": OPT_IN_FIELD,
        },
        "reference": {
            "v1_lens_mean": V1_LENS,
            "v2_full_lens_mean": V2_FULL_LENS,
            "ungated_hybrid_lens_mean": BASELINE_HYBRID_LENS,
            "lens_strict_threshold": LENS_STRICT,
        },
        "rows": rows,
        "best_by_lens_mean": best,
        "first_lens_strict_pass": first_strict_pass,
        "verdict_ko": [
            "price hit = v1 고정; v2는 confidence-gated lens source only",
            "strict lens 55% 통과 시에도 Track A auto-merge 금지",
        ],
        "reproduce": (
            f"py scripts/run_prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1.py "
            f"--n-folds {args.n_folds}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    best_lm = best.get("lens_mean_test_accuracy") if best else None
    print(f"WROTE: {args.output} best_conf={best.get('min_confidence') if best else None} lens={best_lm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
