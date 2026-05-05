#!/usr/bin/env python3
"""Execute safe workspace cleanup moves based on dry-run plan.

Moves only `safe_candidates` with allowed reasons and path filters.
Writes move log for rollback.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Dict, List


DEFAULT_PLAN = "docs/final/artifacts/workspace_postit_cleanup_plan_latest.json"
DEFAULT_LOG = "reports/workspace_postit_cleanup_moves_v1.jsonl"
DEFAULT_TARGET_BASE = "docs/final/artifacts/archive/cataloged"
DEFAULT_P0_VERIFY_SCRIPT = "scripts/verify_p0_constitution_gate_paths.ps1"


def load_plan(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_candidates(plan: Dict[str, object], include_reasons: List[str]) -> List[Dict[str, str]]:
    rows = plan.get("safe_candidates", [])
    out: List[Dict[str, str]] = []
    for r in rows:
        reason = str(r.get("reason", ""))
        if reason in include_reasons:
            out.append(
                {
                    "path": str(r.get("path", "")),
                    "reason": reason,
                }
            )
    return out


def filter_candidates(
    candidates: List[Dict[str, str]],
    include_prefixes: List[str],
    exclude_prefixes: List[str],
) -> List[Dict[str, str]]:
    if not include_prefixes and not exclude_prefixes:
        return candidates
    filtered: List[Dict[str, str]] = []
    for row in candidates:
        p = row["path"]
        if include_prefixes and not any(p.startswith(x) for x in include_prefixes):
            continue
        if exclude_prefixes and any(p.startswith(x) for x in exclude_prefixes):
            continue
        filtered.append(row)
    return filtered


def load_p0_required_prefixes(verify_script_path: Path) -> List[str]:
    """Parse required paths from verify_p0 script and return artifacts prefixes."""
    if not verify_script_path.exists():
        return []
    txt = verify_script_path.read_text(encoding="utf-8")
    # Capture quoted entries inside $required array.
    raw_paths = re.findall(r'"([^"]+)"', txt)
    out: List[str] = []
    for p in raw_paths:
        norm = p.replace("\\", "/")
        # We only use artifact paths as hard exclusion prefixes.
        if norm.startswith("docs/final/artifacts/"):
            out.append(norm)
    # Sort longest first for stable matching.
    return sorted(set(out), key=len, reverse=True)


def move_candidates(
    root: Path,
    candidates: List[Dict[str, str]],
    target_base: Path,
    log_path: Path,
    apply: bool,
    limit: int,
) -> Dict[str, object]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_dir = target_base / ts
    moved = 0
    skipped_missing = 0
    skipped_conflict = 0
    preview: List[Dict[str, str]] = []

    if apply:
        session_dir.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    for row in candidates[:limit if limit > 0 else len(candidates)]:
        rel = row["path"]
        src = root / rel
        dst = session_dir / rel
        if not src.exists():
            skipped_missing += 1
            continue
        if dst.exists():
            skipped_conflict += 1
            continue
        preview.append({"from": rel, "to": str(dst.relative_to(root).as_posix())})
        if not apply:
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        moved += 1
        log_row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "action": "move_safe_candidate",
            "reason": row["reason"],
            "from": rel,
            "to": str(dst.relative_to(root).as_posix()),
            "session_dir": str(session_dir.relative_to(root).as_posix()),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    return {
        "apply": apply,
        "session_dir": str(session_dir.relative_to(root).as_posix()),
        "selected_candidates": len(candidates[: limit if limit > 0 else len(candidates)]),
        "moved_count": moved,
        "skipped_missing_count": skipped_missing,
        "skipped_conflict_count": skipped_conflict,
        "preview": preview[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute safe post-it cleanup moves.")
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--target-base", default=DEFAULT_TARGET_BASE)
    parser.add_argument("--log-path", default=DEFAULT_LOG)
    parser.add_argument(
        "--include-reasons",
        nargs="+",
        default=["artifact_cataloged_doc", "historical_snapshot"],
    )
    parser.add_argument(
        "--include-prefixes",
        nargs="+",
        default=[],
        help="Only move files whose path starts with these prefixes",
    )
    parser.add_argument(
        "--exclude-prefixes",
        nargs="+",
        default=[
            "docs/final/artifacts/archive/",
            "docs/final/artifacts/schemas/",
            "docs/final/artifacts/bio_",
            "docs/final/artifacts/B_TRACK_",
            "docs/final/artifacts/ATHENA_",
            "docs/final/artifacts/MULTILENS_",
            "docs/final/artifacts/LOGOS_",
            "docs/final/artifacts/SASANG_",
            "docs/final/artifacts/MANSE_",
            "docs/final/artifacts/MKM_TRINITY_INDEX",
            "docs/final/artifacts/mkm_mcp_tool_audit_v1.json",
            "docs/final/artifacts/MKM_MCP_STDIO_POINTER_V1.json",
            "docs/final/artifacts/trackb_quaternion_",
            "docs/final/artifacts/workspace_postit_",
            "docs/final/artifacts/MKM_",
            "docs/final/artifacts/MARKET_",
        ],
        help="Skip files whose path starts with these prefixes",
    )
    parser.add_argument(
        "--p0-verify-script",
        default=DEFAULT_P0_VERIFY_SCRIPT,
        help="verify_p0 script path used to auto-protect required artifacts",
    )
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--apply", action="store_true", help="Perform real moves")
    parser.add_argument(
        "--summary-out",
        default="docs/final/artifacts/workspace_postit_cleanup_apply_summary_latest.json",
    )
    args = parser.parse_args()

    root = Path(".").resolve()
    plan = load_plan(root / args.plan)
    candidates = pick_candidates(plan, args.include_reasons)
    auto_p0_excludes = load_p0_required_prefixes(root / args.p0_verify_script)
    merged_excludes = sorted(set(args.exclude_prefixes + auto_p0_excludes))
    candidates = filter_candidates(
        candidates=candidates,
        include_prefixes=args.include_prefixes,
        exclude_prefixes=merged_excludes,
    )
    result = move_candidates(
        root=root,
        candidates=candidates,
        target_base=root / args.target_base,
        log_path=root / args.log_path,
        apply=args.apply,
        limit=args.limit,
    )
    payload = {
        "schema": "workspace_postit_cleanup_apply_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_path": args.plan,
        "target_base": args.target_base,
        "log_path": args.log_path,
        "include_reasons": args.include_reasons,
        "auto_p0_excludes_count": len(auto_p0_excludes),
        **result,
    }
    summary_path = root / args.summary_out
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] summary: {args.summary_out}")
    print(f"[ok] selected_candidates: {payload['selected_candidates']}")
    print(f"[ok] moved_count: {payload['moved_count']}")
    print(f"[ok] session_dir: {payload['session_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
