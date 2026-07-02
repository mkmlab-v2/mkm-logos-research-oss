#!/usr/bin/env python3
"""Verify logos inquiry S4 synthesis allowlist artifact (P0 security wire)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/logos_inquiry_s4_synthesis_allowlist_v1_latest.json"


def main() -> int:
    if not SPEC.is_file():
        print(json.dumps({"ok": False, "error": "missing_spec", "path": str(SPEC)}))
        return 1
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    ok = (
        doc.get("schema") == "logos_inquiry_s4_synthesis_allowlist_v1"
        and doc.get("default_mode") == "deterministic_conflict_parallel"
        and doc.get("inquiry_beta_policy", {}).get("s4_llm_default") == "off"
        and bool(doc.get("forbidden_llm_payload"))
    )
    print(json.dumps({"ok": ok, "path": str(SPEC)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
