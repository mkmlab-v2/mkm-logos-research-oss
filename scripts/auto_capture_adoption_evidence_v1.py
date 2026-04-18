# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.92, L:0.90, K:0.39, M:0.68}
# Balance: 94
# Purpose: Auto-confirm adoption evidence when files exist in evidence folder.
# Keywords: automation, evidence, adoption, confirm, track-a
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "docs/final/evidence"
LATEST_PATH = ROOT / "docs/final/artifacts/adoption_evidence_capture_latest.json"
LOG_PATH = ROOT / "docs/final/artifacts/adoption_evidence_capture_auto_log_v1.json"

# Recommended: <event_prefix>_<YYYY-MM-DD>.<ext> e.g. submission_receipt_2026-04-17.png
_PREFIXES = ("submission_receipt_", "screening_pass_", "meeting_confirmed_")
_DATE_IN_NAME = re.compile(r"(19|20)\d{2}-\d{2}-\d{2}")
_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".pdf", ".eml", ".msg", ".txt", ".html"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_filename(path: Path) -> dict[str, Any]:
    stem = path.stem.lower()
    reasons: list[str] = []
    ok = True
    if not any(stem.startswith(p) for p in _PREFIXES):
        ok = False
        reasons.append(f"must start with one of: {', '.join(_PREFIXES)}")
    if path.suffix.lower() not in _ALLOWED_EXT:
        ok = False
        reasons.append(f"extension should be one of: {sorted(_ALLOWED_EXT)}")
    if ok and not _DATE_IN_NAME.search(stem):
        reasons.append("optional: embed YYYY-MM-DD in filename for audit trail")
    return {"path": str(path), "ok": ok, "reasons": reasons}


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-capture adoption evidence from evidence folder")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Do not CONFIRM unless every file passes naming convention (prefix + allowed ext).",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="CI: validate naming only (no JSON writes). Exit 1 if any evidence file fails convention.",
    )
    args = ap.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in EVIDENCE_DIR.glob("*") if p.is_file()], key=lambda p: p.name.lower())
    files_rel = [str(p.relative_to(ROOT)).replace("\\", "/") for p in files]
    checks = [_validate_filename(p) for p in files]
    all_names_ok: bool | None = all(c["ok"] for c in checks) if checks else None
    any_name_fail = any(not c["ok"] for c in checks)

    if args.check:
        payload = {
            "schema": "adoption_evidence_naming_check_v1",
            "generated_at_utc": _utc_now(),
            "repo_root": str(ROOT),
            "naming_convention": {
                "prefixes": list(_PREFIXES),
                "allowed_extensions": sorted(_ALLOWED_EXT),
                "example": "submission_receipt_2026-04-17.png",
            },
            "naming_validation": checks,
            "evidence_file_count": len(files_rel),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if files_rel and any_name_fail:
            return 1
        return 0

    latest = _load(LATEST_PATH)

    changed = False
    if files_rel:
        if args.strict and any_name_fail:
            latest["status"] = "PENDING_RENAME"
            latest["acceptance_gate_result"] = "FAIL_NAMING_STRICT"
            latest["operator_note"] = (
                "Evidence files present but naming convention failed (--strict). "
                "Rename to e.g. submission_receipt_2026-04-17.png and rerun."
            )
            latest["evidence_file_paths"] = files_rel
            latest["naming_convention_hint"] = (
                "Use prefix submission_receipt_ | screening_pass_ | meeting_confirmed_ "
                "plus optional _YYYY-MM-DD before extension."
            )
        else:
            latest["status"] = "CONFIRMED"
            latest["event_type"] = latest.get("event_type") or "submission_receipt"
            latest["organization_name"] = latest.get("organization_name") or "LG Electronics HS"
            latest["program_name"] = latest.get("program_name") or "초격차 스타트업 프로젝트"
            latest["captured_at_utc"] = _utc_now()
            latest["evidence_channel"] = latest.get("evidence_channel") or "official_doc"
            latest["evidence_summary"] = latest.get("evidence_summary") or "Auto-captured from evidence folder."
            latest["evidence_file_paths"] = files_rel
            latest["operator_note"] = "Auto-confirmed by auto_capture_adoption_evidence_v1.py"
            if any_name_fail and not args.strict:
                latest["acceptance_gate_result"] = "PASS_WITH_NAMING_WARNINGS"
                latest["operator_note"] += " Some files did not match recommended naming; see auto_log naming_validation."
            else:
                latest["acceptance_gate_result"] = "PASS"
        changed = True
    else:
        latest["status"] = "PENDING_CAPTURE"
        latest["acceptance_gate_result"] = "WAITING_EVIDENCE_FILES"
        latest["operator_note"] = (
            "No files in docs/final/evidence yet. Drop official proof files and rerun this script."
        )
        changed = True

    if changed:
        _write(LATEST_PATH, latest)

    log = {
        "schema": "adoption_evidence_capture_auto_log_v1",
        "generated_at_utc": _utc_now(),
        "strict_mode": bool(args.strict),
        "naming_convention": {
            "prefixes": list(_PREFIXES),
            "allowed_extensions": sorted(_ALLOWED_EXT),
            "example": "submission_receipt_2026-04-17.png",
        },
        "naming_validation": checks,
        "all_names_ok": all_names_ok,
        "evidence_file_count": len(files_rel),
        "evidence_file_paths": files_rel,
        "latest_status": latest.get("status"),
        "latest_path": str(LATEST_PATH),
    }
    _write(LOG_PATH, log)
    print(str(LOG_PATH))
    print(str(LATEST_PATH))
    if args.strict and files_rel and any_name_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
