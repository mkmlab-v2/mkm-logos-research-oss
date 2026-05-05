#!/usr/bin/env python3
"""Check required environment variables for smartfarm OpenAPI live fetch."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


REQUIRED_ENV = [
    "RDA_AGMET_API_BASE_URL",
    "RDA_AGMET_API_ENDPOINT",
    "RDA_AGMET_API_KEY",
]


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check env readiness for fetch_rda_agmet_openapi_v1.py live mode.")
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_openapi_env_check_v1.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    details = []
    missing = []

    for key in REQUIRED_ENV:
        val = os.getenv(key, "").strip()
        ok = bool(val)
        if not ok:
            missing.append(key)
        details.append(
            {
                "key": key,
                "present": ok,
                "masked_value": _mask(val),
            }
        )

    status = "PASS" if not missing else "WARN_OR_FAIL"
    payload = {
        "schema": "smartfarm_openapi_env_check_v1",
        "status": status,
        "required_env": REQUIRED_ENV,
        "missing_env": missing,
        "details": details,
        "next_action": (
            "Set missing env vars and rerun in live mode."
            if missing
            else "Environment ready. You can run run_smartfarm_daily_ingest_and_gate_v1.ps1 -LiveFetch."
        ),
    }

    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] env check -> {out}")
    print(f"[ok] status={status}")
    if missing:
        print(f"[warn] missing: {', '.join(missing)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

