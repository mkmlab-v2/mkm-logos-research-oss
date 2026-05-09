#!/usr/bin/env python3
"""Build three-lens DNA bridge evidence artifact from approved DNA report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "bio_dna_constitution_final_approval_latest.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "dna_training_bridge_evidence_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if not SRC.is_file():
        raise SystemExit(f"Missing source: {SRC}")
    src_doc = _read_json(SRC)
    payload = {
        "schema": "dna_training_bridge_evidence_v1",
        "generated_at_utc": _now(),
        "source_report_path": str(SRC),
        "source_report_exists": True,
        "source_report_schema": src_doc.get("schema"),
        "research_only": True,
        "human_signoff_required": True,
        "bridge_status": "evidence_bound",
        "notes": [
            "This artifact binds approved DNA report evidence to three-lens staged bridge.",
            "No direct live trigger is enabled by this bridge.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
