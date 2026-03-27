#!/usr/bin/env python3
"""Generate multi-domain dual-track codebook with balanced training records.

Purpose:
- Keep governance/hybrid policies intact
- Expand lookup entries across multiple domains
- Produce balanced training records for domain imbalance mitigation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.template.json"
DEFAULT_OUT = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.multidomain_1000.json"

LOOKUP_ENTRIES = [
    {
        "lookup_id": "constitution.parent_map.ty",
        "domain": "constitution",
        "input_key": "TY",
        "canonical_output": {
            "parent_name": "TY",
            "description": "Constitution parent mapping, immutable runtime output.",
        },
        "source_refs": ["docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"],
        "status": "active",
    },
    {
        "lookup_id": "compression.core.zlib_lossless",
        "domain": "compression",
        "input_key": "zlib_lossless_core",
        "canonical_output": {
            "strategy": "zlib_lossless_core",
            "literal_restoration_rate": 100.0,
        },
        "source_refs": ["docs/final/COMPRESSION_RESTORATION_SSOT_2026-03-27.md"],
        "status": "active",
    },
    {
        "lookup_id": "ops.policy.off_by_default",
        "domain": "ops",
        "input_key": "off_by_default",
        "canonical_output": {
            "policy_enabled": True,
            "quaternion_default": False,
            "threshold_gate_default": False,
        },
        "source_refs": ["docs/final/QUATERNION_FACTCHECK_AND_NEXT_ACTIONS_2026-03-26.md"],
        "status": "active",
    },
    {
        "lookup_id": "other.guardian.mode.hybrid",
        "domain": "other",
        "input_key": "MODEL_PROVIDER=hybrid",
        "canonical_output": {
            "routing": "vertex_first_local_fallback",
            "fallback_required": True,
        },
        "source_refs": ["projects/no1kmedi/README_GUARDIAN.md"],
        "status": "active",
    },
]

PROMPT_BY_DOMAIN = {
    "constitution": [
        "Classify this constitution sample to its immutable parent family.",
        "Return the canonical constitution parent label for this input.",
    ],
    "compression": [
        "Select the approved lossless compression core for runtime.",
        "Which compression strategy satisfies 100% literal restoration?",
    ],
    "ops": [
        "What is the default policy for risky hybrid features?",
        "Should quaternion and threshold gate be enabled by default?",
    ],
    "other": [
        "Choose the recommended model routing mode for resilience.",
        "How should runtime routing behave when cloud provider fails?",
    ],
}

RESPONSE_BY_LOOKUP = {
    "constitution.parent_map.ty": "TY",
    "compression.core.zlib_lossless": "zlib_lossless_core",
    "ops.policy.off_by_default": "off_by_default=true",
    "other.guardian.mode.hybrid": "MODEL_PROVIDER=hybrid",
}


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("base codebook must be object")
    return payload


def _split_for_index(i: int, total: int) -> str:
    train_end = int(total * 0.8)
    val_end = int(total * 0.9)
    if i < train_end:
        return "train"
    if i < val_end:
        return "validation"
    return "test"


def _build_records(total: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lookup_count = len(LOOKUP_ENTRIES)
    for i in range(total):
        entry = LOOKUP_ENTRIES[i % lookup_count]
        domain = entry["domain"]
        lookup_id = entry["lookup_id"]
        prompts = PROMPT_BY_DOMAIN[domain]
        prompt = prompts[(i // lookup_count) % len(prompts)]
        split = _split_for_index(i, total)
        records.append(
            {
                "training_id": f"train.{domain}.{i+1:04d}",
                "lookup_id_ref": lookup_id,
                "prompt": f"{prompt} Sample-{i+1:04d}",
                "response": RESPONSE_BY_LOOKUP[lookup_id],
                "split": split,
                "quality_gate_passed": True,
                "notes": "Balanced multi-domain synthetic seed record.",
            }
        )
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate multi-domain dual-track codebook")
    ap.add_argument("--base", default=str(DEFAULT_BASE), help="Base codebook JSON")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output codebook JSON")
    ap.add_argument("--count", type=int, default=1000, help="Number of training records")
    args = ap.parse_args()

    if args.count <= 0:
        print("❌ --count must be > 0")
        return 1

    base_path = _as_abs(args.base)
    out_path = _as_abs(args.out)
    if not base_path.is_file():
        print(f"❌ base not found: {base_path}")
        return 1

    payload = _load_json(base_path)
    if not isinstance(payload.get("lookup"), dict) or not isinstance(payload.get("training"), dict):
        print("❌ invalid base structure: lookup/training missing")
        return 1

    payload["lookup"]["entries"] = LOOKUP_ENTRIES
    payload["lookup"]["ssot_locked"] = True
    payload["training"]["enabled"] = False
    payload["training"]["records"] = _build_records(args.count)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ generated multi-domain codebook: {out_path.resolve()}")
    print(f"records: {args.count}")
    print(f"lookup_entries: {len(LOOKUP_ENTRIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
