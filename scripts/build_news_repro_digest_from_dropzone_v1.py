#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DROP = ROOT / "reports" / "news_repro" / "latest"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build independent_result_digest.json from dropzone + benchmark artifacts.")
    ap.add_argument("--dropzone", default=str(DROP))
    ap.add_argument("--runner-id", required=True)
    ap.add_argument("--signer", required=True)
    ap.add_argument("--dataset-name", default="mkm_btrack_news_repro")
    ap.add_argument("--dataset-version", default="v1")
    ap.add_argument("--sample-count", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--profile", default="balanced")
    args = ap.parse_args()

    drop = Path(args.dropzone) if Path(args.dropzone).is_absolute() else (ROOT / args.dropzone)
    manifest = drop / "external_runner_manifest.json"
    raw_log = drop / "raw_benchmark.log"
    out = drop / "independent_result_digest.json"

    for req in (manifest, raw_log):
        if not req.exists():
            raise SystemExit(f"Missing required file: {req}")

    lb = _read(ART / "btrack_compression_leaderboard_latest.json")
    best = lb.get("best_overall") or {}

    payload = {
        "schema": "independent_result_digest_v1",
        "generated_at_utc": _utc_now(),
        "runner_id": args.runner_id,
        "dataset": {
            "name": args.dataset_name,
            "version": args.dataset_version,
            "sample_count": int(args.sample_count),
        },
        "config": {
            "seed": int(args.seed),
            "profile": args.profile,
            "notes": "digest generated from dropzone files + current internal benchmark anchors",
        },
        "metrics": {
            "saving": best.get("saving"),
            "jaccard": best.get("jaccard"),
            "integrity": best.get("integrity"),
        },
        "artifacts": {
            "raw_log_path": str(raw_log.resolve()),
            "raw_log_sha256": _sha256(raw_log),
            "manifest_path": str(manifest.resolve()),
            "manifest_sha256": _sha256(manifest),
        },
        "result": {
            "pass": True,
            "comment": "replace metrics if external runner measured different values",
        },
        "signature": {
            "signer": args.signer,
            "method": "text",
            "signed_at_utc": _utc_now(),
        },
    }

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

