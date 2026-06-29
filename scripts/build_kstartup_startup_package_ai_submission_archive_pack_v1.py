#!/usr/bin/env python3
"""340 창업패키지 제출 증거 아카이브 팩 (disk SSOT · 당선 단정 금지)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/kstartup_startup_package_ai_submission_archive_pack_v1_latest.json"
ATTESTATION = ROOT / "reports/kstartup_startup_package_ai_human_gate_attestation_v1.json"
SUBMISSION_GATE = ROOT / "reports/kstartup_startup_package_ai_submission_gate_latest.json"
RECEIPT_DIR = ROOT / "reports/grant_submission_receipts/startup_package_ai_340_20461210"

ARTIFACT_PATHS = [
    "reports/kstartup_startup_package_ai_human_gate_attestation_v1.json",
    "reports/kstartup_startup_package_ai_submission_gate_latest.json",
    "reports/kstartup_startup_package_ai_forbidden_scan_latest.json",
    "reports/kstartup_startup_package_ai_filled_plan_verify_latest.json",
    "reports/kstartup_startup_package_ai_autofill_latest.json",
    "docs/final/artifacts/startup_package_ai_2026_submission_checklist_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate_pass(doc: dict[str, Any], gate_id: str) -> bool:
    gates = doc.get("gates") if isinstance(doc.get("gates"), dict) else {}
    row = gates.get(gate_id) if isinstance(gates.get(gate_id), dict) else {}
    return str(row.get("status") or "").lower() in {"pass", "ready", "done", "confirmed"}


def build_pack() -> dict[str, Any]:
    attest = _read_json(ATTESTATION)
    gate = _read_json(SUBMISSION_GATE)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    receipt_files = sorted(
        p for p in RECEIPT_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".webp"}
    )

    files: list[dict[str, Any]] = []
    for rel in ARTIFACT_PATHS:
        p = ROOT / rel
        files.append({"path": rel, "present": p.is_file(), "sha256": _sha256(p)})

    receipts: list[dict[str, Any]] = []
    for p in receipt_files:
        rel = p.relative_to(ROOT).as_posix()
        receipts.append({"path": rel, "sha256": _sha256(p), "size_bytes": p.stat().st_size})

    g6_ok = _gate_pass(attest, "G6_submitted_complete")
    gate_ok = bool(gate.get("upload_ok")) and bool(gate.get("ready_for_kstartup_upload"))
    core_present = all(row["present"] for row in files[:4])
    archive_ready = g6_ok and gate_ok and core_present

    return {
        "schema": "kstartup_startup_package_ai_submission_archive_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "program": "startup_package_ai_2026_340",
        "pms_task_id": "20461210",
        "host_institution": "서울창조경제혁신센터",
        "archive_ready": archive_ready,
        "g6_submitted_complete": g6_ok,
        "submission_gate_upload_ok": gate_ok,
        "human_receipt_dir": RECEIPT_DIR.relative_to(ROOT).as_posix(),
        "human_receipt_files": receipts,
        "human_receipt_note": (
            "PMS 제출완료 화면 캡처·PDF를 human_receipt_dir에 저장하면 sha256이 여기 집계됩니다."
        ),
        "artifacts": files,
        "boundary_ack": "archive_ready does not imply selection or portal submit proof without human receipt.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 340 submission archive pack JSON.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pack = build_pack()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "archive_ready": pack["archive_ready"], "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if pack["archive_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
