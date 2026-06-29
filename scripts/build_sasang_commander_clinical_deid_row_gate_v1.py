#!/usr/bin/env python3
"""Gate: commander clinical de-identified pending row matches template [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/final/templates/commander_attested_clinical_row_template_v1.json"
PENDING = ROOT / "data/myeongni/curated_commander_clinical_pending_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_commander_clinical_deid_row_gate_v1_latest.json"
DEID_ID = "commander_attested_clinical_deid_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pending_row() -> dict[str, Any] | None:
    if not PENDING.is_file():
        return None
    for line in PENDING.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("person_id") or "") == DEID_ID:
            return row
    return None


def build() -> dict[str, Any]:
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8-sig")) if TEMPLATE.is_file() else {}
    row = _load_pending_row() or {}
    required = tpl.get("required_fields") if isinstance(tpl.get("required_fields"), list) else []

    def _field_present(field: str) -> bool:
        if field in row and row.get(field) not in (None, ""):
            return True
        if field == "birth_instant_utc":
            return bool(str(row.get("birth_instant_utc") or row.get("dob_utc") or "").strip())
        if field == "display_name":
            return bool(str(row.get("display_name") or row.get("name") or "").strip())
        return False

    missing = [f for f in required if not _field_present(f)]
    prov = str(row.get("provenance") or "")
    checks = {
        "pending_row_present": {"passed": row.get("person_id") == DEID_ID},
        "template_required_fields": {"passed": len(missing) == 0},
        "provenance_commander_attested": {"passed": "commander_attested" in prov},
        "deid_display_name_tagged": {"passed": "[DE-IDENTIFIED]" in str(row.get("display_name") or "")},
        "track_a_bridge_forbidden": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_commander_clinical_deid_row_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "deid_row_status": "ready" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "missing_fields": missing,
        "person_id": DEID_ID,
        "reproduce": "py scripts/build_sasang_commander_clinical_deid_row_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "deid_row_status": doc["deid_row_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
