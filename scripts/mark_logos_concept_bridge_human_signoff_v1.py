#!/usr/bin/env python3
"""Mark concept_bridge artifacts commander/operator signed ([HYPO] B-track only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument(
        "--btrack-operator-proxy-ack",
        action="store_true",
        help="B-track research ack only; not live trading or Track A promotion",
    )
    ap.add_argument(
        "--commander-direct-signoff",
        action="store_true",
        help="Commander-direct lane label (still B-track; not Track A promotion)",
    )
    args = ap.parse_args()

    if not args.btrack_operator_proxy_ack and not args.commander_direct_signoff:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "requires --btrack-operator-proxy-ack or --commander-direct-signoff",
                },
                ensure_ascii=False,
            )
        )
        return 2

    signoff_lane = (
        "commander_direct_v1" if args.commander_direct_signoff else "btrack_operator_proxy_ack"
    )

    reg = json.loads(args.registry_json.read_text(encoding="utf-8-sig"))
    updated: list[str] = []
    for entry in reg.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        policy = doc.setdefault("policy", {})
        if not isinstance(policy, dict):
            policy = {}
            doc["policy"] = policy
        policy["human_signoff_completed"] = True
        policy["human_reviewed"] = True
        policy["human_signoff_utc"] = _utc_now()
        policy["human_signoff_by"] = args.signoff_by
        policy["signoff_lane"] = signoff_lane
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated.append(rel)

    reg["human_reviewed_count"] = len(updated)
    n = len([e for e in reg.get("entries") or [] if isinstance(e, dict) and e.get("present")])
    reg["human_reviewed_ratio"] = round(reg["human_reviewed_count"] / n, 4) if n else 0.0
    reg["governance_warning_zero_human"] = reg["human_reviewed_count"] == 0
    reg["updated_at_utc"] = _utc_now()
    args.registry_json.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "updated": len(updated)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
