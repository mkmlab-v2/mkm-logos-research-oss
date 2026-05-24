#!/usr/bin/env python3
"""[HYPO] Align 30d BTC experiments to a fixed eval-date panel (SSOT anchor score JSON)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANCHOR = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_aligned_30d_experiment_v1_latest.json"
WORK = ROOT / "reports/btrack_aligned_30d_work"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _btc_dates(anchor: Path) -> list[str]:
    doc = _load(anchor)
    dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in (doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
    )
    return [d for d in dates if d]


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _eval_metrics(path: Path) -> dict[str, Any]:
    m = _load(path).get("metrics") or {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "scoring_mode": m.get("scoring_mode"),
    }


def _reconcile_panels(anchor: Path, other: Path) -> dict[str, Any]:
    def rows_map(p: Path) -> dict[str, dict[str, Any]]:
        doc = _load(p)
        out: dict[str, dict[str, Any]] = {}
        for r in doc.get("rows") or []:
            if not isinstance(r, dict):
                continue
            if str(r.get("instrument") or "").lower() != "btc":
                continue
            ed = str(r.get("eval_date") or "")[:10]
            if ed:
                out[ed] = r
        return out

    a = rows_map(anchor)
    b = rows_map(other)
    da, db = set(a), set(b)
    overlap = sorted(da & db)
    pred_mismatch = sum(
        1
        for d in overlap
        if a[d].get("predicted_direction") != b[d].get("predicted_direction")
    )
    return {
        "anchor_n": len(da),
        "other_n": len(db),
        "only_anchor": sorted(da - db),
        "only_other": sorted(db - da),
        "overlap_n": len(overlap),
        "predicted_direction_mismatch_on_overlap": pred_mismatch,
    }


def main() -> int:
    ap = __import__("argparse").ArgumentParser(description=__doc__)
    ap.add_argument("--anchor-score", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--compare-score", type=Path, default=ROOT / "docs/final/artifacts/btrack_prophecy_score_30d_latest.json")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    dates = _btc_dates(args.anchor_score)
    if not dates:
        print("No BTC dates in anchor score.", file=sys.stderr)
        return 2

    WORK.mkdir(parents=True, exist_ok=True)
    dates_path = WORK / "anchor_eval_dates.json"
    dates_path.write_text(json.dumps({"eval_dates": dates}, indent=2) + "\n", encoding="utf-8")

    hypo = _load(DEFAULT_HYP)
    frozen_dir = str((hypo.get("prediction") or {}).get("direction") or "bear").strip().lower()

    per_date_v1 = WORK / "per_date_v1.json"
    score_frozen = WORK / "score_frozen_current_hypo.json"
    score_v1 = WORK / "score_v1_perdate.json"
    eval_frozen = WORK / "eval_frozen.json"
    eval_v1 = WORK / "eval_v1.json"
    eval_anchor = WORK / "eval_anchor_snapshot.json"

    py = sys.executable
    _run(
        [
            py,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--score-json",
            str(args.anchor_score.relative_to(ROOT)),
            "--ensemble-mode",
            "v1",
            "--output",
            str(per_date_v1.relative_to(ROOT)),
        ]
    )
    for score_out, per_date_json in (
        (score_frozen, None),
        (score_v1, per_date_v1),
    ):
        cmd = [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            str(DEFAULT_BTC.relative_to(ROOT)),
            "--hypothesis-json",
            str(DEFAULT_HYP.relative_to(ROOT)),
            "--batch-eval-dates-json",
            str(dates_path.relative_to(ROOT)),
            "--output",
            str(score_out.relative_to(ROOT)),
        ]
        if per_date_json is not None:
            cmd.extend(["--per-date-direction-json", str(per_date_json.relative_to(ROOT))])
        _run(cmd)

    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(args.anchor_score.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_anchor.relative_to(ROOT)),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_frozen.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_frozen.relative_to(ROOT)),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_v1.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_v1.relative_to(ROOT)),
        ]
    )

    # KPI-B WF on anchor panel
    kpi_b_score = WORK / "score_kpi_b_wf.json"
    kpi_b_eval = WORK / "eval_kpi_b_wf.json"
    _run(
        [
            py,
            "scripts/run_btrack_kpi_b_shadow_eval_v1.py",
            "--score-json",
            str(args.anchor_score.relative_to(ROOT)),
            "--score-out",
            str(kpi_b_score.relative_to(ROOT)),
            "--eval-out",
            str(kpi_b_eval.relative_to(ROOT)),
            "--summary-out",
            str((WORK / "kpi_b_summary.json").relative_to(ROOT)),
        ]
    )

    report = {
        "schema": "btrack_aligned_30d_experiment_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "anchor_score": str(args.anchor_score),
        "anchor_eval_dates": dates,
        "current_hypothesis_direction": frozen_dir,
        "panel_reconcile_vs_latest": _reconcile_panels(args.anchor_score, args.compare_score),
        "lanes": [
            {
                "lane": "anchor_snapshot_on_disk",
                "note": "Historical frozen panel (may use old hypo direction at build time).",
                "metrics": _eval_metrics(eval_anchor),
            },
            {
                "lane": "frozen_current_hypothesis_same_dates",
                "note": f"Re-score same {len(dates)} dates with current hypothesis {frozen_dir!r}.",
                "metrics": _eval_metrics(eval_frozen),
            },
            {
                "lane": "v1_per_date_same_dates",
                "metrics": _eval_metrics(eval_v1),
            },
            {
                "lane": "kpi_b_walkforward_same_dates",
                "metrics": _eval_metrics(kpi_b_eval),
            },
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for lane in report["lanes"]:
        m = lane["metrics"]
        print(
            f"{lane['lane']}: all={m.get('price_directional_hit_rate')} "
            f"dir={m.get('price_hit_rate_on_directional_calls')} n={m.get('n_evaluated')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
