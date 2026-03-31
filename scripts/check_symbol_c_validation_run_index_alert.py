#!/usr/bin/env python3
"""Fail-fast check for symbol C validation run index alert decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_run_index_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check run index alert decision")
    ap.add_argument("--run-index-json", default=str(DEFAULT_INDEX))
    ap.add_argument("--alert-profile", default="stable")
    args = ap.parse_args()

    index_path = _abs(args.run_index_json)
    if not index_path.is_file():
        print(f"ERROR: missing run index: {index_path}")
        return 2
    idx = _jread(index_path)
    alert_profile = str(args.alert_profile).strip().lower() or "stable"
    if alert_profile == "stable":
        alert = idx.get("alert", {})
    else:
        profiles = idx.get("alert_profiles", {})
        alert = profiles.get(alert_profile, {}) if isinstance(profiles, dict) else {}
    decision = str(alert.get("decision", "hold")).lower()
    failures = alert.get("failures", [])
    print("Symbol C validation run index alert check")
    print(f"- profile: {alert_profile}")
    print(f"- decision: {decision}")
    if decision != "pass":
        print("RESULT: FAIL")
        if isinstance(failures, list):
            for f in failures:
                print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
