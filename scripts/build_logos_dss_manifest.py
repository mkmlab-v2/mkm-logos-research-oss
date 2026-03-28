#!/usr/bin/env python3
"""
Emit data/logos/manuscripts/LOGOS_DSS_MANIFEST.json with row counts and file SHA-256.

  py scripts/build_logos_dss_manifest.py

Requires manuscript JSONL to exist; hashes are of the UTF-8 file bytes on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = repo_root()
    out_default = root / "data/logos/manuscripts/LOGOS_DSS_MANIFEST.json"
    default_inputs = [
        root / "data/logos/manuscripts/dss_parsed.jsonl",
        root / "data/logos/manuscripts/apocrypha_std.jsonl",
    ]

    ap = argparse.ArgumentParser(description="Build LOGOS_DSS_MANIFEST.json")
    ap.add_argument("--out", type=Path, default=out_default, help="Output manifest path")
    ap.add_argument(
        "--jsonl",
        type=Path,
        nargs="*",
        default=default_inputs,
        help="Manuscript JSONL files to register",
    )
    args = ap.parse_args()

    entries: list[dict] = []
    for p in args.jsonl:
        p = p.resolve()
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2
        rel = p.relative_to(root).as_posix()
        rows = 0
        with p.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows += 1
        entries.append(
            {
                "path_workspace": rel,
                "row_count": rows,
                "file_sha256": file_sha256(p),
                "encoding": "UTF-8",
            }
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "schema_version": "1.0",
        "manifest_id": "LOGOS_DSS_MANIFEST",
        "updated_utc": now,
        "track": "logos_manuscripts",
        "verify_script": "scripts/verify_logos_manuscripts_integrity.py",
        "backfill_script": "scripts/backfill_logos_manuscript_hashes.py",
        "builder_script": "scripts/build_logos_dss_manifest.py",
        "notes": "Self-contained JSONL rows (DSS, apocrypha). Canonical text per row matches verify_logos_manuscripts_integrity.canonical_text_for_row.",
        "manuscript_files": entries,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
