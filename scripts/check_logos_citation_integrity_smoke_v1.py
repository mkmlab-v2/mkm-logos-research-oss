#!/usr/bin/env python3
"""Smoke: Logos Citation Integrity guardrail — CONSTITUTION pointer + validator + orphan cite veto."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
VALIDATOR = ROOT / "scripts/logos_response_validator_v1.py"
FIXTURE = ROOT / "tests/fixtures/logos_response_v1_valid_min.json"
SCHEMA = ROOT / "docs/final/artifacts/schemas/logos_response_schema_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_citation_integrity_smoke_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos citation integrity smoke v1")
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    checks: list[dict[str, object]] = []

    text = CONSTITUTION.read_text(encoding="utf-8", errors="replace") if CONSTITUTION.is_file() else ""
    marker_ok = "Logos Citation Integrity guardrail" in text and "logos_response_validator_v1" in text
    checks.append({"name": "constitution_guardrail_pointer", "ok": marker_ok})

    r = subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", "--input", str(FIXTURE), "--schema", str(SCHEMA)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    checks.append(
        {
            "name": "logos_response_validator_fixture",
            "ok": r.returncode == 0,
            "exit_code": r.returncode,
        }
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.run_logos_llm_distill_citation_lock_v1 import _validate_citations

    orphan = _validate_citations("Jhn.1.1 ok [HYPO] Jhn.9.9 orphan", {"Jhn.1.1"})
    checks.append(
        {
            "name": "orphan_verse_citation_veto",
            "ok": orphan.get("citation_valid") is False and "Jhn.9.9" in (orphan.get("orphan_citations") or []),
        }
    )

    lock = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_llm_distill_citation_lock_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    checks.append(
        {
            "name": "citation_lock_requires_opt_in",
            "ok": lock.returncode == 2,
            "exit_code": lock.returncode,
        }
    )

    doc = {
        "schema": "logos_citation_integrity_smoke_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "checks": checks,
        "ok": all(c.get("ok") for c in checks),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {"out": str(OUT), "ok": doc["ok"]}
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
