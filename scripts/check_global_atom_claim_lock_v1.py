#!/usr/bin/env python3
"""Verify and optionally refresh the Global Atom claim lock registry.

This script protects high-visibility claim numbers (e.g. ~3.05M edges)
by verifying they still match the frozen evidence artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _claim(registry: dict[str, Any], claim_id: str) -> dict[str, Any]:
    claims = registry.get("claims")
    if not isinstance(claims, list):
        raise SystemExit("invalid registry: claims must be a list")
    for item in claims:
        if isinstance(item, dict) and item.get("claim_id") == claim_id:
            return item
    raise SystemExit(f"claim_id not found: {claim_id}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_registry = root / "docs" / "final" / "artifacts" / "global_atom_claim_lock_registry_latest.json"
    default_claim_id = "global_atom_edge_count_305m_v1"

    ap = argparse.ArgumentParser(description="Check Global Atom claim lock values against frozen evidence.")
    ap.add_argument("--registry-json", default=str(default_registry))
    ap.add_argument("--claim-id", default=default_claim_id)
    ap.add_argument("--write-lock", action="store_true", help="Update sha256 placeholder with current file hash.")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero when mismatches are found.")
    args = ap.parse_args()

    reg_path = Path(args.registry_json)
    if not reg_path.exists():
        raise SystemExit(f"missing registry: {reg_path}")
    registry = _load_json(reg_path)
    c = _claim(registry, args.claim_id)

    src = c.get("source_of_truth") if isinstance(c.get("source_of_truth"), dict) else {}
    src_path = Path(str(src.get("path", "")))
    if not src_path.exists():
        raise SystemExit(f"missing source artifact: {src_path}")
    src_doc = _load_json(src_path)
    src_edge_count = (((src_doc.get("key_facts") if isinstance(src_doc.get("key_facts"), dict) else {})).get("edge_count"))
    if not isinstance(src_edge_count, int):
        raise SystemExit("source artifact missing key_facts.edge_count")

    expected = c.get("value")
    mismatch = bool(expected != src_edge_count)
    src_hash = _sha256(src_path)
    locked_hash = src.get("sha256_placeholder")
    hash_mismatch = isinstance(locked_hash, str) and locked_hash not in ("", "TBD_RECOMPUTE_AND_LOCK", src_hash)

    out = {
        "schema": "global_atom_claim_lock_check_v1",
        "checked_at_utc": _now_utc(),
        "claim_id": args.claim_id,
        "expected_value": expected,
        "observed_value": src_edge_count,
        "value_match": not mismatch,
        "source_path": str(src_path),
        "source_sha256": src_hash,
        "locked_sha256": locked_hash,
        "hash_match": not hash_mismatch,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.write_lock:
        src["sha256_placeholder"] = src_hash
        c["source_of_truth"] = src
        registry["generated_at_utc"] = _now_utc()
        reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.strict and (mismatch or hash_mismatch):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
