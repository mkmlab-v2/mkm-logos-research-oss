#!/usr/bin/env python3
"""Build Solapi/LMS dry payloads for patient intake SMS — no live API send."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "docs/final/artifacts/patient_intake_notification_templates_v1.json"
GATE = ROOT / "docs/final/artifacts/patient_intake_send_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/patient_intake_solapi_dry_v1_latest.json"

SAMPLE = {
    "intake_url": "https://jema-ai.com/intake",
    "clinic_name": "한의원",
    "intake_pin": "ABC-123",
    "patient_phone": "01012345678",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, value in variables.items():
        out = out.replace("{" + key + "}", value)
    return out


def _solapi_shape(template_key: str, body: str, to: str) -> dict[str, Any]:
    return {
        "message": {
            "to": to,
            "from": "DRY_RUN_FROM",
            "type": "LMS",
            "text": body,
            "subject": f"[DRY] patient_intake:{template_key}",
        }
    }


def build(templates_doc: dict[str, Any], gate_doc: dict[str, Any] | None) -> dict[str, Any]:
    templates = templates_doc.get("templates") or {}
    dry: list[dict[str, Any]] = []
    for key, tpl in sorted(templates.items()):
        body = _render(str(tpl.get("body") or ""), SAMPLE)
        dry.append(
            {
                "template_key": key,
                "channel": tpl.get("channel", "sms_lms"),
                "resolved_body": body,
                "solapi_request_shape": _solapi_shape(key, body, "DRY_RUN_TO"),
            }
        )

    send_gate = (gate_doc or {}).get("send_gate", "HOLD")
    ready_internal = bool((gate_doc or {}).get("ready_internal_poc"))
    return {
        "schema": "patient_intake_solapi_dry_v1",
        "generated_at_utc": _utc(),
        "lane": "internal_poc",
        "send_gate": send_gate,
        "ready_internal_poc": ready_internal,
        "live_send": False,
        "ready_for_external_send": False,
        "templates_pointer": str(TEMPLATES.relative_to(ROOT)).replace("\\", "/"),
        "gate_pointer": str(GATE.relative_to(ROOT)).replace("\\", "/"),
        "sample_variables": SAMPLE,
        "templates_dry": dry,
        "ok": all(t["resolved_body"].strip() for t in dry),
        "reproduce": "py scripts/build_patient_intake_solapi_dry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not TEMPLATES.is_file():
        print(json.dumps({"ok": False, "error": f"missing {TEMPLATES}"}))
        return 2

    gate_doc = json.loads(GATE.read_text(encoding="utf-8")) if GATE.is_file() else None
    doc = build(json.loads(TEMPLATES.read_text(encoding="utf-8")), gate_doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.out), "send_gate": doc["send_gate"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
