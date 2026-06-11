#!/usr/bin/env python3
"""Human-gated apply for contributor prophecy → signoff envelope (does not auto-write general_prophecy_latest)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "docs/final/artifacts/prophecy_contributor_promotion_candidate_v1_latest.json"
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/prophecy_contributor_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--human-approve-promotion", action="store_true")
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.human_approve_promotion:
        print("error: --human-approve-promotion required", file=sys.stderr)
        return 2

    cand_path = args.candidate_json.resolve()
    if not cand_path.is_file():
        print(f"error: missing candidate: {cand_path}", file=sys.stderr)
        return 2

    cand = _load(cand_path)
    if not cand.get("commander_may_apply_registry_bridge"):
        print(
            json.dumps(
                {
                    "denied": True,
                    "reason": "promotion_gates_not_met",
                    "gates": cand.get("promotion_gates"),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    signoff: dict[str, Any] = {
        "schema": "prophecy_contributor_signoff_v1",
        "generated_at_utc": _utc(),
        "lane": "contributor_provided",
        "track": "btrack_research_only",
        "reviewer": args.reviewer,
        "human_approve_promotion": True,
        "note": args.note,
        "candidate_ref": _rel(cand_path),
        "inputs": cand.get("inputs"),
        "metrics": cand.get("metrics"),
        "auto_registry_merge_performed": False,
        "boundary_ack": (
            "Signoff records commander approval for contributor sandbox evidence only. "
            "Merge new question_ids into general_prophecy_latest requires separate human edit or patch workflow."
        ),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_write": _rel(args.signoff_json)}, ensure_ascii=False))
        return 0

    out = args.signoff_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "signoff": _rel(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
