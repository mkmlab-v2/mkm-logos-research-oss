#!/usr/bin/env python3
"""Validate recovered codepack assets from archive import.

This checker is intentionally lightweight and fact-safe:
- verifies required files exist
- computes SHA256 and byte size
- validates JSON parseability for recovered datasets
- writes a single latest artifact report
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "scripts" / "experimental" / "codepack_recovery"
OUT = ROOT / "docs" / "final" / "artifacts" / "recovered_codepack_validation_latest.json"

REQUIRED_CODE = [
    "core/unified_codebook_builder.py",
    "core/mkm_sovereign_codebook.py",
    "core/oracle_codebook.py",
    "core/build_full_codebook.py",
    "core/build_codebook_with_progress.py",
    "core/force_rebuild_s_codebook.py",
    "scripts/build_standard_codebook.py",
    "scripts/step2_build_all_domain_codebooks.py",
    "scripts/build_spirit_domain_codebook.py",
    "scripts/build_knowledge_domain_codebook.py",
]

REQUIRED_JSON = [
    "data/education_codebook.json",
    "data/sovereign_codebook.json",
    "data/signal_codebook_service_repo_bootstrap.json",
    "data/backtest_signal_codebook_service_repo_bootstrap.json",
    "data/signal_codebook_mkm_life_pr.json",
    "data/s_codebook_sample.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _inspect_file(rel: str, *, parse_json: bool) -> dict[str, Any]:
    path = BASE / rel
    if not path.is_file():
        return {"path": rel, "exists": False}
    out: dict[str, Any] = {
        "path": rel,
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    if parse_json:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            out["json_valid"] = True
            if isinstance(payload, dict):
                out["json_top_level"] = "object"
                out["top_level_key_count"] = len(payload)
            elif isinstance(payload, list):
                out["json_top_level"] = "array"
                out["top_level_key_count"] = len(payload)
            else:
                out["json_top_level"] = type(payload).__name__
                out["top_level_key_count"] = None
        except Exception as exc:  # pragma: no cover
            out["json_valid"] = False
            out["json_error"] = str(exc)
    return out


def main() -> int:
    code_rows = [_inspect_file(p, parse_json=False) for p in REQUIRED_CODE]
    json_rows = [_inspect_file(p, parse_json=True) for p in REQUIRED_JSON]
    ok = all(r.get("exists") for r in code_rows) and all(
        r.get("exists") and r.get("json_valid") for r in json_rows
    )

    report = {
        "schema": "recovered_codepack_validation_v1",
        "generated_at_utc": _utc_now(),
        "base_path": str(BASE),
        "ok": ok,
        "counts": {
            "code_required": len(REQUIRED_CODE),
            "json_required": len(REQUIRED_JSON),
            "code_present": sum(1 for r in code_rows if r.get("exists")),
            "json_present": sum(1 for r in json_rows if r.get("exists")),
            "json_valid": sum(1 for r in json_rows if r.get("json_valid")),
        },
        "code_files": code_rows,
        "json_files": json_rows,
        "fact_safe_note": "Archive import validation only. No production routing or performance claims.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

