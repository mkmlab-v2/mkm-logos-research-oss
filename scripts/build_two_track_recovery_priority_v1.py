#!/usr/bin/env python3
"""Build prioritized recovery plan from two-track prereq check output."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def parse_args() -> argparse.Namespace:
    repo_root_default = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Build top-N recovery priorities for two-track chain.")
    p.add_argument("--repo-root", type=Path, default=repo_root_default)
    p.add_argument(
        "--prereq-check-json",
        type=Path,
        default=Path("docs/final/artifacts/two_track_submission_prereq_check_latest.json"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/two_track_recovery_priority_latest.json"),
    )
    p.add_argument("--top-n", type=int, default=10)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    prereq_path = args.prereq_check_json if args.prereq_check_json.is_absolute() else (repo_root / args.prereq_check_json)
    out_path = args.out if args.out.is_absolute() else (repo_root / args.out)
    if not prereq_path.is_file():
        raise SystemExit(f"missing prereq check json: {prereq_path}")

    doc = _load(prereq_path)
    missing_refs = ((doc.get("chain_scan") or {}).get("missing_python_refs") or [])
    ordered_missing = [x for x in missing_refs if isinstance(x, dict) and isinstance(x.get("script"), str)]
    top_n = max(1, int(args.top_n))
    top = ordered_missing[:top_n]

    items: list[dict[str, Any]] = []
    for idx, row in enumerate(top, start=1):
        script = str(row.get("script", ""))
        items.append(
            {
                "priority_rank": idx,
                "script": script,
                "reason": "earlier chain dependency blocks downstream stages",
                "recommended_action": "restore from known-good snapshot/branch before rebuilding outputs",
            }
        )

    missing_required = ((doc.get("gates") or {}).get("missing_required_artifacts") or [])
    result = {
        "schema": "two_track_recovery_priority_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "source": {"prereq_check_json": str(prereq_path)},
        "summary": {
            "missing_python_refs_count": len(ordered_missing),
            "missing_required_artifacts_count": len(missing_required),
            "top_n": top_n,
        },
        "top_priority_scripts": items,
        "missing_required_artifacts": missing_required,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

