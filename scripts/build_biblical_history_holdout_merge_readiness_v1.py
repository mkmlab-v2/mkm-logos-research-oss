#!/usr/bin/env python3
"""Summarize holdout merge dry-run + signoff + H-DSS1 anchor readiness (B-track)."""

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
DEFAULT_OUT = ROOT / "reports/biblical_history_holdout_merge_readiness_latest.json"
H_DSS1_HOLDOUT = "hist.arch.dead_sea_scrolls_cave1_1947"


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-merge", action="store_true", help="Execute merge when signoff approved.")
    args = ap.parse_args()

    signoff = _load(args.signoff_json) if args.signoff_json.is_file() else {}
    registry = _load(args.registry_json) if args.registry_json.is_file() else {"questions": []}
    before_ids = _question_ids(registry)

    dry = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/merge_biblical_history_holdout_to_general_prophecy_v1.py"),
            "--dry-run",
            "--signoff-json",
            str(args.signoff_json),
            "--holdout-json",
            str(args.holdout_json),
            "--registry-json",
            str(args.registry_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    dry_doc: dict[str, Any] = {}
    if dry.returncode == 0 and dry.stdout.strip():
        dry_doc = json.loads(dry.stdout.strip().splitlines()[-1])

    merge_ok = False
    merge_added: list[str] = []
    if args.run_merge and signoff.get("approved"):
        merge = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/merge_biblical_history_holdout_to_general_prophecy_v1.py"),
                "--signoff-json",
                str(args.signoff_json),
                "--holdout-json",
                str(args.holdout_json),
                "--registry-json",
                str(args.registry_json),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        merge_ok = merge.returncode == 0
        if merge.stdout.strip():
            try:
                merge_doc = json.loads(merge.stdout.strip().splitlines()[-1])
                merge_added = list(merge_doc.get("added") or [])
            except json.JSONDecodeError:
                pass

    after_registry = _load(args.registry_json) if args.registry_json.is_file() else registry
    after_ids = _question_ids(after_registry)

    payload = {
        "schema": "biblical_history_holdout_merge_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "signoff": {
            "path": str(args.signoff_json),
            "approved": bool(signoff.get("approved")),
            "expected_questions_added": signoff.get("expected_questions_added"),
        },
        "dry_run": dry_doc,
        "h_dss1_holdout_anchor": {
            "question_id": H_DSS1_HOLDOUT,
            "in_registry_before": H_DSS1_HOLDOUT in before_ids,
            "in_registry_after": H_DSS1_HOLDOUT in after_ids,
            "in_would_add": H_DSS1_HOLDOUT in list(dry_doc.get("would_add") or []),
        },
        "merge_executed": args.run_merge and bool(signoff.get("approved")),
        "merge_ok": merge_ok,
        "questions_added": merge_added,
        "registry_question_count_after": len(after_ids),
        "next_human_action": (
            "none_if_merge_ok"
            if merge_ok
            else ("run_with_--run-merge" if signoff.get("approved") else "set signoff approved=true after review")
        ),
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "merge_ok": merge_ok}, ensure_ascii=False))
    return 0 if (not args.run_merge or merge_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
