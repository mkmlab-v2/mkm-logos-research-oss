#!/usr/bin/env python3
"""Fail-safe must_keep_tags gate for ops memory index ([HYPO] / research_only).

Phase source — verify anchor slices in SSOT files still contain required tags.
Phase inject — verify assembled inject payload before chat resume pack use.

  py scripts/check_mkm_ops_memory_must_keep_gate_v1.py --phase source
  py scripts/check_mkm_ops_memory_must_keep_gate_v1.py --phase inject --payload-text "..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    extract_node_from_index,
    load_index,
    missing_must_keep_tags,
    verify_index_sha_drift,
    verify_index_sources,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def _verify_inject_payload(index: dict[str, Any], payload: str) -> list[str]:
    errors: list[str] = []
    nodes = index.get("nodes") or {}
    for node_id, node in nodes.items():
        tags = node.get("must_keep_tags") or []
        missing = missing_must_keep_tags(payload, tags)
        if missing:
            errors.append(f"{node_id}: inject payload missing tags: {missing}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--phase",
        choices=("source", "inject"),
        default="source",
        help="source=SSOT slices; inject=assembled payload text",
    )
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--payload-file", type=Path, help="Inject phase: text file to verify.")
    ap.add_argument("--payload-text", type=str, help="Inject phase: inline payload.")
    ap.add_argument(
        "--node-id",
        action="append",
        dest="node_ids",
        help="Limit verification to specific node id(s).",
    )
    ap.add_argument(
        "--fail-on-stale-sha",
        action="store_true",
        help="Exit 1 when indexed content_sha256_prefix drifts from live source.",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    try:
        index = load_index(args.index)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.phase == "source":
        if args.fail_on_stale_sha:
            drift_errors = verify_index_sha_drift(root, index)
            if drift_errors:
                for err in drift_errors:
                    print(f"FAIL: {err}", file=sys.stderr)
                return 1
            print("sha drift gate: OK")

        if args.node_ids:
            errors: list[str] = []
            nodes = index.get("nodes") or {}
            for node_id in args.node_ids:
                node = nodes.get(node_id)
                if not node:
                    errors.append(f"unknown node_id: {node_id}")
                    continue
                try:
                    block = extract_node_from_index(root, node)
                except (FileNotFoundError, ValueError) as exc:
                    errors.append(f"{node_id}: {exc}")
                    continue
                missing = missing_must_keep_tags(block, node.get("must_keep_tags") or [])
                if missing:
                    errors.append(f"{node_id}: must_keep_tags missing: {missing}")
        else:
            errors = verify_index_sources(root, index)

        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 1
        print("must_keep gate (phase=source): OK")
        return 0

    payload = args.payload_text
    if args.payload_file:
        payload = args.payload_file.read_text(encoding="utf-8")
    if not payload:
        print("FAIL: inject phase requires --payload-text or --payload-file", file=sys.stderr)
        return 1

    if args.node_ids:
        errors = []
        nodes = index.get("nodes") or {}
        for node_id in args.node_ids:
            node = nodes.get(node_id)
            if not node:
                errors.append(f"unknown node_id: {node_id}")
                continue
            missing = missing_must_keep_tags(payload, node.get("must_keep_tags") or [])
            if missing:
                errors.append(f"{node_id}: inject payload missing tags: {missing}")
    else:
        errors = _verify_inject_payload(index, payload)

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("must_keep gate (phase=inject): OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
