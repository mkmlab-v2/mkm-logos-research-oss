#!/usr/bin/env python3
"""M3: SHA256 manifest for codebook/shards (GitOps immutability smoke)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SHARDS = ROOT / "codebook" / "shards"
DEFAULT_OUT = ROOT / "docs/final/artifacts/codebook_manifest_hashes_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shards-dir", type=Path, default=SHARDS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--glob", type=str, default="zone_*.json")
    args = ap.parse_args()

    from scripts.core.compression_hardening_v1 import sha256_file

    rows: list[dict[str, Any]] = []
    for path in sorted(args.shards_dir.glob(args.glob)):
        if not path.is_file():
            continue
        digest = sha256_file(path)
        rows.append(
            {
                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
    if not rows:
        raise SystemExit(f"No shard files under {args.shards_dir}")

    doc = {
        "schema": "codebook_manifest_hashes_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "shards_dir": str(args.shards_dir.relative_to(ROOT)).replace("\\", "/"),
        "file_count": len(rows),
        "files": rows,
        "m3_note": "Baseline manifest; CI compares on change detection (future).",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "file_count": len(rows), "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
