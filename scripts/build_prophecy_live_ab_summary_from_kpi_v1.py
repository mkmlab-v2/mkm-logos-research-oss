# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.86, K:0.58, M:0.67}
# Balance: 88
# Purpose: Build a minimal live A/B summary stub from latest KPI snapshot (no fabricated fills).
# Keywords: prophecy, live, ab, kpi, btc, trading
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("C:/workspace")
DEFAULT_KPI = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi" / "latest_kpi.json"
_PANEL_GATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
_DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_promotion_gates_v1_latest.json"
DEFAULT_GATE = _PANEL_GATE if _PANEL_GATE.is_file() else _DEFAULT_GATE
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_live_ab_summary_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


def _exchange_ready(kpi: dict[str, Any]) -> bool:
    if not kpi.get("exchange_snapshot_24h_available"):
        return False
    fills = kpi.get("exchange_snapshot_24h_fills_count")
    return isinstance(fills, (int, float)) and int(fills) > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kpi-json", type=Path, default=DEFAULT_KPI)
    ap.add_argument("--prophecy-gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    kpi = _load_json(args.kpi_json) if args.kpi_json.exists() else {}
    gate = _load_json(args.prophecy_gate_json) if args.prophecy_gate_json.exists() else {}

    ready = _exchange_ready(kpi)
    status = "READY" if ready else "INSUFFICIENT_DATA"

    out_doc: dict[str, Any] = {
        "schema": "prophecy_live_ab_summary_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "status": status,
        "inputs": {
            "kpi_json": _rel(args.kpi_json) if args.kpi_json.exists() else str(args.kpi_json),
            "prophecy_gate_json": _rel(args.prophecy_gate_json) if args.prophecy_gate_json.exists() else str(args.prophecy_gate_json),
        },
        "environment": {
            "status_symbol": kpi.get("status_symbol"),
            "status_testnet": kpi.get("status_testnet"),
            "status_enable_trading": kpi.get("status_enable_trading"),
        },
        "exchange_snapshot_24h": {
            "available": kpi.get("exchange_snapshot_24h_available"),
            "fills_count": kpi.get("exchange_snapshot_24h_fills_count"),
            "realized_pnl": kpi.get("exchange_snapshot_24h_realized_pnl"),
            "commission": kpi.get("exchange_snapshot_24h_commission"),
            "funding_fee": kpi.get("exchange_snapshot_24h_funding_fee"),
            "net": kpi.get("exchange_snapshot_24h_net"),
        },
        "prophecy_gate_snapshot": {
            "auto_promote_ready": gate.get("auto_promote_ready"),
            "strict_pass_streak": gate.get("strict_pass_streak"),
            "promotion_track_mode": (gate.get("inputs") or {}).get("promotion_track_mode"),
        },
        "arms": {
            "control": {"strategy_id": "TBD_control", "metrics": None},
            "treatment": {"strategy_id": "TBD_treatment", "metrics": None},
        },
        "notes_ko": [
            "본 파일은 KPI 스냅샷에서 A/B에 필요한 24h 체결/손익 필드 존재 여부만 판정한다.",
            "fills/손익이 비어 있으면 live A/B 요약은 INSUFFICIENT_DATA로 유지하고 human sign-off에 수동 첨부한다.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
