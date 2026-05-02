#!/usr/bin/env python3
"""Track B slice 3 stub: validate vector index policy JSON + optional corpus bundle pointer.

Does not build embeddings or vector DB — readiness gate only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_POLICY_V1.json"
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "logos_corpus_graph_bundle_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument(
        "--bundle-json",
        type=Path,
        default=None,
        help="Optional logos_corpus_graph_bundle_v1 JSON (defaults to repo artifact if omitted with --require-bundle).",
    )
    ap.add_argument(
        "--require-bundle",
        action="store_true",
        help="Fail if bundle JSON missing or lacks dedupe_bundle_key_sha256.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print OK summary and exit 0.")
    args = ap.parse_args()

    if not args.policy.is_file():
        print(f"Missing policy: {args.policy}", file=sys.stderr)
        return 2

    doc = json.loads(args.policy.read_text(encoding="utf-8"))
    if doc.get("schema") != "logos_vector_index_policy_v1":
        print("Policy schema field mismatch.", file=sys.stderr)
        return 2

    bundle_path = args.bundle_json if args.bundle_json is not None else DEFAULT_BUNDLE
    if args.require_bundle or args.bundle_json is not None:
        if not bundle_path.is_file():
            print(f"Missing bundle: {bundle_path}", file=sys.stderr)
            return 2
        bdoc = json.loads(bundle_path.read_text(encoding="utf-8"))
        if bdoc.get("schema") != "logos_corpus_graph_bundle_v1":
            print("Bundle schema mismatch.", file=sys.stderr)
            return 2
        key = bdoc.get("dedupe_bundle_key_sha256")
        if not isinstance(key, str) or len(key) != 64:
            print("Bundle missing dedupe_bundle_key_sha256.", file=sys.stderr)
            return 2

    if args.dry_run:
        extra = ""
        if bundle_path.is_file():
            bdoc = json.loads(bundle_path.read_text(encoding="utf-8"))
            extra = f" bundle_dedupe={bdoc.get('dedupe_bundle_key_sha256', '')[:16]}…"
        print(f"OK policy={args.policy.name}{extra}")
        return 0

    print(json.dumps({"ok": True, "policy_schema": doc.get("schema")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
