#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build lock manifest for holdout dataset JSONL.")
    ap.add_argument("--dataset-jsonl", default="docs/final/artifacts/global_atom_news_holdout_dataset_v1.jsonl")
    ap.add_argument("--out-json", default="docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json")
    args = ap.parse_args()

    ds = resolve(args.dataset_jsonl)
    if not ds.is_file():
        raise SystemExit(f"missing dataset jsonl: {ds}")
    out = resolve(args.out_json)

    manifest = {
        "schema": "global_atom_news_holdout_dataset_lock_manifest_v1",
        "generated_at_utc": now(),
        "dataset_path": str(ds),
        "dataset_sha256": sha256_file(ds),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

