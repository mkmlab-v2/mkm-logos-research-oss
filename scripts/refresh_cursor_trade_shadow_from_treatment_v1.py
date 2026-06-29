#!/usr/bin/env python3
"""Refresh trades_treatment_v2_shadow.json from trades_treatment.json (live export SSOT).

research_only — aligns shadow timeline with Binance fills export; does not imply
Track A / live promotion. Preserves existing bootstrap rows when dedupe keys match.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history"
DEFAULT_TREATMENT = DEFAULT_DIR / "trades_treatment.json"
DEFAULT_SHADOW = DEFAULT_DIR / "trades_treatment_v2_shadow.json"
DEFAULT_META = DEFAULT_DIR / "trades_shadow_sync_meta_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_array(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _ts_iso(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        sec = float(raw) / 1000.0 if float(raw) > 1_000_000_000_000 else float(raw)
        try:
            return datetime.fromtimestamp(sec, tz=timezone.utc).isoformat()
        except (OSError, ValueError):
            return None
    if isinstance(raw, str) and raw.strip():
        value = raw.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(value)
            return dt.isoformat() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None
    return None


def _dedupe_key(row: dict[str, Any]) -> str:
    for key in ("exchange_trade_id", "trade_id", "id"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return f"{key}:{val}"
    ts = _ts_iso(row.get("timestamp") or row.get("time"))
    side = row.get("side")
    price = row.get("price")
    qty = row.get("qty") or row.get("amount")
    return f"fallback:{ts}:{side}:{price}:{qty}"


def _treatment_to_shadow(row: dict[str, Any]) -> dict[str, Any]:
    realized = float(row.get("realized_pnl") or 0)
    commission = float(row.get("commission") or 0)
    net_pnl = realized - commission
    ts = _ts_iso(row.get("timestamp") or row.get("time"))
    trade_id = row.get("trade_id") or row.get("id")
    order_id = row.get("order_id")
    return {
        "symbol": row.get("symbol") or "BTCUSDT",
        "side": str(row.get("side") or "").upper(),
        "qty": float(row.get("amount") or row.get("qty") or 0),
        "price": float(row.get("price") or 0),
        "realized_pnl": realized,
        "commission": commission,
        "net_pnl": net_pnl,
        "pnl_usdt": net_pnl,
        "is_win": net_pnl > 0,
        "status": "closed",
        "closed": True,
        "timestamp": ts,
        "signal_source": "treatment_live_export_sync",
        "runtime_strategy_id": "treatment_v2_shadow_live_sync",
        "exchange_trade_id": trade_id,
        "exchange_order_id": order_id,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--treatment-file", type=Path, default=DEFAULT_TREATMENT)
    ap.add_argument("--shadow-file", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    ap.add_argument(
        "--drop-bootstrap",
        action="store_true",
        help="Do not preserve prior exchange_fill_backfill bootstrap rows.",
    )
    args = ap.parse_args()

    if not args.treatment_file.is_file():
        print(f"missing treatment file: {args.treatment_file}", file=sys.stderr)
        return 1

    treatment = _load_array(args.treatment_file)
    existing = _load_array(args.shadow_file) if not args.drop_bootstrap else []

    merged: dict[str, dict[str, Any]] = {}
    bootstrap_kept = 0
    for row in existing:
        key = _dedupe_key(row)
        if row.get("signal_source") == "exchange_fill_backfill":
            merged[key] = row
            bootstrap_kept += 1
        else:
            merged[key] = row

    converted = 0
    for row in treatment:
        shadow_row = _treatment_to_shadow(row)
        if not shadow_row.get("timestamp"):
            continue
        merged[_dedupe_key(shadow_row)] = shadow_row
        converted += 1

    out_rows = sorted(
        merged.values(),
        key=lambda r: (_ts_iso(r.get("timestamp")) or "", str(r.get("exchange_trade_id") or "")),
    )

    args.shadow_file.parent.mkdir(parents=True, exist_ok=True)
    args.shadow_file.write_text(
        json.dumps(out_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    dates = sorted(
        {
            _ts_iso(r.get("timestamp"))[:10]
            for r in out_rows
            if _ts_iso(r.get("timestamp"))
        }
    )
    meta = {
        "schema": "trades_shadow_sync_meta_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "treatment_file": str(args.treatment_file),
        "shadow_file": str(args.shadow_file),
        "row_count": len(out_rows),
        "converted_from_treatment": converted,
        "bootstrap_rows_kept": bootstrap_kept,
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "distinct_days": len(dates),
    }
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(args.shadow_file),
                "rows": len(out_rows),
                "distinct_days": len(dates),
                "date_min": dates[0] if dates else None,
                "date_max": dates[-1] if dates else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
