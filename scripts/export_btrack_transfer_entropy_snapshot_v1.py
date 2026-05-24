#!/usr/bin/env python3
"""Export Transfer Entropy snapshot for B-track pathology mapping (read-only, [HYPO]).

Resolution order:
  1) --source-json  (monitor / regime dump; nested transfer_entropy keys)
  2) Known candidate paths (monitoring_latest.json from dump script)
  3) TransferEntropyMarketRegimeDetector on BTC CSV (btrack_probe_v1)
  4) Legacy te_proxy_btc_returns_v1 fallback

Output: docs/final/artifacts/btrack_transfer_entropy_snapshot_v1_latest.json
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "core"))

DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_transfer_entropy_snapshot_v1_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"

TE_CANDIDATE_PATHS: tuple[Path, ...] = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "monitoring_latest.json",
    ROOT / "reports" / "btrack_transfer_entropy_probe_latest.json",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _find_te_value(obj: Any, *, depth: int = 0) -> float | None:
    if depth > 8:
        return None
    if isinstance(obj, dict):
        if "transfer_entropy" in obj:
            try:
                return float(obj["transfer_entropy"])
            except (TypeError, ValueError):
                pass
        for v in obj.values():
            found = _find_te_value(v, depth=depth + 1)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj[:50]:
            found = _find_te_value(item, depth=depth + 1)
            if found is not None:
                return found
    return None


def _method_from_monitor_doc(doc: dict[str, Any]) -> str:
    regime = doc.get("regime_analysis") if isinstance(doc.get("regime_analysis"), dict) else {}
    impl = regime.get("implementation") if isinstance(regime, dict) else None
    if impl:
        return f"transfer_entropy_detector_{impl}"
    if doc.get("schema") == "unified_trading_monitor_snapshot_v1":
        return "monitor_snapshot_v1"
    return "monitor_json"


def _extract_from_source(path: Path) -> tuple[float | None, str]:
    doc = _read_json(path)
    if doc is None:
        return None, "json_parse_failed"
    val = _find_te_value(doc)
    if val is None:
        return None, "transfer_entropy_not_found"
    return val, _method_from_monitor_doc(doc)


def _load_btc_returns(csv_path: Path, *, lookback: int) -> list[float]:
    if not csv_path.is_file():
        return []
    rows: list[tuple[str, float]] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date = (row.get("Date") or row.get("date") or "").strip()
            close_raw = row.get("Close") or row.get("close") or row.get("Adj Close")
            try:
                close = float(close_raw) if close_raw not in (None, "") else None
            except (TypeError, ValueError):
                close = None
            if date and close is not None and close > 0:
                rows.append((date, close))
    if len(rows) < 2:
        return []
    rows.sort(key=lambda t: t[0])
    rets: list[float] = []
    for i in range(1, len(rows)):
        p0, p1 = rows[i - 1][1], rows[i][1]
        if p0 > 0:
            rets.append((p1 - p0) / p0)
    return rets[-max(lookback + 1, 5) :]


async def _run_detector(returns: list[float], *, lookback: int) -> float | None:
    import numpy as np
    from transfer_entropy_market_regime_detector import TransferEntropyMarketRegimeDetector

    det = TransferEntropyMarketRegimeDetector(lookback=lookback)
    arr = np.asarray(returns, dtype=float)
    out = await det.detect_market_regime(arr, np.zeros_like(arr), [], datetime.now(timezone.utc))
    try:
        return float(out.get("transfer_entropy"))
    except (TypeError, ValueError):
        return None


def _te_proxy_from_returns(returns: list[float], *, lookback: int) -> float:
    from transfer_entropy_market_regime_detector import compute_transfer_entropy_probe

    import numpy as np

    return compute_transfer_entropy_probe(np.asarray(returns, dtype=float), None, lookback=lookback)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-json", type=Path, default=None, help="Monitor/regime JSON with transfer_entropy")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--scan-candidates", action="store_true", default=True)
    ap.add_argument("--no-scan-candidates", action="store_false", dest="scan_candidates")
    args = ap.parse_args()

    te_val: float | None = None
    method = "absent"
    source_path: str | None = None

    if args.source_json and args.source_json.is_file():
        te_val, method = _extract_from_source(args.source_json)
        source_path = str(args.source_json.resolve())

    if te_val is None and args.scan_candidates:
        for cand in TE_CANDIDATE_PATHS:
            if not cand.is_file():
                continue
            te_val, method = _extract_from_source(cand)
            if te_val is not None:
                source_path = str(cand.resolve())
                break

    if te_val is None and args.btc_csv.is_file():
        rets = _load_btc_returns(args.btc_csv, lookback=int(args.lookback))
        if len(rets) >= 5:
            try:
                te_val = asyncio.run(_run_detector(rets, lookback=int(args.lookback)))
                method = "transfer_entropy_detector_btrack_probe_v1"
                source_path = str(args.btc_csv.resolve())
            except Exception:
                te_val = _te_proxy_from_returns(rets, lookback=int(args.lookback))
                method = "te_proxy_btc_returns_v1"
                source_path = str(args.btc_csv.resolve())

    doc: dict[str, Any] = {
        "schema": "btrack_transfer_entropy_snapshot_v1",
        "version": "1.1.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO] TE snapshot for B-track sandbox — not live gating.",
        "transfer_entropy": te_val,
        "method": method,
        "source_path": source_path,
        "lookback_days": int(args.lookback),
        "fact_safe_note": "Prefer monitoring_latest.json from dump_unified_trading_monitor_te_snapshot_v1.py. "
        "btrack_probe_v1 is offline-safe; not Track A auto-routing.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} method={method} te={te_val}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
