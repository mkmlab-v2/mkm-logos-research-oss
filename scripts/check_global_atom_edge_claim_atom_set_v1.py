#!/usr/bin/env python3
"""Validate edge_claim_atom_set_v1 against source artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_key_facts(path: Path) -> tuple[int | None, int | None]:
    if not path.exists():
        return None, None
    doc = _load_json(path)
    key_facts = doc.get("key_facts")
    if not isinstance(key_facts, dict):
        return None, None
    edge = key_facts.get("edge_count")
    node = key_facts.get("node_count")
    return (edge if isinstance(edge, int) else None, node if isinstance(node, int) else None)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_atom_set = root / "docs" / "final" / "artifacts" / "global_atom_edge_claim_atom_set_latest.json"
    default_claim_registry = root / "docs" / "final" / "artifacts" / "global_atom_claim_lock_registry_latest.json"

    ap = argparse.ArgumentParser(description="Validate edge claim atom set against source artifacts.")
    ap.add_argument("--atom-set-json", default=str(default_atom_set))
    ap.add_argument("--claim-lock-json", default=str(default_claim_registry))
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    atom_path = Path(args.atom_set_json)
    claim_path = Path(args.claim_lock_json)
    if not atom_path.exists():
        raise SystemExit(f"missing atom set: {atom_path}")
    if not claim_path.exists():
        raise SystemExit(f"missing claim lock registry: {claim_path}")

    atom_doc = _load_json(atom_path)
    claim_doc = _load_json(claim_path)
    atoms = atom_doc.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        raise SystemExit("invalid atom set: atoms must be non-empty list")

    claim_value = None
    expected_profile = claim_doc.get("corpus_profile_id")
    atom_set_profile = atom_doc.get("corpus_profile_id")
    claims = claim_doc.get("claims")
    if isinstance(claims, list):
        for c in claims:
            if isinstance(c, dict) and c.get("claim_id") == atom_doc.get("claim_id"):
                v = c.get("value")
                claim_value = v if isinstance(v, int) else None
                break

    failures: list[str] = []
    atom_checks: list[dict[str, Any]] = []
    anchor_edge = None
    latest_edge = None
    for a in atoms:
        if not isinstance(a, dict):
            failures.append("atom entry is not object")
            continue
        atom_id = str(a.get("atom_id", ""))
        role = str(a.get("atom_role", ""))
        source = a.get("source_of_truth")
        src_path_raw = source.get("path") if isinstance(source, dict) else None
        src_path = Path(src_path_raw) if isinstance(src_path_raw, str) and src_path_raw else Path("")
        observed_edge, observed_node = _read_key_facts(src_path)
        expected_edge = a.get("edge_count") if isinstance(a.get("edge_count"), int) else None
        expected_node = a.get("node_count") if isinstance(a.get("node_count"), int) else None
        edge_match = expected_edge is not None and observed_edge is not None and expected_edge == observed_edge
        node_match = expected_node is not None and observed_node is not None and expected_node == observed_node
        atom_profile = a.get("corpus_profile_id")
        source_profile = _load_json(src_path).get("corpus_profile_id") if src_path.exists() else None

        if not edge_match:
            failures.append(f"{atom_id}: edge mismatch (expected={expected_edge}, observed={observed_edge})")
        if not node_match:
            failures.append(f"{atom_id}: node mismatch (expected={expected_node}, observed={observed_node})")
        if atom_profile != expected_profile:
            failures.append(f"{atom_id}: corpus_profile_id mismatch (atom={atom_profile}, expected={expected_profile})")
        if source_profile != expected_profile:
            failures.append(f"{atom_id}: source corpus_profile_id mismatch (source={source_profile}, expected={expected_profile})")

        if role == "anchor_baseline":
            anchor_edge = expected_edge
        if role == "current_reference":
            latest_edge = expected_edge

        atom_checks.append(
            {
                "atom_id": atom_id,
                "atom_role": role,
                "source_path": str(src_path),
                "edge_expected": expected_edge,
                "edge_observed": observed_edge,
                "edge_match": edge_match,
                "node_expected": expected_node,
                "node_observed": observed_node,
                "node_match": node_match,
                "corpus_profile_id_atom": atom_profile,
                "corpus_profile_id_source": source_profile,
            }
        )

    claim_match = claim_value is not None and anchor_edge is not None and claim_value == anchor_edge
    if not claim_match:
        failures.append(f"claim lock value mismatch (claim={claim_value}, anchor={anchor_edge})")
    if not isinstance(expected_profile, str) or not expected_profile:
        failures.append("claim lock corpus_profile_id missing")
    if atom_set_profile != expected_profile:
        failures.append(f"atom set corpus_profile_id mismatch (atom_set={atom_set_profile}, claim={expected_profile})")

    out = {
        "schema": "edge_claim_atom_set_check_v1",
        "checked_at_utc": _now_utc(),
        "atom_set_path": str(atom_path),
        "claim_lock_path": str(claim_path),
        "claim_id": atom_doc.get("claim_id"),
        "claim_value": claim_value,
        "anchor_edge_count": anchor_edge,
        "latest_edge_count": latest_edge,
        "latest_minus_anchor": (latest_edge - anchor_edge) if isinstance(latest_edge, int) and isinstance(anchor_edge, int) else None,
        "claim_anchor_match": claim_match,
        "corpus_profile_id_claim_lock": expected_profile,
        "corpus_profile_id_atom_set": atom_set_profile,
        "atom_checks": atom_checks,
        "failures": failures,
        "ok": len(failures) == 0,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
