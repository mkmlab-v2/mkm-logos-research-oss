# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.85, K:0.5, M:0.65}
# Balance: 85
# Purpose: Sync workspace biblical-lane gate artifacts into bitcoin-trading memory hook for BTC bot.
# Keywords: bitcoin, biblical, hook, gate, BTCUSDT
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "docs" / "final" / "artifacts"
DEFAULT_PROPHECY = ART / "kospi_biblical_prophecy_output_v2_latest.json"
DEFAULT_STATUS = ART / "kospi_biblical_single_lane_stability_status_latest.json"
DEFAULT_OUT = REPO / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "biblical_single_lane_trading_hook_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_hook(
    prophecy: dict[str, Any],
    status: dict[str, Any],
    instrument: str,
) -> dict[str, Any]:
    lt = status.get("live_trading") if isinstance(status.get("live_trading"), dict) else {}
    if not lt and isinstance(prophecy.get("live_trading"), dict):
        lt = prophecy["live_trading"]

    base = prophecy.get("prophecy", {}).get("base_scenario", {}) or {}
    return {
        "schema_version": "biblical_single_lane_trading_hook_v1",
        "generated_at_utc": _now(),
        "instrument": instrument,
        "market": "BTC",
        "note": (
            "Evidence is produced by the workspace biblical single-lane pipeline (KOSPI-indexed); "
            "this hook maps gate state + bias snapshot for the BTC daemon. Not a price forecast."
        ),
        "source_artifacts": {
            "prophecy_v2": str(DEFAULT_PROPHECY.as_posix()),
            "stability_status": str(DEFAULT_STATUS.as_posix()),
        },
        "live_trading": {
            "lane": str(lt.get("lane", "biblical_only")),
            "phase": str(lt.get("phase", "research")),
            "allowed": bool(lt.get("allowed", False)),
            "reasons_if_blocked": list(lt.get("reasons_if_blocked", [])),
            "policy": str(
                lt.get(
                    "policy",
                    "Biblical lane only; broker path separate; use BIBLICAL_SINGLE_LANE_GATE_MODE.",
                )
            ),
        },
        "prophecy_snapshot": {
            "direction_bias": str(base.get("direction_bias", "neutral")),
            "confidence": float(base.get("confidence", 0.0) or 0.0),
            "regime_label": str(base.get("regime_label", "")),
        },
        "operator_brief": prophecy.get("operator_brief", {}),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync biblical lane hook into bitcoin-trading memory")
    ap.add_argument("--prophecy-json", type=Path, default=DEFAULT_PROPHECY)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--instrument",
        default=os.getenv("BIBLICAL_LANE_INSTRUMENT", "BTCUSDT"),
        help="Trading symbol label for the hook (default BTCUSDT or env BIBLICAL_LANE_INSTRUMENT)",
    )
    args = ap.parse_args()

    if not args.prophecy_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing prophecy: {args.prophecy_json}"}, ensure_ascii=False))
        return 2
    if not args.status_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing status: {args.status_json}"}, ensure_ascii=False))
        return 2

    prophecy = _load(args.prophecy_json)
    status = _load(args.status_json)
    hook = build_hook(prophecy, status, str(args.instrument).strip() or "BTCUSDT")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(hook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "allowed": hook["live_trading"]["allowed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
