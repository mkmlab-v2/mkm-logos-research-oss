#!/usr/bin/env python3
"""[HYPO] One-shot parallel compare: frozen vs v1/v2 per-date on BTC 30d."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
FROZEN_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
FROZEN_EVAL = ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"
OUT = ROOT / "reports/btrack_parallel_compare_30d_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _eval_slice(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    m = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "scoring_mode": m.get("scoring_mode"),
    }


def _lane_per_date(mode: str, *, label: str) -> dict:
    per_date = ROOT / "reports" / f"btrack_ensemble_per_date_{label}_30d_v1.json"
    score = ROOT / "reports" / f"btrack_prophecy_score_{label}_30d_v1.json"
    ev = ROOT / "reports" / f"prophecy_hit_rate_eval_{label}_30d_v1.json"
    cmd_base = [sys.executable]
    _run(
        cmd_base
        + [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
            "--ensemble-mode",
            mode,
            "--output",
            str(per_date.relative_to(ROOT)),
        ]
    )
    _run(
        cmd_base
        + [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            "30",
            "--btc-csv",
            str(BTC.relative_to(ROOT)),
            "--hypothesis-json",
            str(HYP.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ]
    )
    _run(
        cmd_base
        + [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(ev.relative_to(ROOT)),
        ]
    )
    return {"label": label, "ensemble_mode": mode, "metrics": _eval_slice(ev), "paths": {"eval": str(ev)}}


def main() -> int:
    rows = [
        {"label": "frozen_kpi_a", "ensemble_mode": "frozen_single_direction", "metrics": _eval_slice(FROZEN_EVAL)},
    ]
    rows.append(_lane_per_date("v1", label="v1_prod_perdate"))
    rows.append(_lane_per_date("v2_confidence_fusion", label="v2_prod_perdate"))
    report = {
        "schema": "btrack_parallel_compare_30d_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "baseline_path": str(FROZEN_EVAL),
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT.resolve()}")
    for r in rows:
        m = r["metrics"]
        print(
            f"{r['label']}: all={m.get('price_directional_hit_rate')} "
            f"dir={m.get('price_hit_rate_on_directional_calls')} "
            f"calls={m.get('n_directional_calls')} neutral={m.get('n_neutral_predictions')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
