#!/usr/bin/env python3
"""Enforce corpus_profile_id lock across Global Atom artifacts."""

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


def _allowed_profiles(profiles_doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    profiles = profiles_doc.get("profiles")
    if not isinstance(profiles, list):
        return out
    for p in profiles:
        if isinstance(p, dict):
            pid = p.get("corpus_profile_id")
            if isinstance(pid, str) and pid:
                out.add(pid)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_profiles = root / "docs" / "final" / "artifacts" / "global_atom_corpus_profiles_v1.json"
    default_registry = root / "docs" / "final" / "artifacts" / "global_atom_claim_lock_registry_latest.json"
    default_anchor = root / "docs" / "final" / "artifacts" / "global_atom_edge_claim_anchor_v1.json"
    default_atom = root / "docs" / "final" / "artifacts" / "global_atom_edge_claim_atom_set_latest.json"

    ap = argparse.ArgumentParser(description="Check corpus_profile_id consistency across Global Atom lock artifacts.")
    ap.add_argument("--profiles-json", default=str(default_profiles))
    ap.add_argument("--claim-lock-json", default=str(default_registry))
    ap.add_argument("--anchor-json", default=str(default_anchor))
    ap.add_argument("--atom-set-json", default=str(default_atom))
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    profiles_path = Path(args.profiles_json)
    claim_path = Path(args.claim_lock_json)
    anchor_path = Path(args.anchor_json)
    atom_path = Path(args.atom_set_json)

    for p in (profiles_path, claim_path, anchor_path, atom_path):
        if not p.exists():
            raise SystemExit(f"missing required file: {p}")

    profiles_doc = _load_json(profiles_path)
    claim_doc = _load_json(claim_path)
    anchor_doc = _load_json(anchor_path)
    atom_doc = _load_json(atom_path)

    allowed = _allowed_profiles(profiles_doc)
    failures: list[str] = []

    expected = claim_doc.get("corpus_profile_id")
    if not isinstance(expected, str) or not expected:
        failures.append("claim lock top-level corpus_profile_id missing")
        expected = None
    elif expected not in allowed:
        failures.append(f"claim lock corpus_profile_id not in allowed set: {expected}")

    anchor_pid = anchor_doc.get("corpus_profile_id")
    if expected and anchor_pid != expected:
        failures.append(f"anchor corpus_profile_id mismatch: {anchor_pid} != {expected}")

    atom_pid = atom_doc.get("corpus_profile_id")
    if expected and atom_pid != expected:
        failures.append(f"atom set corpus_profile_id mismatch: {atom_pid} != {expected}")

    claim_items = claim_doc.get("claims")
    claim_item_pids: list[tuple[str, Any]] = []
    if isinstance(claim_items, list):
        for item in claim_items:
            if isinstance(item, dict):
                claim_item_pids.append((str(item.get("claim_id", "")), item.get("corpus_profile_id")))
                if expected and item.get("corpus_profile_id") != expected:
                    failures.append(
                        f"claim item corpus_profile_id mismatch: claim_id={item.get('claim_id')} value={item.get('corpus_profile_id')}"
                    )

    onepager_checks: list[dict[str, Any]] = []
    # claim source onepager
    if isinstance(claim_items, list):
        for item in claim_items:
            if not isinstance(item, dict):
                continue
            src = item.get("source_of_truth")
            src_path_raw = src.get("path") if isinstance(src, dict) else None
            if not isinstance(src_path_raw, str) or not src_path_raw:
                continue
            sp = Path(src_path_raw)
            observed_pid = None
            if sp.exists():
                observed_pid = _load_json(sp).get("corpus_profile_id")
            onepager_checks.append({"path": str(sp), "corpus_profile_id": observed_pid, "exists": sp.exists()})
            if expected and observed_pid != expected:
                failures.append(f"source onepager corpus_profile_id mismatch: {sp} => {observed_pid} != {expected}")

    # latest reference onepager from anchor evidence
    evidence = anchor_doc.get("evidence")
    latest_path_raw = evidence.get("latest_onepager_path") if isinstance(evidence, dict) else None
    if isinstance(latest_path_raw, str) and latest_path_raw:
        lp = Path(latest_path_raw)
        observed_pid = None
        if lp.exists():
            observed_pid = _load_json(lp).get("corpus_profile_id")
        onepager_checks.append({"path": str(lp), "corpus_profile_id": observed_pid, "exists": lp.exists()})
        if expected and observed_pid != expected:
            failures.append(f"latest onepager corpus_profile_id mismatch: {lp} => {observed_pid} != {expected}")

    atoms = atom_doc.get("atoms")
    atom_item_pids: list[tuple[str, Any]] = []
    if isinstance(atoms, list):
        for a in atoms:
            if not isinstance(a, dict):
                continue
            atom_item_pids.append((str(a.get("atom_id", "")), a.get("corpus_profile_id")))
            if expected and a.get("corpus_profile_id") != expected:
                failures.append(
                    f"atom corpus_profile_id mismatch: atom_id={a.get('atom_id')} value={a.get('corpus_profile_id')}"
                )

    out = {
        "schema": "global_atom_corpus_profile_lock_check_v1",
        "checked_at_utc": _now_utc(),
        "allowed_profile_ids": sorted(list(allowed)),
        "expected_corpus_profile_id": expected,
        "anchor_corpus_profile_id": anchor_pid,
        "atom_set_corpus_profile_id": atom_pid,
        "claim_item_profiles": claim_item_pids,
        "atom_item_profiles": atom_item_pids,
        "onepager_profile_checks": onepager_checks,
        "failures": failures,
        "ok": len(failures) == 0,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
