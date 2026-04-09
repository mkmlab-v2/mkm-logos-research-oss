#!/usr/bin/env python3
"""Operational readiness check for recovered codebook assets.

Readiness is PASS only when all required gates pass:
1) recovered asset integrity report is ok
2) normalized recovered codebook exists and schema-valid
3) core fact-safe bundle passes
4) normalized artifact has minimum lookup entries and governance defaults
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ART_DIR = ROOT / "docs" / "final" / "artifacts"

RECOVERED_VALIDATION = ART_DIR / "recovered_codepack_validation_latest.json"
NORMALIZED = ART_DIR / "normalized_recovered_codebook_latest.json"
OUT = ART_DIR / "recovered_codebook_operational_readiness_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict[str, Any]] = []

    # 0) Re-run recovered validation to avoid stale state.
    rc, out = _run(["py", "scripts/experimental/codepack_recovery/validate_recovered_codepack.py"])
    checks.append(
        {
            "id": "recovered_validation_refresh",
            "pass": rc == 0,
            "exit_code": rc,
            "output_preview": out[:400],
        }
    )

    # 1) Rebuild normalized artifact.
    rc, out = _run(["py", "scripts/experimental/codepack_recovery/build_normalized_recovered_codebook.py"])
    checks.append(
        {
            "id": "normalized_rebuild",
            "pass": rc == 0,
            "exit_code": rc,
            "output_preview": out[:400],
        }
    )

    # 2) Schema validation for normalized artifact.
    rc, out = _run(
        [
            "py",
            "scripts/validate_master_codebook_schema.py",
            "--instance",
            "docs/final/artifacts/normalized_recovered_codebook_latest.json",
        ]
    )
    checks.append(
        {
            "id": "normalized_schema_validation",
            "pass": rc == 0,
            "exit_code": rc,
            "output_preview": out[:400],
        }
    )

    # 3) Core fact-safe bundle.
    rc, out = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/run_codebook_factsafe_bundle.ps1"])
    checks.append(
        {
            "id": "codebook_factsafe_bundle",
            "pass": rc == 0,
            "exit_code": rc,
            "output_preview": out[:500],
        }
    )

    # 4) Semantic sanity checks on normalized artifact.
    semantic_pass = False
    semantic_detail: dict[str, Any] = {"reason": "normalized_artifact_missing"}
    if NORMALIZED.is_file():
        try:
            doc = _load_json(NORMALIZED)
            entries = (((doc.get("lookup") or {}).get("entries")) or [])
            gov = doc.get("governance") or {}
            semantic_pass = (
                isinstance(entries, list)
                and len(entries) >= 20
                and gov.get("literal_restoration_rate_required") == 100.0
                and gov.get("off_by_default_policy") is True
            )
            semantic_detail = {
                "lookup_entry_count": len(entries) if isinstance(entries, list) else None,
                "literal_restoration_rate_required": gov.get("literal_restoration_rate_required"),
                "off_by_default_policy": gov.get("off_by_default_policy"),
            }
        except Exception as exc:  # pragma: no cover
            semantic_detail = {"reason": f"parse_error: {exc}"}
    checks.append(
        {
            "id": "normalized_semantic_sanity",
            "pass": semantic_pass,
            "detail": semantic_detail,
        }
    )

    # 5) Recovered integrity artifact sanity.
    recovered_pass = False
    recovered_detail: dict[str, Any] = {"reason": "missing_recovered_validation_artifact"}
    if RECOVERED_VALIDATION.is_file():
        try:
            rec = _load_json(RECOVERED_VALIDATION)
            counts = rec.get("counts") or {}
            recovered_pass = (
                rec.get("ok") is True
                and counts.get("code_present") == counts.get("code_required")
                and counts.get("json_valid") == counts.get("json_required")
            )
            recovered_detail = {
                "ok": rec.get("ok"),
                "counts": counts,
            }
        except Exception as exc:  # pragma: no cover
            recovered_detail = {"reason": f"parse_error: {exc}"}
    checks.append(
        {
            "id": "recovered_integrity_sanity",
            "pass": recovered_pass,
            "detail": recovered_detail,
        }
    )

    decision = "PASS" if all(bool(c.get("pass")) for c in checks) else "FAIL"
    report = {
        "schema": "recovered_codebook_operational_readiness_v1",
        "generated_at_utc": _utc_now(),
        "decision": decision,
        "checks": checks,
        "fact_safe_note": "PASS means gate readiness only, not automatic production promotion.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "out": str(OUT)}, ensure_ascii=False))
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

