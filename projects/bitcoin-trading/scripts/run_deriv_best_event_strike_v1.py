#!/usr/bin/env python3
"""
run_deriv_best_event_strike_v1

백테스트 최우수 이벤트 기준으로 현재 신호를 판정하고,
신호가 참일 때만 one-shot 주문 스크립트를 호출한다.

기본값은 dry-run (주문 없음). --live 시에만 주문 제출.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _workspace_root() -> Path:
    here = Path(__file__).resolve()
    if (
        here.parent.name == "scripts"
        and here.parent.parent.name == "bitcoin-trading"
        and here.parents[2].name == "projects"
    ):
        return here.parents[3]
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _f(x: Any) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_panel_row(rows_path: Path) -> Dict[str, Any]:
    lines = [ln for ln in rows_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"no rows in {rows_path}")
    return json.loads(lines[-1])


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    ws = _workspace_root()
    scripts = ws / "projects" / "bitcoin-trading" / "scripts"
    reports = ws / "reports"

    ap = argparse.ArgumentParser(description="Strike only when best deriv event condition is true.")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--qty", type=float, default=0.001)
    ap.add_argument("--leverage", type=int, default=2)
    ap.add_argument("--backtest-report", type=Path, default=reports / "deriv_factor_backtest_30d_v1.json")
    ap.add_argument("--panel-rows", type=Path, default=reports / "deriv_factor_panel_rows_v1.jsonl")
    ap.add_argument("--mainnet", action="store_true", help="forwarded to order script")
    ap.add_argument("--live", action="store_true", help="actually place order when signal is true")
    ap.add_argument("--allow-no-signal", action="store_true", help="allow order even if signal is false")
    ap.add_argument("--out-json", type=Path, default=reports / "deriv_best_event_strike_latest.json")
    args = ap.parse_args()

    bt = _read_json(args.backtest_report)
    thresholds = (((bt.get("result") or {}).get("thresholds")) or {})
    q90_f = _f(thresholds.get("funding_q90"))

    # refresh snapshot for current state
    build_cmd = [
        sys.executable,
        str(scripts / "build_deriv_factor_panel_v1.py"),
        "--symbol",
        args.symbol,
        "--samples",
        "1",
        "--out-dir",
        str(reports),
    ]
    b = _run(build_cmd)
    if b.returncode != 0:
        raise RuntimeError(f"panel refresh failed: {b.stderr or b.stdout}")

    row = _latest_panel_row(args.panel_rows)
    funding_now = _f(row.get("last_funding_rate"))
    signal = bool(q90_f is not None and funding_now is not None and funding_now >= q90_f)

    decision = {
        "schema": "deriv_best_event_strike_v1",
        "symbol": args.symbol,
        "best_event": "funding_high",
        "best_event_horizon_bars": 12,
        "threshold_funding_q90": q90_f,
        "funding_now": funding_now,
        "signal": signal,
        "live": bool(args.live),
        "mainnet": bool(args.mainnet),
        "qty": args.qty,
        "leverage": args.leverage,
        "order_attempted": False,
        "order_rc": None,
        "order_stdout": None,
        "order_stderr": None,
    }

    should_order = signal or args.allow_no_signal
    if should_order:
        side = "BUY"  # funding_high strategy baseline in current backtest
        order_cmd = [
            sys.executable,
            str(scripts / "execute_binance_usdm_single_order_v1.py"),
            "--symbol",
            args.symbol,
            "--side",
            side,
            "--qty",
            str(args.qty),
            "--leverage",
            str(args.leverage),
        ]
        if args.live:
            order_cmd.append("--live")
        if args.mainnet:
            order_cmd.append("--mainnet")
        p = _run(order_cmd)
        decision["order_attempted"] = True
        decision["order_rc"] = p.returncode
        decision["order_stdout"] = (p.stdout or "")[:2000]
        decision["order_stderr"] = (p.stderr or "")[:2000]

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "signal": signal, "order_attempted": decision["order_attempted"], "out_json": str(args.out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
