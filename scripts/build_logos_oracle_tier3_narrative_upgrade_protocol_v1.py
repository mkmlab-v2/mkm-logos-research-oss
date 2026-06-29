#!/usr/bin/env python3
"""Build Oracle Logos Tier-3 narrative upgrade protocol SSOT ([HYPO] / B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"

from logos_oracle_tier3_narrative_upgrade_lib_v1 import build_protocol_document  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    doc = build_protocol_document(root=args.workspace_root.resolve())
    doc["generated_at_utc"] = _utc_now()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    released = sum(1 for b in doc["blocker_release_matrix"] if b["released"])
    print(f"WROTE: {args.out}")
    print(
        f"tier3_constitution_narrative_full_upgrade_ready="
        f"{doc['tier3_constitution_narrative_full_upgrade_ready']} blockers={released}/4"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
