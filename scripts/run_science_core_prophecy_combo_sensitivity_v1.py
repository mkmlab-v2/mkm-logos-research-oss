#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core prophecy combo fee sensitivity [HYPO][research_only].

Runs lens combo backtest with fee-bps grid; extracts recommended-lane metrics.
Governance attach gate respected unless --force-run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_science_core_prophecy_combo_attach_v1 import resolve_governance_attach  # noqa: E402

DEFAULT_GOV = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_science_core_panel_v1.json"
DEFAULT_SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_science_core_panel_v1.json"
DEFAULT_SCIENCE_JSONL = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_FULL_OUT = ROOT / "reports/science_core_prophecy_combo_sensitivity_full_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/science_core_prophecy_combo_sensitivity_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_prophecy_combo_sensitivity_v1_latest.json"

LANE_TO_STRATEGY = {
    "science_plus_sasang": "science+sasang",
    "science_plus_myeongni": "science+myeongni",
    "science_plus_logos": "science+logos",
    "science_core": "science",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _strategy_row(ranked: list[dict[str, Any]], strategy_id: str) -> dict[str, Any] | None:
    for row in ranked:
        if str(row.get("strategy_id") or row.get("id") or "") == strategy_id:
            return row
    return None


def _metrics_slim(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    m = row.get("metrics") if isinstance(row.get("metrics"), dict) else row
    return {
        "strategy_id": row.get("strategy_id") or row.get("id"),
        "total_return": m.get("total_return"),
        "cagr": m.get("cagr"),
        "max_drawdown": m.get("max_drawdown"),
        "sharpe": m.get("sharpe"),
        "hit_rate": m.get("hit_rate"),
        "n_active_days": m.get("n_active_days"),
    }


def build_sensitivity_summary(
    *,
    backtest: dict[str, Any],
    recommended_lane: str | None,
    fee_grid: list[float],
) -> dict[str, Any]:
    strategy_id = LANE_TO_STRATEGY.get(str(recommended_lane or ""), "science+sasang")
    fee_rows: list[dict[str, Any]] = []
    for block in backtest.get("fee_sensitivity") or []:
        if not isinstance(block, dict):
            continue
        fee_bps = block.get("fee_bps")
        ranked = block.get("ranked_strategies") or []
        lane_row = _strategy_row(ranked, strategy_id)
        best = block.get("best_strategy")
        fee_rows.append(
            {
                "fee_bps": fee_bps,
                "recommended_lane_strategy_id": strategy_id,
                "recommended_lane_metrics": _metrics_slim(lane_row),
                "best_strategy_id": (best or {}).get("strategy_id") or (best or {}).get("id"),
                "best_strategy_metrics": _metrics_slim(best if isinstance(best, dict) else None),
                "recommended_lane_rank": next(
                    (i + 1 for i, r in enumerate(ranked) if (r.get("strategy_id") or r.get("id")) == strategy_id),
                    None,
                ),
            }
        )

    baseline = fee_rows[0] if fee_rows else {}
    base_metrics = (baseline.get("recommended_lane_metrics") or {}) if baseline else {}
    robust = all(
        (r.get("recommended_lane_metrics") or {}).get("total_return") is not None
        and float((r.get("recommended_lane_metrics") or {}).get("total_return") or 0) > 0
        for r in fee_rows
        if (r.get("fee_bps") or 0) <= 20
    )

    return {
        "schema": "science_core_prophecy_combo_sensitivity_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "recommended_lane": recommended_lane,
        "recommended_lane_strategy_id": strategy_id,
        "fee_bps_grid": fee_grid,
        "fee_sensitivity_rows": fee_rows,
        "baseline_fee_bps": baseline.get("fee_bps"),
        "baseline_recommended_lane_metrics": base_metrics,
        "robust_positive_return_up_to_20bps": robust,
        "headline_claim_allowed": False,
        "note_ko": "fee grid 민감도만 — CAGR 단일 headline·Track A·실매매 승격 근거 아님.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--target-instrument", default="kospi")
    ap.add_argument("--fee-bps-grid", default="0,5,10,15,20")
    ap.add_argument("--full-output", type=Path, default=DEFAULT_FULL_OUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    ap.add_argument("--force-run", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    fee_grid = [float(x.strip()) for x in str(args.fee_bps_grid).split(",") if x.strip()]
    gate = resolve_governance_attach(args.governance_json)
    if not gate.get("composite_attach_recommended") and not args.force_run:
        print("SKIP: composite attach not recommended", file=sys.stderr)
        return 0

    if args.dry_run:
        print(f"DRY_RUN fee_grid={fee_grid} lane={gate.get('recommended_lane')}")
        return 0

    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_prophecy_lens_combo_backtest_v1.py"),
        "--score-json",
        str(args.score_json),
        "--sidecar-json",
        str(args.sidecar_json),
        "--target-instrument",
        str(args.target_instrument),
        "--include-science-core",
        "--science-jsonl",
        str(args.science_jsonl),
        "--logos-vote-mode",
        "omit",
        "--fee-bps",
        str(fee_grid[0] if fee_grid else 5.0),
        "--fee-bps-grid",
        ",".join(str(x) for x in fee_grid),
        "--output",
        str(args.full_output),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        print(f"ERROR: backtest exit {proc.returncode}", file=sys.stderr)
        return proc.returncode

    backtest = _load_json(args.full_output)
    if not backtest:
        print(f"ERROR: missing backtest output {args.full_output}", file=sys.stderr)
        return 2

    doc = build_sensitivity_summary(
        backtest=backtest,
        recommended_lane=str(gate.get("recommended_lane") or "science_plus_sasang"),
        fee_grid=fee_grid,
    )
    doc["governance_gate"] = gate
    doc["full_backtest_path"] = str(args.full_output).replace("\\", "/")

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    base = doc.get("baseline_recommended_lane_metrics") or {}
    print(
        f"WROTE: {args.output.resolve()} lane={doc.get('recommended_lane_strategy_id')} "
        f"robust={doc.get('robust_positive_return_up_to_20bps')} cagr@base={base.get('cagr')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
