#!/usr/bin/env python3
"""Build human-audit packet from current approved Layer5 goldset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDSET = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_v1_latest.jsonl"
DEFAULT_PACKET = ROOT / "docs" / "final" / "artifacts" / "layer5_human_audit_packet_latest.json"
DEFAULT_REVIEW_CSV = ROOT / "docs" / "final" / "artifacts" / "layer5_human_audit_review_template_v1.csv"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goldset-jsonl", type=Path, default=DEFAULT_GOLDSET)
    ap.add_argument("--packet-json", type=Path, default=DEFAULT_PACKET)
    ap.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    args = ap.parse_args()

    rows = _read_jsonl(args.goldset_jsonl)
    cases: list[dict[str, Any]] = []
    for row in rows:
        cid = str(row.get("case_id") or "")
        if not cid:
            continue
        cases.append(
            {
                "case_id": cid,
                "expected_block": bool(row.get("expected_block")),
                "expected_reasons": row.get("expected_reasons") if isinstance(row.get("expected_reasons"), list) else [],
                "review_status": str(row.get("review_status", "approved")),
                "source_file": row.get("source_file"),
                "source_line": row.get("source_line"),
            }
        )

    packet = {
        "schema": "layer5_human_audit_packet_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "goldset_jsonl": str(args.goldset_jsonl).replace("\\", "/"),
        },
        "case_count": len(cases),
        "cases": cases,
        "instructions": [
            "Fill review CSV with audit_decision=approve|reject for each case_id.",
            "Use notes column for rationale when rejecting.",
            "After editing CSV, run apply_layer5_human_audit_v1.py to update statuses and rerun gates.",
        ],
    }
    args.packet_json.parent.mkdir(parents=True, exist_ok=True)
    args.packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.review_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.review_csv.open("w", encoding="utf-8", newline="") as fh:
        fh.write("case_id,audit_decision,notes\n")
        for case in cases:
            fh.write(f"{case['case_id']},approve,\n")

    print(json.dumps({"ok": True, "packet_json": str(args.packet_json), "review_csv": str(args.review_csv), "case_count": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
