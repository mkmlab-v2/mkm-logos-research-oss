#!/usr/bin/env python3
"""Gate for commander-attested clinical row human-gate template [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/final/templates/commander_attested_clinical_row_template_v1.json"
OUT = ROOT / "docs/final/artifacts/sasang_commander_attested_clinical_template_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    if not TEMPLATE.is_file():
        doc = {
            "schema": "sasang_commander_attested_clinical_template_gate_v1",
            "gate_ok": False,
            "template_status": "missing",
        }
        return doc

    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8-sig"))
    required = tpl.get("required_fields") if isinstance(tpl.get("required_fields"), list) else []
    example = tpl.get("example_row") if isinstance(tpl.get("example_row"), dict) else {}
    policy = tpl.get("promotion_policy") if isinstance(tpl.get("promotion_policy"), dict) else {}

    missing = [f for f in required if f not in example]
    checks = {
        "template_schema_ok": {"passed": tpl.get("schema") == "commander_attested_clinical_row_template_v1"},
        "human_gate_required": {"passed": tpl.get("human_gate_required") is True},
        "example_has_required_fields": {"passed": len(missing) == 0},
        "send_gate_hold": {"passed": policy.get("send_gate") == "HOLD"},
        "track_a_bridge_forbidden": {"passed": policy.get("track_a_bridge") is False},
        "auto_ingest_forbidden": {"passed": policy.get("auto_ingest") is False},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_commander_attested_clinical_template_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "template_path": str(TEMPLATE).replace("\\", "/"),
        "template_status": "ready" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "missing_example_fields": missing,
        "reproduce": "py scripts/build_sasang_commander_attested_clinical_template_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "template_status": doc.get("template_status")}))
    return 0 if doc.get("gate_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
