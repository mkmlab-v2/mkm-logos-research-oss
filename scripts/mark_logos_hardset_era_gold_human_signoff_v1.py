#!/usr/bin/env python3
"""Mark hardset overrides fixture as commander-signed (does not invent gold rows)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OV = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--overrides-json", type=Path, default=DEFAULT_OV)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument("--force", action="store_true", help="allow even if overrides empty")
    args = ap.parse_args()

    path = args.overrides_json if args.overrides_json.is_absolute() else ROOT / args.overrides_json
    if not path.is_file():
        raise SystemExit(f"missing: {path}")

    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "logos_chronology_hardset_era_gold_overrides_v1":
        raise SystemExit("invalid overrides schema")

    overrides = doc.get("overrides") or []
    if not overrides and not args.force:
        raise SystemExit("overrides empty; fill fixture or run bootstrap_logos_hardset_era_gold_overrides_operator_proxy_v1.py first")

    policy = doc.setdefault("policy", {})
    if not isinstance(policy, dict):
        policy = {}
        doc["policy"] = policy
    policy["human_signoff_completed"] = True
    policy["human_signoff_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    policy["human_signoff_by"] = args.signoff_by

    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "n_overrides": len(overrides), "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
