#!/usr/bin/env python3
"""Readiness for concept_bridge human signoff (B-track)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_concept_bridge_signoff_readiness_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    reg = json.loads(args.registry_json.read_text(encoding="utf-8-sig"))
    entries = [e for e in reg.get("entries") or [] if isinstance(e, dict) and e.get("present")]
    signed = sum(1 for e in entries if e.get("human_reviewed"))
    doc = {
        "schema": "logos_concept_bridge_signoff_readiness_v1",
        "bridge_count": len(entries),
        "human_reviewed_count": signed,
        "ready_for_btrack_operator_proxy_ack": len(entries) >= 2 and signed == 0,
        "blockers": [] if signed else ["awaiting_human_or_btrack_operator_proxy_ack"],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "signed": signed, "total": len(entries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
