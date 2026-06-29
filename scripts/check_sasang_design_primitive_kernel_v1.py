#!/usr/bin/env python3
"""Offline gate: sasang_design_primitive_kernel_v1_latest.json schema and SSOT refs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/sasang_design_primitive_kernel_v1.schema.json"
CHARTER = ROOT / "docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md"
REQUIRED_PRODUCTS = (
    "personadiary.com",
    "mkmlife.com",
    "jema-ai.com",
    "jemaai.cloud",
    "a-codeai.com",
    "logos.jema-ai.com",
    "internal_ops",
)


def main() -> int:
    missing = [p for p in (KERNEL, SCHEMA, CHARTER) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"MISSING: {p}", file=sys.stderr)
        return 1

    doc = json.loads(KERNEL.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_design_primitive_kernel_v1":
        print("bad schema field", file=sys.stderr)
        return 1

    try:
        import jsonschema
    except ImportError:
        print("jsonschema not installed — run pytest for full validation", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)

    product_depth = doc.get("product_depth") or {}
    missing_products = [p for p in REQUIRED_PRODUCTS if p not in product_depth]
    if missing_products:
        print(f"missing product_depth keys: {missing_products}", file=sys.stderr)
        return 1

    gate = doc.get("gate_contract") or {}
    for ref_key in ("copy_contract_ref", "forbidden_synthesis_ref"):
        rel = gate.get(ref_key)
        if rel and not (ROOT / rel).is_file():
            print(f"missing gate ref {ref_key}={rel}", file=sys.stderr)
            return 1

    anchors = doc.get("primitives", {}).get("valence", {}).get("anchors_ssot", "")
    if anchors and not (ROOT / anchors).is_file():
        print(f"missing valence anchors_ssot: {anchors}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "overall_ok": True,
                "kernel_version": doc.get("kernel_version"),
                "products": list(product_depth.keys()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
