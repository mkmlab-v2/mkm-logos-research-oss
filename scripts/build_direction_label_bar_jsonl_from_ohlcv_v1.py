#!/usr/bin/env python3
"""Build direction_label_bar_v1 JSONL from YFinance-style daily OHLCV (research, B-track).

Reuses the same 1-day return and neutral band as `build_btrack_prophecy_score_from_ohlcv.py`
(bull/bear/neutral) then maps to schema enum up/down/flat.

Horizons:
  1d — return from previous close to current close on label_date (first trading day has no label).
  5d — return from close five sessions earlier to current close (needs five prior rows).

Example:
  py scripts/build_direction_label_bar_jsonl_from_ohlcv_v1.py \\
    --csv research/market_data/kospi_daily_external_yf.csv \\
    --instrument-id KOSPI --horizon 1d --output docs/final/artifacts/direction_label_bar_kospi_1d_latest.jsonl \\
    --validate-labels
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows


def _daily_return(prev_row: dict[str, Any], cur_row: dict[str, Any]) -> float:
    pc = float(prev_row["close"])
    cc = float(cur_row["close"])
    if pc == 0:
        return 0.0
    return (cc - pc) / pc


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _to_udflat(three: str) -> str:
    return {"bull": "up", "bear": "down", "neutral": "flat"}[three]


def _label_hash(
    instrument_id: str,
    label_date: str,
    horizon: str,
    direction: str,
    neutral_bps: float,
) -> str:
    payload = (
        f"direction_label_bar_v1|{instrument_id}|{label_date}|{horizon}|{direction}|neutral_bps={neutral_bps}|v1"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_horizon_days(s: str) -> int:
    s = str(s).strip().lower()
    if s.endswith("d"):
        return int(s[:-1] or "1")
    if s.endswith("w"):
        return int(s[:-1] or "1") * 5
    return int(s)


def main() -> int:
    ap = argparse.ArgumentParser(description="OHLCV → direction_label_bar_v1 JSONL")
    ap.add_argument("--csv", type=Path, required=True, help="YFinance-style daily OHLCV CSV.")
    ap.add_argument("--instrument-id", type=str, required=True, help="e.g. KOSPI, BTC.")
    ap.add_argument("--horizon", type=str, default="1d", help="1d, 5d, … (trading-day steps).")
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--validate-labels",
        action="store_true",
        help="Run validate_news_observation_jsonl_v1.py --labels-jsonl-only on output.",
    )
    ap.add_argument("--max-rows", type=int, default=0, help="Cap output rows (0 = all).")
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    hz_display = str(args.horizon).strip().lower()
    if not hz_display.endswith(("d", "w")):
        hz_display = f"{hz_display}d"
    n_step = _parse_horizon_days(hz_display)
    if n_step < 1:
        print("ERROR: horizon must be positive", file=sys.stderr)
        return 1

    rows = load_kospi_yf_rows(csv_path)
    if len(rows) < n_step + 1:
        print("ERROR: not enough OHLCV rows for horizon", file=sys.stderr)
        return 1

    lines: list[str] = []
    nb = float(args.neutral_bps)
    ins = str(args.instrument_id).strip()

    if hz_display == "1d" or n_step == 1:
        for i in range(1, len(rows)):
            ret = _daily_return(rows[i - 1], rows[i])
            three = _actual_direction(ret, nb)
            ud = _to_udflat(three)
            ld = str(rows[i]["date"])[:10]
            rec = {
                "schema_version": "direction_label_bar_v1",
                "instrument_id": ins,
                "label_date": ld,
                "horizon": "1d",
                "direction": ud,
                "label_sha256": _label_hash(ins, ld, "1d", ud, nb),
                "neutral_bps": nb,
            }
            lines.append(json.dumps(rec, ensure_ascii=False))
            if args.max_rows > 0 and len(lines) >= args.max_rows:
                break
    else:
        # n-step return using calendar rows[i-n_step] -> rows[i]
        for i in range(n_step, len(rows)):
            ret = _daily_return(rows[i - n_step], rows[i])
            three = _actual_direction(ret, nb)
            ud = _to_udflat(three)
            ld = str(rows[i]["date"])[:10]
            hz_key = f"{n_step}d"
            rec = {
                "schema_version": "direction_label_bar_v1",
                "instrument_id": ins,
                "label_date": ld,
                "horizon": hz_key,
                "direction": ud,
                "label_sha256": _label_hash(ins, ld, hz_key, ud, nb),
                "neutral_bps": nb,
            }
            lines.append(json.dumps(rec, ensure_ascii=False))
            if args.max_rows > 0 and len(lines) >= args.max_rows:
                break

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} rows={len(lines)} horizon={hz_display}")

    if args.validate_labels:
        script = ROOT / "scripts" / "validate_news_observation_jsonl_v1.py"
        pr = subprocess.run(
            [
                sys.executable,
                str(script),
                "--labels-jsonl-only",
                "--labels-jsonl",
                str(args.output.resolve()),
                "--verify-label-hashes",
            ],
            cwd=str(ROOT),
        )
        return pr.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
