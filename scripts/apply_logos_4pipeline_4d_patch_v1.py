#!/usr/bin/env python3
"""Apply logos_4pipeline_4d_fallback_patch JSONL to a copy of verse_4pipeline_full (B-track).

Default: --dry-run (counts only). Use --write --out-json to emit patched array (large).
Does not modify data/logos/verse_4pipeline_full_31102.json (writes --out-json only).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
PATCH = ROOT / "reports/logos_4pipeline_4d_fallback_patch_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/logos_verse_4pipeline_patched_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_patch(path: Path) -> dict[str, dict]:
    m: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            after = row.get("pipeline4_vector_4d_after")
            if vid and isinstance(after, dict):
                m[vid] = after
    return m


def apply(
    *,
    full_path: Path,
    patch_path: Path,
    write: bool,
    out_path: Path,
) -> dict:
    pmap = _load_patch(patch_path)
    rows = json.loads(full_path.read_text(encoding="utf-8-sig"))
    applied = 0
    missing_vid = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "")
        if vid not in pmap:
            continue
        p4 = row.get("pipeline4_unified_v2")
        if not isinstance(p4, dict):
            p4 = {}
            row["pipeline4_unified_v2"] = p4
        p4["vector_4d"] = pmap[vid]
        applied += 1
    for vid in pmap:
        if vid not in {str(r.get("verse_id") or "") for r in rows if isinstance(r, dict)}:
            missing_vid += 1
    meta = {
        "generated_at_utc": _utc(),
        "dry_run": not write,
        "patch_rows": len(pmap),
        "applied": applied,
        "missing_verse_id_in_full": missing_vid,
        "full_path": str(full_path),
        "out_path": str(out_path if write else "(none)"),
    }
    if write:
        target = out_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-json", type=Path, default=FULL)
    ap.add_argument("--patch-jsonl", type=Path, default=PATCH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = ap.parse_args()
    write = args.write and not args.dry_run
    if not args.full_json.is_file() or not args.patch_jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing inputs"}))
        return 2
    meta = apply(
        full_path=args.full_json,
        patch_path=args.patch_jsonl,
        write=write,
        out_path=args.out_json,
    )
    print(json.dumps({"ok": True, **meta}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
