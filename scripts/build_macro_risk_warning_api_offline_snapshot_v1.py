#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.8, M:0.4}
# Balance: 88
# Purpose: Build macro risk warning response artifact without running API server.
# Keywords: macro risk, offline snapshot, fact-lock, policy binding

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.macro_risk_warning_api_stub import (
    MacroRiskWarningRequest,
    build_macro_risk_warning_response,
)

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build offline macro risk warning API snapshot.")
    p.add_argument("--asset-scope", default="BTC-USD")
    p.add_argument("--horizon", choices=["1h", "4h", "24h", "7d"], default="24h")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--include-evidence-ref", action="store_true")
    return p.parse_args()


def build_snapshot(asset_scope: str, horizon: str, include_evidence_ref: bool) -> dict:
    req = MacroRiskWarningRequest(
        client_request_id="offline_snapshot",
        asset_scope=asset_scope,
        horizon=horizon,  # type: ignore[arg-type]
        include_evidence_ref=include_evidence_ref,
    )
    return build_macro_risk_warning_response(req).model_dump()


def main() -> int:
    args = parse_args()
    resp = build_snapshot(
        asset_scope=args.asset_scope,
        horizon=args.horizon,
        include_evidence_ref=bool(args.include_evidence_ref),
    )
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"macro_risk_warning_api_offline_snapshot_v1: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
