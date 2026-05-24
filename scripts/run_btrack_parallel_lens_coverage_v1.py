#!/usr/bin/env python3
"""[HYPO] Parallel pack: refresh sidecar for anchor panel, MS combo, overlap backtest."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
SIDECAR_OUT = ROOT / "reports/btrack_prophecy_score_insight_sidecar_anchor_30d_v1.json"
MS_PER_DATE = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
MS_SCORE = ROOT / "reports/btrack_prophecy_score_ms_anchor_v1_v2.json"
MS_EVAL = ROOT / "reports/prophecy_hit_rate_eval_ms_anchor_v1_v2.json"
PACK_OUT = ROOT / "reports/btrack_parallel_lens_coverage_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
ALIGNED = ROOT / "reports/btrack_aligned_30d_experiment_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _eval_slice(path: Path) -> dict[str, Any]:
    m = json.loads(path.read_text(encoding="utf-8"))["metrics"]
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
    }


def _coverage(sidecar: Path, dates: list[str]) -> dict[str, Any]:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _extract_lens_maps, _majority_sign, _sign_to_dir

    doc = json.loads(sidecar.read_text(encoding="utf-8"))
    my, sa, _, _ = _extract_lens_maps(doc)
    rows = []
    for d in dates:
        in_my = d in my
        in_sa = d in sa
        signs = [my.get(d, 0), sa.get(d, 0)]
        pred = _sign_to_dir(_majority_sign(signs))
        rows.append(
            {
                "eval_date": d,
                "in_sidecar": d in {str(r.get("eval_date") or "")[:10] for r in doc.get("per_date_features") or []},
                "myeongni_mapped": in_my,
                "sasang_mapped": in_sa,
                "predicted_direction": pred,
            }
        )
    active = [r for r in rows if r["predicted_direction"] != "neutral"]
    return {
        "n_dates": len(dates),
        "n_in_per_date_features": sum(1 for r in rows if r["in_sidecar"]),
        "n_directional_predictions": len(active),
        "n_neutral_predictions": len(rows) - len(active),
        "rows": rows,
    }


def main() -> int:
    py = sys.executable
    dates = json.loads(ANCHOR_DATES.read_text(encoding="utf-8"))["eval_dates"]

    def _rel(p: Path) -> str:
        p = p.resolve()
        try:
            return str(p.relative_to(ROOT.resolve()))
        except ValueError:
            return str(p)

    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py",
            "--score-json",
            _rel(ANCHOR_SCORE),
            "--out",
            _rel(SIDECAR_OUT),
        ]
    )
    cov = _coverage(SIDECAR_OUT, dates)

    _run(
        [
            py,
            "scripts/build_btrack_lens_combo_myeongni_sasang_per_date_v1.py",
            "--score-json",
            _rel(ANCHOR_SCORE),
            "--sidecar-json",
            _rel(SIDECAR_OUT),
            "--output",
            _rel(MS_PER_DATE),
        ]
    )
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            _rel(BTC),
            "--hypothesis-json",
            _rel(HYP),
            "--batch-eval-dates-json",
            _rel(ANCHOR_DATES),
            "--per-date-direction-json",
            _rel(MS_PER_DATE),
            "--panel-instrument",
            "btc",
            "--output",
            _rel(MS_SCORE),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(MS_SCORE),
            "--headline-instrument",
            "btc",
            "--output",
            _rel(MS_EVAL),
        ]
    )

    # Backtest on overlap dates only (sidecar per_date max)
    sidecar_dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in json.loads(SIDECAR_OUT.read_text(encoding="utf-8")).get("per_date_features") or []
            if str(r.get("eval_date") or "")[:10]
        }
    )
    overlap_score = ROOT / "reports/btrack_prophecy_score_anchor_overlap_v1.json"
    overlap_dates_path = ROOT / "reports/btrack_anchor_overlap_eval_dates_v1.json"
    overlap_dates_path.write_text(
        json.dumps({"eval_dates": sidecar_dates}, indent=2) + "\n", encoding="utf-8"
    )
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            _rel(BTC),
            "--hypothesis-json",
            _rel(HYP),
            "--batch-eval-dates-json",
            _rel(overlap_dates_path),
            "--panel-instrument",
            "btc",
            "--output",
            _rel(overlap_score),
        ]
    )
    bt_out = ROOT / "reports/prophecy_lens_combo_backtest_anchor_overlap_v1_latest.json"
    _run(
        [
            py,
            "scripts/run_prophecy_lens_combo_backtest_v1.py",
            "--score-json",
            _rel(overlap_score),
            "--sidecar-json",
            _rel(SIDECAR_OUT),
            "--target-instrument",
            "btc",
            "--logos-vote-mode",
            "omit",
            "--output",
            _rel(bt_out),
        ]
    )
    bt = json.loads(bt_out.read_text(encoding="utf-8"))
    ms_best = bt.get("best_strategy") or {}

    pack = {
        "schema": "btrack_parallel_lens_coverage_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "sidecar_path": str(SIDECAR_OUT),
        "sidecar_coverage_on_anchor_dates": cov,
        "ms_combo_eval": _eval_slice(MS_EVAL),
        "ms_combo_eval_prior": _eval_slice(ROOT / "reports/prophecy_hit_rate_eval_ms_anchor_panel_v1.json")
        if (ROOT / "reports/prophecy_hit_rate_eval_ms_anchor_panel_v1.json").is_file()
        else {},
        "lens_combo_backtest_overlap": {
            "score_dates": sidecar_dates,
            "best_strategy_id": ms_best.get("strategy_id"),
            "metrics": ms_best.get("metrics"),
        },
        "aligned_30d_pointer": str(ALIGNED) if ALIGNED.is_file() else None,
        "operator_lines": [
            "- [MKM-LENS-COV] Rebuilt sidecar through anchor score dates; compare ms_combo_eval vs prior stale sidecar.",
            "- [MKM-LENS-COV] Use directional_hit_rate_active from backtest for apples-to-apples with 75% headline.",
        ],
    }
    PACK_OUT.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {PACK_OUT.resolve()}")
    print("coverage", cov["n_directional_predictions"], "/", cov["n_dates"])
    print("ms_eval", pack["ms_combo_eval"])
    print("backtest active", (ms_best.get("metrics") or {}).get("directional_hit_rate_active"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
