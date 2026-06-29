#!/usr/bin/env python3
"""Merge historical holdout registry into general_prophecy_latest (human sign-off required)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/biblical_history_holdout_production_merge_signoff_v1.json"
DEFAULT_HOLDOUT = ROOT / "tests/fixtures/general_prophecy_registry_historical_holdout_v1.json"
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_REPORT = ROOT / "reports/biblical_history_holdout_production_merge_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _question_ids(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out.add(q["question_id"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge biblical history holdout into production registry.")
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.signoff_json.is_file():
        raise SystemExit(f"missing signoff: {args.signoff_json}")
    signoff = _load(args.signoff_json)
    if not signoff.get("approved"):
        raise SystemExit("signoff approved=false; merge blocked")

    before = _load(args.registry_json)
    before_ids = _question_ids(before)
    holdout = _load(args.holdout_json)
    holdout_ids = _question_ids(holdout)
    new_ids = sorted(holdout_ids - before_ids)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "before_count": len(before_ids),
                    "would_add": new_ids,
                    "after_count": len(before_ids | holdout_ids),
                },
                ensure_ascii=False,
            )
        )
        return 0

    cmd = [
        sys.executable,
        str(ROOT / "scripts/generate_general_prophecy_v1.py"),
        "-i",
        str(args.registry_json),
        "-o",
        str(args.registry_json),
        "--no-default-merge",
        "--merge-from",
        str(args.holdout_json),
    ]
    p = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if p.returncode != 0:
        return int(p.returncode)

    after = _load(args.registry_json)
    after_ids = _question_ids(after)
    added = sorted(after_ids - before_ids)

    report = {
        "schema": "biblical_history_holdout_production_merge_report_v1",
        "generated_at_utc": _utc_now(),
        "signoff_json": str(args.signoff_json),
        "holdout_json": str(args.holdout_json),
        "registry_json": str(args.registry_json),
        "before_question_count": len(before_ids),
        "after_question_count": len(after_ids),
        "questions_added": added,
        "research_rail": "B",
        "gating_status": "NON_GATING",
        "track_a_promotion": False,
        "live_trading_trigger": False,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "added": added, "after_count": len(after_ids)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
