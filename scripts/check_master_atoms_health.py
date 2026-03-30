#!/usr/bin/env python3
"""Health gate for original-language master atoms artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_summary_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Check master atoms summary health thresholds")
    ap.add_argument("--summary", default=str(SUMMARY))
    ap.add_argument("--min-unique-atoms", type=int, default=10000)
    ap.add_argument("--min-hebrew-atoms", type=int, default=5000)
    ap.add_argument("--min-greek-atoms", type=int, default=3000)
    args = ap.parse_args()

    summary_path = _abs(args.summary)
    if not summary_path.is_file():
        print(f"ERROR: missing file: {summary_path}")
        return 2

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    stats = payload.get("stats", {})
    unique_atoms = int(stats.get("unique_master_atoms", 0) or 0)
    by_lang = stats.get("unique_atoms_by_lang", {})
    hebrew_atoms = int(by_lang.get("hebrew", 0) if isinstance(by_lang, dict) else 0)
    greek_atoms = int(by_lang.get("greek", 0) if isinstance(by_lang, dict) else 0)

    failures: list[str] = []
    if unique_atoms < args.min_unique_atoms:
        failures.append(f"unique_master_atoms below min: current={unique_atoms} min={args.min_unique_atoms}")
    if hebrew_atoms < args.min_hebrew_atoms:
        failures.append(f"hebrew atoms below min: current={hebrew_atoms} min={args.min_hebrew_atoms}")
    if greek_atoms < args.min_greek_atoms:
        failures.append(f"greek atoms below min: current={greek_atoms} min={args.min_greek_atoms}")

    print("Master atoms health check")
    print(
        f"- thresholds: unique>={args.min_unique_atoms}, "
        f"hebrew>={args.min_hebrew_atoms}, greek>={args.min_greek_atoms}"
    )
    print(f"- unique_master_atoms: {unique_atoms}")
    print(f"- hebrew_atoms: {hebrew_atoms}")
    print(f"- greek_atoms: {greek_atoms}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
