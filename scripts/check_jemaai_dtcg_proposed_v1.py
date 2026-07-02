#!/usr/bin/env python3
"""Validate JEMA AI proposed DTCG token skeleton (Pack A Antigravity input).

  py scripts/check_jemaai_dtcg_proposed_v1.py

Exit 0 = structure OK for antigravity handoff. Does not validate visual quality.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DTCG = ROOT / "docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json"
SEED = ROOT / "docs/final/artifacts/jemaai_design_reference_seed_antigravity_v1.json"
AUDIT = ROOT / "docs/final/artifacts/jemaai_design_audit_surface_map_v1_latest.json"

REQUIRED_DTCG_KEYS = [
    "schema",
    "shared_primitive",
    "semantic",
    "presets",
    "css_var_map_existing",
    "antigravity_proposed_output_slots",
    "forbidden",
    "acceptance_after_cursor_merge",
]

REQUIRED_PRESETS = [
    "jemaai-marketing-stripe-linear",
    "jemaai-enterprise-trust",
    "jemaai-hub-discover-v3",
]

REQUIRED_SEMANTIC_TRUST = ["clinical", "saas", "hub"]


def main() -> int:
    errors: list[str] = []

    if not DTCG.is_file():
        errors.append(f"missing {DTCG.relative_to(ROOT)}")
    if not SEED.is_file():
        errors.append(f"missing {SEED.relative_to(ROOT)}")
    if not AUDIT.is_file():
        errors.append(f"missing {AUDIT.relative_to(ROOT)}")

    if errors:
        for e in errors:
            print(f"[check_jemaai_dtcg_proposed_v1] FAIL: {e}")
        return 1

    dtcg = json.loads(DTCG.read_text(encoding="utf-8"))
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    if dtcg.get("schema") != "jemaai_dtcg_tokens_proposed_v1":
        errors.append("dtcg.schema mismatch")
    if dtcg.get("send_gate") != "HOLD":
        errors.append("dtcg.send_gate must be HOLD")
    if seed.get("schema") != "design_reference_seed_v1":
        errors.append("seed.schema mismatch")
    if audit.get("schema") != "jemaai_design_audit_surface_map_v1":
        errors.append("audit.schema mismatch")

    for key in REQUIRED_DTCG_KEYS:
        if key not in dtcg:
            errors.append(f"dtcg missing key: {key}")

    presets = dtcg.get("presets", {})
    for name in REQUIRED_PRESETS:
        if name not in presets:
            errors.append(f"dtcg.presets missing: {name}")

    trust = dtcg.get("semantic", {}).get("trust", {})
    for role in REQUIRED_SEMANTIC_TRUST:
        if role not in trust:
            errors.append(f"semantic.trust missing: {role}")

    clinical = trust.get("clinical", {}).get("accent", {}).get("$value", "")
    saas = trust.get("saas", {}).get("accent", {}).get("$value", "")
    if clinical == saas:
        errors.append("clinical and saas accent must not be identical references")

    slots = dtcg.get("antigravity_proposed_output_slots", [])
    if len(slots) < 5:
        errors.append("antigravity_proposed_output_slots too few")

    if seed.get("dtcg_input") != "docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json":
        errors.append("seed.dtcg_input path mismatch")

    if errors:
        print("[check_jemaai_dtcg_proposed_v1] FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "schema": dtcg.get("schema"),
                "presets": list(presets.keys()),
                "proposed_slots": len(slots),
                "dtcg": str(DTCG.relative_to(ROOT)).replace("\\", "/"),
                "seed": str(SEED.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
