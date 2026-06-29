#!/usr/bin/env python3
"""[HYPO] Build causal fABBA sidecar feature_lut JSON (B-track, non-gating meta only).

Does not modify Primary prophecy score path or Track A weights.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_fabba_sidecar_lib_v1 import build_sidecar_feature_lut_document

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_feature_lut_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--include-btc", action="store_true")
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--ngram-size", type=int, default=3)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--backend", choices=("auto", "apca_stub", "fabba"), default="auto")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.kospi_csv.is_file():
        raise SystemExit(f"missing kospi csv: {args.kospi_csv}")

    now = _utc_now()
    instruments = [
        build_sidecar_feature_lut_document(
            instrument_id="kospi",
            csv_path=args.kospi_csv,
            generated_at_utc=now,
            lookback=args.lookback,
            ngram_size=args.ngram_size,
            tol=args.tol,
            backend=args.backend,
            neutral_bps=args.neutral_bps,
            eval_days=args.eval_days,
            alpha=args.alpha,
        )
    ]
    if args.include_btc:
        if not args.btc_csv.is_file():
            raise SystemExit(f"missing btc csv: {args.btc_csv}")
        instruments.append(
            build_sidecar_feature_lut_document(
                instrument_id="btc",
                csv_path=args.btc_csv,
                generated_at_utc=now,
                lookback=args.lookback,
                ngram_size=args.ngram_size,
                tol=args.tol,
                backend=args.backend,
                neutral_bps=args.neutral_bps,
                eval_days=args.eval_days,
                alpha=args.alpha,
            )
        )

    doc = {
        "schema": "prophecy_fabba_sidecar_feature_lut_bundle_v1",
        "generated_at_utc": now,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "send_gate": "HOLD",
        "instruments": instruments,
        "reproduce": (
            f"py scripts/build_prophecy_fabba_sidecar_feature_lut_v1.py --eval-days {args.eval_days} "
            f"--lookback {args.lookback} --ngram-size {args.ngram_size} --neutral-bps {args.neutral_bps}"
            + (" --include-btc" if args.include_btc else "")
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"kospi_rows={instruments[0]['stats']['n_feature_rows']} "
        f"backend={instruments[0]['backend_meta'].get('backend')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
