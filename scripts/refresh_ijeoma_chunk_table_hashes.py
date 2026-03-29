#!/usr/bin/env python3
"""
Recompute char_len, sha256, preview_80chars for each IJEOMA chunk row from current canonical TXT.

Join rule matches verify_ijeoma_chunk_table.py:
  reconstructed = "".join(lines[line_start - 1 : line_end])
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_manifest(manifest_path: Path) -> dict:
    with manifest_path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    root = repo_root()
    default_manifest = root / "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json"
    default_chunk = root / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"

    ap = argparse.ArgumentParser(
        description="Refresh chunk table JSONL hashes from canonical (same line ranges)"
    )
    ap.add_argument("--manifest", type=Path, default=default_manifest)
    ap.add_argument("--chunk-table", type=Path, default=None)
    ap.add_argument("--canonical", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Print stats only, do not write")
    args = ap.parse_args()

    manifest: dict | None = None
    if args.manifest.is_file():
        manifest = load_manifest(args.manifest)
    else:
        print(f"WARN: manifest not found: {args.manifest}", file=sys.stderr)

    chunk_table = args.chunk_table or (
        root / manifest["chunk_table"]["path_workspace"].replace("\\", "/")
        if manifest
        else default_chunk
    )
    canonical = args.canonical or (
        root / manifest["canonical_source"]["path_workspace"].replace("\\", "/")
        if manifest
        else root / "docs/sasang-origin/정교동의수세보원원문.txt"
    )

    if not canonical.is_file():
        print(f"ERROR: canonical missing: {canonical}", file=sys.stderr)
        return 2
    if not chunk_table.is_file():
        print(f"ERROR: chunk table missing: {chunk_table}", file=sys.stderr)
        return 2

    text = canonical.read_bytes().decode("utf-8")
    lines = text.splitlines()

    out_rows: list[dict] = []
    updated = 0
    with chunk_table.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ls = int(row["line_start"])
            le = int(row["line_end"])
            if ls < 1 or le < ls:
                print(f"ERROR: invalid bounds {row.get('chunk_id')} {ls}-{le}", file=sys.stderr)
                return 1
            start_i = ls - 1
            end_i = le
            if end_i > len(lines) or start_i >= len(lines):
                print(
                    f"ERROR: chunk {row.get('chunk_id')} out of range lines={len(lines)}",
                    file=sys.stderr,
                )
                return 1
            chunk_lines = lines[start_i:end_i]
            reconstructed = "".join(chunk_lines)
            new_len = len(reconstructed)
            new_sha = hashlib.sha256(reconstructed.encode("utf-8")).hexdigest()
            new_preview = reconstructed[:80]
            old_len = int(row.get("char_len", -1))
            old_sha = (row.get("sha256") or "").strip().lower()
            if new_len != old_len or new_sha != old_sha:
                updated += 1
            row["char_len"] = new_len
            row["sha256"] = new_sha
            row["preview_80chars"] = new_preview
            out_rows.append(row)

    if args.dry_run:
        print(f"rows={len(out_rows)} would_update={updated} dry_run")
        return 0

    tmp = chunk_table.with_suffix(chunk_table.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as w:
        for row in out_rows:
            w.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(chunk_table)
    print(f"OK: wrote {chunk_table} rows={len(out_rows)} rows_updated_metadata={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
