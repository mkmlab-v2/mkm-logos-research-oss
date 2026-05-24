#!/usr/bin/env python3
"""Build dry-run cleanup plan from workspace post-it index.

No file move/delete is performed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_INDEX = "docs/final/artifacts/workspace_postit_index_latest.json"
DEFAULT_JSON_OUT = "docs/final/artifacts/workspace_postit_cleanup_plan_latest.json"
DEFAULT_MD_OUT = "docs/final/artifacts/workspace_postit_cleanup_plan_latest.md"


def load_index(path: Path) -> List[Dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("items", [])


def group_by_stem(items: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for item in items:
        rel = str(item.get("path", ""))
        p = Path(rel)
        key = f"{p.parent.as_posix()}::{p.stem}"
        grouped[key].append(item)
    return grouped


def classify_items(
    items: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    safe, caution, blocked = [], [], []
    for it in items:
        path = str(it.get("path", ""))
        status = str(it.get("status", ""))
        typ = str(it.get("type", ""))
        evidence = str(it.get("evidence_level", ""))

        if path.startswith("scripts/") or typ == "automation":
            blocked.append(
                {
                    "path": path,
                    "reason": "execution_path_risk",
                    "suggestion": "do_not_move_without_reference_updates",
                }
            )
            continue
        # Ops anchors referenced by scheduled tasks (TG digest, personadiary mirror).
        if path.endswith("commander_profile_v1.example.json") or "/commander_profile_v1" in path:
            blocked.append(
                {
                    "path": path,
                    "reason": "ops_scheduled_task_anchor",
                    "suggestion": "never_archive_use_p0_verify",
                }
            )
            continue
        if path.startswith("reports/"):
            caution.append(
                {
                    "path": path,
                    "reason": "generated_runtime_artifact",
                    "suggestion": "keep_or_archive_with_regeneration_check",
                }
            )
            continue
        if "freeze/" in path:
            safe.append(
                {
                    "path": path,
                    "reason": "historical_snapshot",
                    "suggestion": "candidate_for_archive_subfolder",
                }
            )
            continue
        if path.startswith("docs/final/artifacts/") and status == "cataloged":
            safe.append(
                {
                    "path": path,
                    "reason": "artifact_cataloged_doc",
                    "suggestion": "candidate_for_thematic_subfolder",
                }
            )
            continue
        if evidence == "A":
            caution.append(
                {
                    "path": path,
                    "reason": "high_evidence_reference",
                    "suggestion": "require_fact_lock_review_before_move",
                }
            )
            continue
        caution.append(
            {
                "path": path,
                "reason": "default_review_required",
                "suggestion": "manual_review",
            }
        )
    return safe, caution, blocked


def find_duplicate_candidates(
    grouped: Dict[str, List[Dict[str, object]]], max_rows: int = 200
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for key, bucket in grouped.items():
        if len(bucket) < 2:
            continue
        latest = [x for x in bucket if str(x.get("status")) == "active_latest"]
        cataloged = [x for x in bucket if str(x.get("status")) == "cataloged"]
        if latest and cataloged:
            rows.append(
                {
                    "group_key": key,
                    "latest_paths": [str(x.get("path")) for x in latest],
                    "cataloged_paths": [str(x.get("path")) for x in cataloged[:10]],
                    "suggestion": "keep_latest_primary_and_archive_older_cataloged",
                }
            )
    rows.sort(key=lambda x: x["group_key"])
    return rows[:max_rows]


def build_summary(
    total: int, safe: List[Dict[str, object]], caution: List[Dict[str, object]], blocked: List[Dict[str, object]], dupes: List[Dict[str, object]]
) -> Dict[str, object]:
    return {
        "total_items_scanned": total,
        "safe_candidates_count": len(safe),
        "caution_candidates_count": len(caution),
        "blocked_candidates_count": len(blocked),
        "duplicate_groups_count": len(dupes),
        "policy": {
            "mode": "dry_run_only",
            "destructive_actions": "none",
            "move_actions": "none",
        },
    }


def write_outputs(payload: Dict[str, object], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    s = payload["summary"]
    lines = [
        "# Workspace Cleanup Plan (Dry Run)",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- total_items_scanned: {s['total_items_scanned']}",
        f"- safe_candidates_count: {s['safe_candidates_count']}",
        f"- caution_candidates_count: {s['caution_candidates_count']}",
        f"- blocked_candidates_count: {s['blocked_candidates_count']}",
        f"- duplicate_groups_count: {s['duplicate_groups_count']}",
        "",
        "## Safe Candidates (top 30)",
    ]
    for row in payload["safe_candidates"][:30]:
        lines.append(f"- `{row['path']}` ({row['reason']})")
    lines.extend(["", "## Caution Candidates (top 30)"])
    for row in payload["caution_candidates"][:30]:
        lines.append(f"- `{row['path']}` ({row['reason']})")
    lines.extend(["", "## Blocked Candidates (top 30)"])
    for row in payload["blocked_candidates"][:30]:
        lines.append(f"- `{row['path']}` ({row['reason']})")
    lines.extend(["", "## Duplicate Groups (top 20)"])
    for row in payload["duplicate_candidates"][:20]:
        lines.append(f"- `{row['group_key']}`")
        for p in row["latest_paths"][:2]:
            lines.append(f"  - latest: `{p}`")
        for p in row["cataloged_paths"][:2]:
            lines.append(f"  - older: `{p}`")
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build workspace cleanup dry-run plan.")
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    items = load_index(Path(args.index))
    safe, caution, blocked = classify_items(items)
    dupes = find_duplicate_candidates(group_by_stem(items))
    payload = {
        "schema": "workspace_postit_cleanup_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": build_summary(len(items), safe, caution, blocked, dupes),
        "safe_candidates": safe,
        "caution_candidates": caution,
        "blocked_candidates": blocked,
        "duplicate_candidates": dupes,
    }
    write_outputs(payload, Path(args.json_out), Path(args.md_out))
    print(f"[ok] cleanup plan json: {args.json_out}")
    print(f"[ok] cleanup plan md: {args.md_out}")
    print(f"[ok] scanned items: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
