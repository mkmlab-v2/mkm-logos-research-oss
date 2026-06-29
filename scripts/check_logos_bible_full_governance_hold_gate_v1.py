#!/usr/bin/env python3
"""Gate: Logos bible_full artifacts must stay research_only + send_gate HOLD (no Track A)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_bible_full_governance_hold_gate_v1_latest.json"

REQUIRED_PATHS = [
    ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_studio_dynamic_subgraph_router_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()
    failures: list[str] = []

    for path in REQUIRED_PATHS:
        if not path.is_file():
            failures.append(f"missing:{path.name}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if doc.get("research_only") is not True:
            failures.append(f"research_only_false:{path.name}")
        if doc.get("send_gate") != "HOLD":
            failures.append(f"send_gate_not_hold:{path.name}")
        if doc.get("track_a_auto_promote") is True:
            failures.append(f"track_a_auto_promote:{path.name}")

    audit = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
    if audit.is_file():
        wall = json.loads(audit.read_text(encoding="utf-8-sig")).get("track_wall") or {}
        if wall.get("track_a_auto_promote") is True:
            failures.append("audit_track_a_auto_promote")

    doc = {
        "schema": "logos_bible_full_governance_hold_gate_v1",
        "generated_at_utc": _utc(),
        "ok": len(failures) == 0,
        "failures": failures,
        "reproduce": "py scripts/check_logos_bible_full_governance_hold_gate_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failures": failures, "out": str(OUT)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
