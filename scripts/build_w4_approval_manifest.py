#!/usr/bin/env python3
"""Build integrity manifest for W4 approval packet files."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "W4_APPROVAL_PACKET_MANIFEST_V1.json"

PACKET_FILES = [
    "W4_PROMOTION_DECISION_FINAL.md",
    "W4_PROMOTION_DECISION_DRAFT.json",
    "W4_APPROVAL_PACKET_INDEX_V1.md",
    "W3_MULTI_BATCH_STABILITY_SUMMARY_V1.json",
    "W3_GATE_THRESHOLD_SWEEP_V1.json",
    "W3_K_SWEEP_500_1000_2000_V1.json",
    "W3_RESONANCE_BATCH_RESULT_V4.json",
    "W3_RESONANCE_COMPUTE_SPEC_V1.json",
    "W2_GATE_READINESS_NOTE.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    rows = []
    for name in PACKET_FILES:
        p = ART / name
        exists = p.is_file()
        rows.append(
            {
                "file": f"docs/final/artifacts/{name}",
                "exists": exists,
                "size_bytes": p.stat().st_size if exists else None,
                "sha256": _sha256(p) if exists else None,
            }
        )

    out = {
        "schema": "w4_approval_packet_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "packet_root": "docs/final/artifacts",
        "required_files_count": len(PACKET_FILES),
        "all_required_files_exist": all(r["exists"] for r in rows),
        "files": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: approval packet manifest generated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
