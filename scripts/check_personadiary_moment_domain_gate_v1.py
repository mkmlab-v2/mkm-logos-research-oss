#!/usr/bin/env python3
"""Offline gate: personadiary moment domain pack + preview ops pointer [B-track]."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/commander/domain_packs/personadiary_moment_pack_v1.json"
PREVIEW = ROOT / "docs/final/artifacts/personadiary_preview_ops_v1_latest.json"
OUT = ROOT / "reports/personadiary_moment_domain_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    errors: list[str] = []
    if not PACK.is_file():
        errors.append(f"missing pack: {PACK}")
    else:
        doc = json.loads(PACK.read_text(encoding="utf-8-sig"))
        if doc.get("schema") != "general_prophecy_registry_v1":
            errors.append("pack schema mismatch")
    preview_ok = PREVIEW.is_file()
    ok = not errors
    report = {
        "schema": "personadiary_moment_domain_gate_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "pack_path": str(PACK.relative_to(ROOT)).replace("\\", "/"),
        "preview_ops_present": preview_ok,
        "errors": errors,
        "reproduce": "py scripts/check_personadiary_moment_domain_gate_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "preview_ops_present": preview_ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
