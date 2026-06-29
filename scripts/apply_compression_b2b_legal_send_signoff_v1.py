#!/usr/bin/env python3
"""Record compression B2B legal/send sign-off state (commander + optional counsel)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
READINESS = ROOT / "reports/compression_enterprise_summary_readiness_v1_latest.json"
ROI_REPORT = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def apply(*, commander_ack: bool, counsel_ack: bool, note: str) -> dict[str, Any]:
    roi = _load(ROI_REPORT)
    measured = (roi.get("measured_proxy") or {}).get("case_count")
    external_ok = commander_ack and counsel_ack and bool(measured)
    doc = {
        "schema": "compression_b2b_legal_send_signoff_v1",
        "generated_at_utc": _utc(),
        "commander_signoff": commander_ack,
        "counsel_signoff": counsel_ack,
        "rq009_alignment": "counsel_required_for_external_send",
        "send_gate": "OPEN" if external_ok else "HOLD",
        "ready_for_external_send": external_ok,
        "ready_for_internal_rehearsal_materials": commander_ack,
        "pilot_roi_report": ROI_REPORT.relative_to(ROOT).as_posix() if ROI_REPORT.is_file() else None,
        "note": note,
        "boundary_ack": (
            "Commander chat pre-approval does not replace counsel for press/case-study SEND. "
            "Dollar/KRW ROI remains null until customer-masked corpus + audit."
        ),
    }
    OUT_DEFAULT.parent.mkdir(parents=True, exist_ok=True)
    OUT_DEFAULT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readiness = _load(READINESS)
    if readiness:
        readiness["generated_at_utc"] = _utc()
        readiness["ready_for_external_send"] = external_ok
        readiness["legal_send_signoff"] = OUT_DEFAULT.relative_to(ROOT).as_posix()
        readiness["send_gate"] = doc["send_gate"]
        if not counsel_ack:
            readiness["note"] = (
                "Commander pre-approval recorded; counsel_signoff false — external send HOLD (RQ-009)."
            )
        READINESS.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commander-acknowledge", action="store_true")
    ap.add_argument("--counsel-acknowledge", action="store_true")
    ap.add_argument("--note", default="commander chat pre-approval 2026-06-10")
    args = ap.parse_args()
    if not args.commander_acknowledge and not args.counsel_acknowledge:
        print(json.dumps({"ok": False, "error": "pass --commander-acknowledge and/or --counsel-acknowledge"}))
        return 1
    doc = apply(
        commander_ack=args.commander_acknowledge,
        counsel_ack=args.counsel_acknowledge,
        note=args.note,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "send_gate": doc["send_gate"],
                "ready_for_external_send": doc["ready_for_external_send"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
