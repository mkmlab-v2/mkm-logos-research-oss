#!/usr/bin/env python3
"""Validate contrastive challenge set reproducibility contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_contrastive_challenge_summary_latest.json"
EXPECTED_PROFILE_ID = "logos_contrastive_challenge_v2"
EXPECTED_SCHEMA = "logos_falsification_contrastive_challenge_summary_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check reproducibility lock for contrastive challenge set.")
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    failures: list[str] = []
    summary = _load(args.summary_json)
    news_output = Path(str(summary.get("news_output", "")))
    labels_output = Path(str(summary.get("labels_output", "")))

    if summary.get("schema") != EXPECTED_SCHEMA:
        failures.append("schema_mismatch")
    if summary.get("profile_id") != EXPECTED_PROFILE_ID:
        failures.append("profile_id_mismatch")
    if int(summary.get("news_rows", -1)) != 48:
        failures.append("news_rows_mismatch")
    if int(summary.get("label_rows", -1)) != 48:
        failures.append("label_rows_mismatch")
    if not news_output.is_file():
        failures.append("missing_news_output")
    if not labels_output.is_file():
        failures.append("missing_labels_output")

    expected_hashes = summary.get("content_sha256", {})
    if not isinstance(expected_hashes, dict):
        failures.append("missing_content_sha256")
        expected_hashes = {}

    observed_news_hash = _sha256(news_output) if news_output.is_file() else None
    observed_labels_hash = _sha256(labels_output) if labels_output.is_file() else None

    if expected_hashes.get("news_jsonl") != observed_news_hash:
        failures.append("news_hash_mismatch")
    if expected_hashes.get("labels_jsonl") != observed_labels_hash:
        failures.append("labels_hash_mismatch")

    result = {
        "ok": len(failures) == 0,
        "summary_json": str(args.summary_json),
        "profile_id": summary.get("profile_id"),
        "news_rows": summary.get("news_rows"),
        "label_rows": summary.get("label_rows"),
        "expected_hashes": expected_hashes,
        "observed_hashes": {
            "news_jsonl": observed_news_hash,
            "labels_jsonl": observed_labels_hash,
        },
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
