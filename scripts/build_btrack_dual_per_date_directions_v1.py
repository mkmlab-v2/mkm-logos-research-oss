#!/usr/bin/env python3
"""Build KOSPI + BTC causal per-date directions and merge for dual-leg scoring.

Writes:
  - reports/btrack_ensemble_per_date_directions_dual_v1_latest.json (merged, instrument-tagged)
  - reports/btrack_ensemble_per_date_directions_v1_latest.json (BTC-only legacy alias)

research_only — not a live trading trigger.
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

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_KOSPI_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_DUAL_OUT = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_BTC_OUT = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"
BUILD_ONE = ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_build_one(
    *,
    target_instrument: str,
    recent_trading_days: int,
    bundle_json: Path,
    ensemble_config: Path,
    btc_csv: Path,
    kospi_csv: Path,
    ensemble_mode: str | None,
    out_path: Path,
    include_today: bool = False,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(BUILD_ONE),
        "--bundle-json",
        str(bundle_json),
        "--ensemble-config",
        str(ensemble_config),
        "--btc-csv",
        str(btc_csv),
        "--kospi-csv",
        str(kospi_csv),
        "--recent-trading-days",
        str(recent_trading_days),
        "--target-instrument",
        target_instrument,
        "--output",
        str(out_path),
    ]
    if include_today:
        cmd.append("--include-today")
    if ensemble_mode:
        cmd.extend(["--ensemble-mode", ensemble_mode])
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(
            f"build_btrack_ensemble_per_date_directions_v1 ({target_instrument}) exit {cp.returncode}: {cp.stderr.strip()}"
        )
    return _load_json(out_path)


def merge_dual_documents(
    *,
    kospi_doc: dict[str, Any],
    btc_doc: dict[str, Any],
    dual_out: Path,
    btc_legacy_out: Path | None = None,
) -> dict[str, Any]:
    k_rows = [r for r in (kospi_doc.get("rows") or []) if isinstance(r, dict)]
    b_rows = [r for r in (btc_doc.get("rows") or []) if isinstance(r, dict)]
    merged_rows = k_rows + b_rows
    dual_doc: dict[str, Any] = {
        "schema": "btrack_ensemble_per_date_directions_dual_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "research_only": True,
        "ensemble_mode": btc_doc.get("ensemble_mode") or kospi_doc.get("ensemble_mode"),
        "inputs": {
            "kospi_source": kospi_doc.get("inputs"),
            "btc_source": btc_doc.get("inputs"),
            "n_rows_kospi": len(k_rows),
            "n_rows_btc": len(b_rows),
        },
        "note": (
            "Merged KOSPI+BTC instrument-tagged causal per-date directions. "
            "Use with build_btrack_prophecy_score_from_ohlcv.py --force-dual-leg-panel "
            "--per-date-direction-json."
        ),
        "rows": merged_rows,
    }
    dual_out.parent.mkdir(parents=True, exist_ok=True)
    dual_out.write_text(json.dumps(dual_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if btc_legacy_out is not None:
        btc_legacy_out.write_text(json.dumps(btc_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dual_doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument(
        "--kospi-ensemble-config",
        type=Path,
        default=DEFAULT_KOSPI_CFG,
        help="KOSPI leg config (default disables overnight overlay per Phase B ablation).",
    )
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument(
        "--include-today",
        action="store_true",
        help="Include UTC today in per-date rows (morning forecast; hit-rate score still excludes today).",
    )
    ap.add_argument("--ensemble-mode", choices=("v1", "v2_confidence_fusion"), default=None)
    ap.add_argument("--dual-output", type=Path, default=DEFAULT_DUAL_OUT)
    ap.add_argument("--btc-legacy-output", type=Path, default=DEFAULT_BTC_OUT)
    ap.add_argument("--skip-btc-legacy-output", action="store_true")
    ap.add_argument("--work-dir", type=Path, default=None, help="Temp dir for intermediate JSON (default: dual-output parent).")
    args = ap.parse_args(argv)

    for p in (args.bundle_json, args.btc_csv, args.kospi_csv):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2
    if args.recent_trading_days < 1:
        print("--recent-trading-days must be >= 1", file=sys.stderr)
        return 2

    work = args.work_dir or args.dual_output.parent
    work.mkdir(parents=True, exist_ok=True)
    kospi_tmp = work / "_dual_per_date_kospi_tmp.json"
    btc_tmp = work / "_dual_per_date_btc_tmp.json"

    kospi_cfg = args.kospi_ensemble_config if args.kospi_ensemble_config.is_file() else args.ensemble_config
    kospi_doc = _run_build_one(
        target_instrument="kospi",
        recent_trading_days=args.recent_trading_days,
        bundle_json=args.bundle_json,
        ensemble_config=kospi_cfg,
        btc_csv=args.btc_csv,
        kospi_csv=args.kospi_csv,
        ensemble_mode=args.ensemble_mode,
        out_path=kospi_tmp,
        include_today=bool(args.include_today),
    )
    btc_doc = _run_build_one(
        target_instrument="btc",
        recent_trading_days=args.recent_trading_days,
        bundle_json=args.bundle_json,
        ensemble_config=args.ensemble_config,
        btc_csv=args.btc_csv,
        kospi_csv=args.kospi_csv,
        ensemble_mode=args.ensemble_mode,
        out_path=btc_tmp,
        include_today=bool(args.include_today),
    )
    legacy = None if args.skip_btc_legacy_output else args.btc_legacy_output
    dual_doc = merge_dual_documents(
        kospi_doc=kospi_doc,
        btc_doc=btc_doc,
        dual_out=args.dual_output,
        btc_legacy_out=legacy,
    )
    print(
        f"WROTE: {args.dual_output.resolve()} rows={len(dual_doc.get('rows') or [])} "
        f"(kospi={len(kospi_doc.get('rows') or [])} btc={len(btc_doc.get('rows') or [])})"
    )
    if legacy is not None:
        print(f"WROTE: {legacy.resolve()} (btc legacy alias)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
