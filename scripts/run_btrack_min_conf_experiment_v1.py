#!/usr/bin/env python3
"""B-track [HYPO] experiment: lower min_direction_confidence and compare hit-rate KPIs.

Does not modify production *_latest.json (baseline read-only). Writes comparison report only.
Does not enable live trading or change ALERT_1 / ALERT_1b policy.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_btrack_neutral_attribution_v1 import build_report

SCHEMA = "btrack_min_conf_experiment_v1"
DEFAULT_BASELINE_EVAL = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_REPORT = ROOT / "reports/btrack_min_conf_experiment_v1_latest.json"
DEFAULT_GRID_REPORT = ROOT / "reports/btrack_min_conf_experiment_grid_v1_latest.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_slice(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "directional_call_hits": m.get("directional_call_hits"),
        "price_hits": m.get("price_hits"),
        "headline_instrument": m.get("headline_instrument"),
        "scoring_mode": m.get("scoring_mode"),
    }


def _run_py(args: list[str], *, env: dict[str, str] | None = None) -> None:
    cmd = [sys.executable, *args]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr or proc.stdout}"
        )


def run_experiment(
    *,
    candidate_threshold: float,
    baseline_eval: Path,
    work_dir: Path,
    btc_only: bool = False,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    per_date_out = work_dir / f"per_date_minconf_{candidate_threshold:.2f}.json"
    score_out = work_dir / f"score_minconf_{candidate_threshold:.2f}.json"
    eval_out = work_dir / f"eval_minconf_{candidate_threshold:.2f}.json"
    attr_out = work_dir / f"neutral_attr_minconf_{candidate_threshold:.2f}.json"

    env = os.environ.copy()
    env["MKM_BTRACK_MIN_DIRECTION_CONFIDENCE"] = str(candidate_threshold)

    _run_py(
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
            "--output",
            str(per_date_out.relative_to(ROOT)),
        ],
        env=env,
    )
    score_cmd = [
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--recent-trading-days",
        "30",
        "--btc-csv",
        str(BTC_CSV.relative_to(ROOT)),
        "--per-date-direction-json",
        str(per_date_out.relative_to(ROOT)),
        "--output",
        str(score_out.relative_to(ROOT)),
    ]
    if btc_only:
        score_cmd.extend(["--hypothesis-json", "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"])
    else:
        score_cmd.extend(
            [
                "--force-dual-leg-panel",
                "--kospi-csv",
                str(KOSPI_CSV.relative_to(ROOT)),
            ]
        )
    _run_py(score_cmd, env=env)
    eval_cmd = [
        "scripts/eval_prophecy_hit_rate_v1.py",
        "--run-mode",
        "price",
        "--score-json",
        str(score_out.relative_to(ROOT)),
        "--output",
        str(eval_out.relative_to(ROOT)),
    ]
    _run_py(eval_cmd, env=env)

    per_date_doc = _load(per_date_out)
    cfg = _load(CFG) if CFG.is_file() else {}
    attr = build_report(per_date_doc, ensemble_cfg=cfg, eval_path=eval_out)
    attr_out.write_text(json.dumps(attr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "min_direction_confidence": candidate_threshold,
        "paths": {
            "per_date_json": str(per_date_out),
            "score_json": str(score_out),
            "eval_json": str(eval_out),
            "neutral_attribution_json": str(attr_out),
        },
        "metrics": _metrics_slice(_load(eval_out)),
        "neutral_attribution_summary": attr.get("summary"),
    }


def build_comparison(
    baseline_eval: Path,
    candidate: dict[str, Any],
    *,
    production_threshold: float,
) -> dict[str, Any]:
    base_ev = _load(baseline_eval)
    base_m = _metrics_slice(base_ev)
    cand_m = candidate["metrics"]
    delta = {}
    for key in (
        "price_directional_hit_rate",
        "price_hit_rate_on_directional_calls",
        "n_directional_calls",
        "n_neutral_predictions",
    ):
        b = base_m.get(key)
        c = cand_m.get(key)
        if isinstance(b, (int, float)) and isinstance(c, (int, float)):
            delta[key] = round(float(c) - float(b), 6)
    thresh = float(candidate["min_direction_confidence"])
    alert1_base_pass = float(base_m.get("price_directional_hit_rate") or 0) >= 0.5
    alert1_cand_pass = float(cand_m.get("price_directional_hit_rate") or 0) >= 0.5
    n_calls = int(cand_m.get("n_directional_calls") or 0)
    dir_rate = float(cand_m.get("price_hit_rate_on_directional_calls") or 0)
    alert1b_pass = n_calls >= 10 and dir_rate >= 0.5

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "production_threshold_unchanged": production_threshold,
        "baseline": {
            "label": f"production_snapshot_min_conf_{production_threshold:.2f}",
            "eval_path": str(baseline_eval),
            "metrics": base_m,
        },
        "candidate": candidate,
        "delta_candidate_minus_baseline": delta,
        "alert_policy_preview": {
            "ALERT_1_headline_all_rows": {
                "baseline_pass": alert1_base_pass,
                "candidate_pass": alert1_cand_pass,
            },
            "ALERT_1b_directional_skill": {
                "candidate_pass": alert1b_pass,
                "informational_only": True,
            },
            "note": "Preview only; production panel still uses *_latest at 0.25 until human promotes experiment.",
        },
        "recommendation": _recommendation_text(delta, thresh),
        "operator_lines": _operator_lines(base_m, cand_m, delta, thresh),
    }


def _recommendation_text(delta: dict[str, Any], thresh: float) -> str:
    dn = delta.get("n_directional_calls", 0)
    dh = delta.get("price_directional_hit_rate", 0)
    dd = delta.get("price_hit_rate_on_directional_calls", 0)
    if dn >= 3 and dh > 0.05:
        return (
            f"Candidate {thresh:.2f} adds calls and lifts all-rows hit — "
            "worth B-track weekly review; do not auto-change production config."
        )
    if dn >= 3 and dd <= 0:
        return (
            f"Candidate {thresh:.2f} adds calls but does not lift directional skill — "
            "prefer ensemble/weights work over threshold cut."
        )
    return (
        f"Candidate {thresh:.2f} modest KPI shift (Δcalls={dn}) — "
        "keep production 0.25; log experiment only."
    )


def _operator_lines(
    base_m: dict[str, Any],
    cand_m: dict[str, Any],
    delta: dict[str, Any],
    thresh: float,
) -> list[str]:
    def pct(v: Any) -> str:
        if v is None:
            return "n/a"
        return f"{float(v):.1%}"

    return [
        (
            f"- [MKM-MINCONF-EXP] baseline(0.25): all-rows {pct(base_m.get('price_directional_hit_rate'))} "
            f"dir-only {pct(base_m.get('price_hit_rate_on_directional_calls'))} "
            f"calls={base_m.get('n_directional_calls')}"
        ),
        (
            f"- [MKM-MINCONF-EXP] candidate({thresh:.2f}): all-rows {pct(cand_m.get('price_directional_hit_rate'))} "
            f"dir-only {pct(cand_m.get('price_hit_rate_on_directional_calls'))} "
            f"calls={cand_m.get('n_directional_calls')} "
            f"(Δcalls={delta.get('n_directional_calls')}, Δall-rows={delta.get('price_directional_hit_rate')})"
        ),
    ]


def build_grid_report(
    baseline_eval: Path,
    candidates: list[dict[str, Any]],
    *,
    production_threshold: float = 0.25,
) -> dict[str, Any]:
    base_ev = _load(baseline_eval)
    base_m = _metrics_slice(base_ev)
    rows: list[dict[str, Any]] = []
    for cand in sorted(candidates, key=lambda c: float(c["min_direction_confidence"])):
        cm = cand["metrics"]
        rows.append(
            {
                "min_direction_confidence": cand["min_direction_confidence"],
                "metrics": cm,
                "delta_vs_baseline": {
                    k: round(float(cm.get(k) or 0) - float(base_m.get(k) or 0), 6)
                    for k in (
                        "price_directional_hit_rate",
                        "price_hit_rate_on_directional_calls",
                        "n_directional_calls",
                        "n_neutral_predictions",
                    )
                    if cm.get(k) is not None and base_m.get(k) is not None
                },
                "alert_1_pass": float(cm.get("price_directional_hit_rate") or 0) >= 0.5,
                "alert_1b_pass": int(cm.get("n_directional_calls") or 0) >= 10
                and float(cm.get("price_hit_rate_on_directional_calls") or 0) >= 0.5,
            }
        )

    def _score_row(r: dict[str, Any]) -> tuple[float, float]:
        m = r["metrics"]
        return (
            float(m.get("price_directional_hit_rate") or 0),
            float(m.get("price_hit_rate_on_directional_calls") or 0),
        )

    best_all_rows = max(rows, key=lambda r: _score_row(r)[0]) if rows else None
    best_dir_only = max(rows, key=lambda r: _score_row(r)[1]) if rows else None
    grid_lines = [
        (
            f"- [MKM-MINCONF-GRID] baseline({production_threshold:.2f}): "
            f"all-rows {float(base_m.get('price_directional_hit_rate') or 0):.1%} "
            f"dir {float(base_m.get('price_hit_rate_on_directional_calls') or 0):.1%} "
            f"calls={base_m.get('n_directional_calls')}"
        )
    ]
    for r in rows:
        m = r["metrics"]
        t = r["min_direction_confidence"]
        grid_lines.append(
            f"- [MKM-MINCONF-GRID] {t:.2f}: all-rows {float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"dir {float(m.get('price_hit_rate_on_directional_calls') or 0):.1%} "
            f"calls={m.get('n_directional_calls')} "
            f"A1={'pass' if r['alert_1_pass'] else 'fail'} A1b={'pass' if r['alert_1b_pass'] else 'fail'}"
        )

    return {
        "schema": "btrack_min_conf_experiment_grid_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "production_threshold": production_threshold,
        "baseline_metrics": base_m,
        "candidates": rows,
        "best_by_all_rows_hit_rate": best_all_rows["min_direction_confidence"] if best_all_rows else None,
        "best_by_directional_hit_rate": best_dir_only["min_direction_confidence"] if best_dir_only else None,
        "note": "Grid is [HYPO] only; production min_direction_confidence unchanged until human promotes.",
        "operator_lines": grid_lines,
    }


def parse_threshold_grid(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(max(0.0, min(1.0, float(part))))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-threshold", type=float, default=None)
    ap.add_argument(
        "--grid",
        type=str,
        default="",
        help="Comma thresholds e.g. 0.18,0.20,0.22 (runs all; writes grid report).",
    )
    ap.add_argument("--baseline-eval", type=Path, default=DEFAULT_BASELINE_EVAL)
    ap.add_argument("--work-dir", type=Path, default=ROOT / "reports" / "btrack_min_conf_experiment_work")
    ap.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--grid-output", type=Path, default=DEFAULT_GRID_REPORT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--btc-only",
        action="store_true",
        help="Score/eval BTC single-leg 30d (no --force-dual-leg-panel); comparable to frozen KPI-A.",
    )
    args = ap.parse_args()

    if not args.baseline_eval.is_file():
        print(f"Missing baseline eval: {args.baseline_eval}", file=sys.stderr)
        return 2
    if not BTC_CSV.is_file():
        print("Missing BTC CSV for score.", file=sys.stderr)
        return 2
    if not args.btc_only and not KOSPI_CSV.is_file():
        print("Missing KOSPI CSV for dual-leg score (pass --btc-only to skip).", file=sys.stderr)
        return 2

    grid_raw = str(args.grid or "").strip()
    if grid_raw:
        thresholds = parse_threshold_grid(grid_raw)
        if not thresholds:
            print("Empty --grid.", file=sys.stderr)
            return 2
        candidates: list[dict[str, Any]] = []
        for t in thresholds:
            print(f"==> min_conf experiment threshold={t:.2f}", file=sys.stderr)
            candidates.append(
                run_experiment(
                    candidate_threshold=t,
                    baseline_eval=args.baseline_eval,
                    work_dir=args.work_dir,
                    btc_only=bool(args.btc_only),
                )
            )
        grid_report = build_grid_report(
            args.baseline_eval, candidates, production_threshold=0.25
        )
        if not args.stdout_only:
            args.grid_output.parent.mkdir(parents=True, exist_ok=True)
            args.grid_output.write_text(
                json.dumps(grid_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"WROTE: {args.grid_output.resolve()}")
        # Also write single-threshold report for best all-rows row
        best_t = grid_report.get("best_by_all_rows_hit_rate")
        best_cand = next(
            (c for c in candidates if float(c["min_direction_confidence"]) == float(best_t)),
            candidates[-1],
        )
        single = build_comparison(args.baseline_eval, best_cand, production_threshold=0.25)
        single["grid_pointer"] = str(args.grid_output)
        single["selected_as_best_all_rows_threshold"] = best_t
        if not args.stdout_only:
            args.output.write_text(json.dumps(single, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"WROTE: {args.output.resolve()} (best all-rows threshold={best_t})")
        for line in grid_report.get("operator_lines") or []:
            print(line)
        if args.stdout_only:
            print(json.dumps(grid_report, ensure_ascii=False, indent=2))
        return 0

    thresh = float(args.candidate_threshold if args.candidate_threshold is not None else 0.18)
    candidate = run_experiment(
        candidate_threshold=thresh,
        baseline_eval=args.baseline_eval,
        work_dir=args.work_dir,
        btc_only=bool(args.btc_only),
    )
    report = build_comparison(
        args.baseline_eval,
        candidate,
        production_threshold=0.25,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
        for line in report.get("operator_lines") or []:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
