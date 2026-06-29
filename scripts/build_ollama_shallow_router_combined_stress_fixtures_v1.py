#!/usr/bin/env python3
"""Merge base + stress shallow router golden fixtures for Phase 10-C [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
DEFAULT_STRESS = ROOT / "tests/fixtures/ollama_shallow_router_golden_stress_v1.json"
DEFAULT_OUT = ROOT / "tests/fixtures/ollama_shallow_router_golden_combined_stress_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge_fixtures(base: dict[str, Any], stress: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for src in (base, stress):
        for row in src.get("fixtures") or []:
            if not isinstance(row, dict):
                continue
            fid = str(row.get("id") or "")
            if not fid or fid in seen:
                continue
            merged.append(row)
            seen.add(fid)
    return {
        "schema": "ollama_shallow_router_golden_combined_stress_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "base_schema": base.get("schema"),
        "stress_schema": stress.get("schema"),
        "fixtures": merged,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--stress", type=Path, default=DEFAULT_STRESS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    base = json.loads(args.base.read_text(encoding="utf-8-sig"))
    stress = json.loads(args.stress.read_text(encoding="utf-8-sig"))
    doc = merge_fixtures(base, stress)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "fixtures": len(doc["fixtures"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
