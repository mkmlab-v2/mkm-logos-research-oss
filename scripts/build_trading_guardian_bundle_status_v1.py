#!/usr/bin/env python3
"""Build single-file trading guardian bundle status."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build trading guardian bundle status.")
    ap.add_argument("--workspace-root", default=".")
    ap.add_argument(
        "--output-json",
        default="reports/trading_guardian_bundle_status_latest.json",
    )
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    health = _read_json(root / "reports" / "trading_automation_health_latest.json")
    coverage = _read_json(
        root / "reports" / "binance_usdm_single_order" / "protective_order_coverage_latest.json"
    )

    health_ok = bool(health.get("overall_ok", False))
    coverage_ok = bool(coverage.get("ok", False))
    status = "GREEN" if (health_ok and coverage_ok) else "DEGRADED"

    bundle: dict[str, Any] = {
        "schema": "trading_guardian_bundle_status_v1",
        "generated_at_utc": _now_iso(),
        "status": status,
        "ok": status == "GREEN",
        "components": {
            "trading_automation_health": {
                "ok": health_ok,
                "overall_ok": health.get("overall_ok"),
                "security_ok": health.get("security_ok"),
                "go_no_go_ok": health.get("go_no_go_ok"),
                "go_no_go": health.get("go_no_go"),
                "generated_at_utc": health.get("generated_at_utc"),
            },
            "protective_coverage": {
                "ok": coverage_ok,
                "status": coverage.get("status"),
                "symbol": coverage.get("symbol"),
                "position": coverage.get("position"),
                "generated_at_utc": coverage.get("generated_at_utc"),
            },
        },
    }

    out = root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"trading_guardian_bundle_status_written={out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
