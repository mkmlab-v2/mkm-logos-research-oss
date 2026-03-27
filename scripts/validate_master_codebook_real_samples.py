#!/usr/bin/env python3
"""Validate real-text sample set against dual-track master codebook lookup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CODEBOOK = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.multidomain_5000.json"
DEFAULT_SAMPLES = WORKSPACE_ROOT / "data" / "constitution" / "master_codebook_real_validation_samples.jsonl"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_codebook(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("codebook must be object")
    return payload


def _expected_from_lookup(lookup: dict[str, Any]) -> str:
    lid = str(lookup.get("lookup_id", ""))
    canonical = lookup.get("canonical_output", {})
    if not isinstance(canonical, dict):
        return ""

    if lid == "constitution.parent_map.ty":
        return str(canonical.get("parent_name", ""))
    if lid == "compression.core.zlib_lossless":
        return str(canonical.get("strategy", ""))
    if lid == "ops.policy.off_by_default":
        policy = canonical.get("policy_enabled")
        return "off_by_default=true" if policy is True else ""
    if lid == "other.guardian.mode.hybrid":
        return "MODEL_PROVIDER=hybrid"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate real text samples against master codebook")
    ap.add_argument("--codebook", default=str(DEFAULT_CODEBOOK), help="Codebook JSON")
    ap.add_argument("--samples", default=str(DEFAULT_SAMPLES), help="Real validation JSONL")
    args = ap.parse_args()

    codebook_path = _as_abs(args.codebook)
    samples_path = _as_abs(args.samples)

    errors: list[str] = []
    if not codebook_path.is_file():
        errors.append(f"codebook not found: {codebook_path}")
    if not samples_path.is_file():
        errors.append(f"samples not found: {samples_path}")
    if errors:
        print("❌ real sample validation failed")
        for e in errors:
            print(f"- {e}")
        return 1

    payload = _load_codebook(codebook_path)
    lookup = payload.get("lookup", {})
    entries = lookup.get("entries", []) if isinstance(lookup, dict) else []
    if not isinstance(entries, list):
        print("❌ real sample validation failed")
        print("- codebook lookup.entries must be list")
        return 1

    lookup_index: dict[str, dict[str, Any]] = {}
    for row in entries:
        if isinstance(row, dict) and isinstance(row.get("lookup_id"), str):
            lookup_index[row["lookup_id"]] = row

    total = 0
    matched = 0
    with samples_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            sid = row.get("sample_id")
            lref = row.get("lookup_id_ref")
            prompt = row.get("prompt")
            expected = row.get("response_expected")
            if not isinstance(sid, str) or not sid:
                errors.append("sample_id missing/invalid")
                continue
            if not isinstance(lref, str) or lref not in lookup_index:
                errors.append(f"{sid}: lookup_id_ref invalid ({lref})")
                continue
            if not isinstance(prompt, str) or len(prompt.strip()) < 8:
                errors.append(f"{sid}: prompt too short")
                continue
            if not isinstance(expected, str) or not expected.strip():
                errors.append(f"{sid}: response_expected missing")
                continue

            derived = _expected_from_lookup(lookup_index[lref])
            if expected.strip() != derived.strip():
                errors.append(f"{sid}: expected mismatch ({expected} != {derived})")
                continue
            matched += 1

    if errors:
        print("❌ real sample validation failed")
        print(f"total: {total}, matched: {matched}")
        for e in errors[:20]:
            print(f"- {e}")
        return 1

    print("✅ real sample validation passed")
    print(f"codebook: {codebook_path.resolve()}")
    print(f"samples: {samples_path.resolve()}")
    print(f"total: {total}, matched: {matched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
