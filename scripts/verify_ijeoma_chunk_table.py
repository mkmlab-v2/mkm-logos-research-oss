#!/usr/bin/env python3
"""
Verify IJEOMA chunk table JSONL against merged canonical UTF-8 text.

Join rule (1-based line numbers): reconstructed = "".join(lines[line_start - 1 : line_end])
No newlines between joined lines — matches IJEOMA chunking spec.
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


def verify(
    canonical: Path,
    chunk_table: Path,
    manifest: dict | None,
    max_failures: int,
) -> int:
    if not canonical.is_file():
        print(f"ERROR: canonical file missing: {canonical}", file=sys.stderr)
        print("Place merged TXT at manifest canonical_source.path_workspace or pass --canonical.", file=sys.stderr)
        return 2

    raw = canonical.read_bytes()
    if manifest:
        exp = manifest.get("canonical_source", {}).get("byte_length")
        if exp is not None and len(raw) != exp:
            print(
                f"WARN: file byte_length {len(raw)} != manifest canonical_source.byte_length {exp}"
            )

    text = raw.decode("utf-8")
    lines = text.splitlines()

    mismatches: list[dict] = []
    row_num = 0

    with chunk_table.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row_num += 1
            row = json.loads(line)
            chunk_id = row["chunk_id"]
            ls = int(row["line_start"])
            le = int(row["line_end"])
            exp_len = int(row["char_len"])
            exp_sha = row["sha256"].strip().lower()

            if ls < 1 or le < ls:
                mismatches.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": f"invalid bounds line_start={ls} line_end={le}",
                    }
                )
            else:
                start_i = ls - 1
                end_i = le  # exclusive slice end = inclusive 1-based line_end
                if end_i > len(lines):
                    mismatches.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": f"line_end {le} past EOF (lines={len(lines)})",
                        }
                    )
                elif start_i >= len(lines):
                    mismatches.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": f"line_start {ls} past EOF (lines={len(lines)})",
                        }
                    )
                else:
                    chunk_lines = lines[start_i:end_i]
                    reconstructed = "".join(chunk_lines)
                    got_len = len(reconstructed)
                    got_sha = hashlib.sha256(reconstructed.encode("utf-8")).hexdigest()

                    if got_len != exp_len or got_sha != exp_sha:
                        mismatches.append(
                            {
                                "chunk_id": chunk_id,
                                "line_start": ls,
                                "line_end": le,
                                "expected_len": exp_len,
                                "got_len": got_len,
                                "expected_sha256": exp_sha,
                                "got_sha256": got_sha,
                            }
                        )

            if len(mismatches) >= max_failures:
                break

    print(f"Rows scanned: {row_num}")
    print(f"Canonical lines: {len(lines)}")
    if manifest:
        est = manifest.get("canonical_source", {}).get("line_count_estimate")
        if est is not None and len(lines) != est:
            print(f"WARN: line count {len(lines)} != manifest line_count_estimate {est}")

    if not mismatches:
        print("OK: all scanned chunks match char_len and sha256.")
        return 0

    print(f"FAIL: {len(mismatches)} mismatch(es) (showing up to {max_failures}):")
    for m in mismatches:
        print(json.dumps(m, ensure_ascii=False))
    return 1


def main() -> int:
    root = repo_root()
    default_manifest = root / "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json"
    default_chunk = root / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"

    ap = argparse.ArgumentParser(description="Verify IJEOMA chunk table against canonical TXT")
    ap.add_argument("--manifest", type=Path, default=default_manifest, help="Manifest JSON path")
    ap.add_argument("--chunk-table", type=Path, default=None, help="Override chunk JSONL path")
    ap.add_argument("--canonical", type=Path, default=None, help="Override canonical TXT path")
    ap.add_argument("--max-failures", type=int, default=50, help="Stop after N mismatches")
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

    if not chunk_table.is_file():
        print(f"ERROR: chunk table missing: {chunk_table}", file=sys.stderr)
        return 2

    return verify(canonical, chunk_table, manifest, args.max_failures)


if __name__ == "__main__":
    sys.exit(main())
