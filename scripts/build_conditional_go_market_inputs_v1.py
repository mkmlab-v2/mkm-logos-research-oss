#!/usr/bin/env python3
"""Build conditional_go_market_inputs_latest.json from lightweight market signals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "conditional_go_market_inputs_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y"}:
            return True
        if v in {"0", "false", "no", "n"}:
            return False
    return default


def _fetch_from_yfinance() -> tuple[bool | None, bool | None]:
    try:
        import yfinance as yf
    except Exception:
        return None, None

    try:
        ks = yf.Ticker("^KS11").history(period="10d", interval="1d", auto_adjust=True).dropna()
        if len(ks) < 2:
            return None, None
        prev_low = float(ks["Low"].iloc[-2])
        close = float(ks["Close"].iloc[-1])
        kospi_structure_hold = close >= prev_low
    except Exception:
        kospi_structure_hold = None

    semi_leader_recovery: bool | None = None
    try:
        leader_ok: list[bool] = []
        for ticker in ("005930.KS", "000660.KS"):
            df = yf.Ticker(ticker).history(period="10d", interval="1d", auto_adjust=True).dropna()
            if len(df) < 2:
                continue
            close_last = float(df["Close"].iloc[-1])
            open_last = float(df["Open"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            leader_ok.append(close_last >= open_last and close_last >= close_prev)
        if leader_ok:
            semi_leader_recovery = any(leader_ok)
    except Exception:
        semi_leader_recovery = None

    return kospi_structure_hold, semi_leader_recovery


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-json", type=Path, default=None, help="Optional fixed input payload for deterministic runs/tests.")
    ap.add_argument("--foreign-flow-turn", default="", help="Optional override true/false.")
    ap.add_argument("--confidence", type=float, default=-1.0, help="Optional override in [0,1].")
    args = ap.parse_args()

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    current = _read_json_optional(out_path)
    current_checks = current.get("checks") if isinstance(current.get("checks"), dict) else {}

    foreign_flow_turn = _to_bool(current_checks.get("foreign_flow_turn"), False)
    if str(args.foreign_flow_turn).strip():
        foreign_flow_turn = _to_bool(args.foreign_flow_turn, foreign_flow_turn)

    kospi_structure_hold = _to_bool(current_checks.get("kospi_structure_hold"), False)
    semi_leader_recovery = _to_bool(current_checks.get("semi_leader_recovery"), False)

    yfinance_ok = False
    if args.sample_json is not None:
        sample_path = args.sample_json if args.sample_json.is_absolute() else ROOT / args.sample_json
        sample = _read_json_optional(sample_path)
        checks = sample.get("checks") if isinstance(sample.get("checks"), dict) else {}
        kospi_structure_hold = _to_bool(checks.get("kospi_structure_hold"), kospi_structure_hold)
        semi_leader_recovery = _to_bool(checks.get("semi_leader_recovery"), semi_leader_recovery)
        yfinance_ok = bool(sample.get("yfinance_ok") is True)
    else:
        ks_hold, semi_recover = _fetch_from_yfinance()
        if ks_hold is not None:
            kospi_structure_hold = ks_hold
            yfinance_ok = True
        if semi_recover is not None:
            semi_leader_recovery = semi_recover
            yfinance_ok = True

    checks_true = sum([foreign_flow_turn, kospi_structure_hold, semi_leader_recovery])
    inferred_conf = [0.2, 0.45, 0.62, 0.8][checks_true]
    confidence = inferred_conf if args.confidence < 0 else max(0.0, min(1.0, float(args.confidence)))

    payload = {
        "schema": "conditional_go_market_inputs_v1",
        "generated_at_utc": _now(),
        "source_note": "Auto refreshed from market signals; foreign flow may remain manual override.",
        "checks": {
            "foreign_flow_turn": bool(foreign_flow_turn),
            "kospi_structure_hold": bool(kospi_structure_hold),
            "semi_leader_recovery": bool(semi_leader_recovery),
        },
        "confidence_0_1": round(confidence, 6),
        "diagnostics": {
            "yfinance_ok": yfinance_ok,
            "checks_true_count": checks_true,
            "confidence_mode": "override" if args.confidence >= 0 else "inferred",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "checks_true": checks_true, "yfinance_ok": yfinance_ok}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
