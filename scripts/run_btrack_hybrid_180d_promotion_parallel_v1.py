#!/usr/bin/env python3
"""[HYPO] 180d hybrid ms_when_active_else_v1 panel + WF gates (parallel research lane)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "reports/btrack_hybrid_180d_work"
OUT = ROOT / "reports/btrack_hybrid_180d_promotion_parallel_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
ANCHOR_SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_anchor_30d_v1.json"
EXPANSION_WORK = ROOT / "reports/btrack_ms_180d_expansion_work"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _merge_hybrid_rows(v1_rows: list[dict], ms_rows: list[dict], dates: list[str]) -> list[dict]:
    v1 = {str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "neutral").lower() for r in v1_rows}
    ms = {str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "neutral").lower() for r in ms_rows}
    out: list[dict] = []
    for ed in dates:
        m = ms.get(ed, "neutral")
        pred = m if m in ("bull", "bear") else v1.get(ed, "neutral")
        out.append(
            {
                "eval_date": ed,
                "instrument": "btc",
                "predicted_direction": pred,
                "ensemble_mode": "hybrid_ms_when_active_else_v1",
                "sources": {"v1": v1.get(ed), "ms": m},
            }
        )
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument(
        "--use-expansion-ms",
        action="store_true",
        help="Use reports/btrack_ms_180d_expansion_work MS per-date (53d active typical).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    out_path = args.output
    if args.use_expansion_ms and args.output == OUT:
        out_path = ROOT / "reports/btrack_hybrid_180d_expansion_ms_promotion_parallel_v1_latest.json"

    py = sys.executable
    WORK.mkdir(parents=True, exist_ok=True)
    lock = WORK / ".score_writer.lock"
    v1_per = WORK / "v1_per_date.json"
    ms_per = WORK / "ms_per_date.json"
    hybrid_per = WORK / "hybrid_per_date.json"
    score = WORK / "score.json"
    lens_wf = WORK / "lens_walkforward.json"
    inst_wf = WORK / "instrument_walkforward.json"
    gates = WORK / "promotion_gates.json"
    hit_eval = WORK / "hit_rate_eval.json"

    def _build_v1_per() -> None:
        _run(
            [
                py,
                "scripts/build_btrack_ensemble_per_date_directions_v1.py",
                "--recent-trading-days",
                str(args.recent_trading_days),
                "--ensemble-mode",
                "v1",
                "--output",
                _rel(v1_per),
            ]
        )

    if args.use_expansion_ms and (EXPANSION_WORK / "ms_per_date_180d.json").is_file():
        ms_per.write_bytes((EXPANSION_WORK / "ms_per_date_180d.json").read_bytes())
        exp_v1 = EXPANSION_WORK / "v1_per_date_180d.json"
        if exp_v1.is_file():
            v1_per.write_bytes(exp_v1.read_bytes())
        else:
            _build_v1_per()
    else:
        _build_v1_per()
        score_anchor = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
        sidecar = (
            ANCHOR_SIDECAR
            if ANCHOR_SIDECAR.is_file()
            else ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
        )
        _run(
            [
                py,
                "scripts/build_btrack_lens_combo_myeongni_sasang_per_date_v1.py",
                "--score-json",
                _rel(score_anchor),
                "--sidecar-json",
                _rel(sidecar),
                "--output",
                _rel(ms_per),
            ]
        )

    v1_doc = json.loads(v1_per.read_text(encoding="utf-8"))
    ms_doc = json.loads(ms_per.read_text(encoding="utf-8"))
    dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in v1_doc.get("rows") or []
            if isinstance(r, dict)
        }
    )
    dates = [d for d in dates if d]

    hybrid_doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc(),
        "ensemble_mode": "hybrid_ms_when_active_else_v1",
        "research_only": True,
        "rows": _merge_hybrid_rows(v1_doc.get("rows") or [], ms_doc.get("rows") or [], dates),
    }
    hybrid_per.write_text(json.dumps(hybrid_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--hypothesis-json",
            _rel(HYPO),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--force-dual-leg-panel",
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--neutral-bps",
            str(args.neutral_bps),
            "--per-date-direction-json",
            _rel(hybrid_per),
            "--lock-file",
            _rel(lock),
            "--output",
            _rel(score),
            "--downside-force-bear-enable",
            "--downside-force-bear-lookback",
            "5",
            "--downside-force-bear-min-down-days",
            "3",
            "--downside-force-bear-min-cum-down-pct",
            "4.5",
        ]
    )
    _run(
        [
            py,
            "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
            "--score-json",
            _rel(score),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--target-instrument",
            "btc",
            "--n-folds",
            str(max(2, args.n_folds)),
            "--include-source-direction-signal",
            "--include-expanded-prior-features",
            "--output",
            _rel(lens_wf),
        ]
    )
    _run(
        [
            py,
            "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
            "--score-json",
            _rel(score),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--n-folds",
            str(max(2, args.n_folds)),
            "--output",
            _rel(inst_wf),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_promotion_gates_v1.py",
            "--promotion-track-mode",
            "dual",
            "--lens-walkforward-json",
            _rel(lens_wf),
            "--instrument-walkforward-json",
            _rel(inst_wf),
            "--score-json",
            _rel(score),
            "--hypothesis-json",
            _rel(HYPO),
            "--output",
            _rel(gates),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(score),
            "--headline-instrument",
            "btc",
            "--output",
            _rel(hit_eval),
        ]
    )

    g = json.loads(gates.read_text(encoding="utf-8"))
    m = json.loads(hit_eval.read_text(encoding="utf-8")).get("metrics") or {}
    pack = {
        "schema": "btrack_hybrid_180d_promotion_parallel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "use_expansion_ms": bool(args.use_expansion_ms),
        "panel_days": args.recent_trading_days,
        "combined_all_passed": g.get("combined_all_passed"),
        "soft_passed": g.get("soft_passed"),
        "promotion_recommendation": g.get("promotion_recommendation"),
        "hit_rate_all_rows": m.get("price_directional_hit_rate"),
        "wf_mean": (json.loads(lens_wf.read_text(encoding="utf-8")).get("aggregate") or {}).get(
            "mean_test_accuracy"
        ),
        "paths": {
            "hybrid_per_date": _rel(hybrid_per),
            "score": _rel(score),
            "gates": _rel(gates),
            "hit_eval": _rel(hit_eval),
        },
    }
    out_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"hybrid 180d: hit={pack['hit_rate_all_rows']} combined={pack['combined_all_passed']} "
        f"soft={pack['soft_passed']} rec={pack['promotion_recommendation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
