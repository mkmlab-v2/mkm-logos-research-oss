#!/usr/bin/env python3
"""Record commander-direct signoff on thematic gold (B-track; not Track A / live trading)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/logos_rag_gold_commander_signoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--signoff-by", default="commander")
    args = ap.parse_args()

    gold = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    gold["status"] = "commander_direct_signoff_v1"
    gold["signoff"] = "commander_direct_v1"
    gold["signoff_lane"] = "commander_direct_v1"
    gold["updated_at_utc"] = _utc_now()
    gold["note"] = (
        (gold.get("note") or "")
        + " Commander-direct thematic gold ack (B-track); q01 theology_primary union excluded."
    ).strip()
    args.gold_json.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "logos_rag_gold_commander_signoff_v1",
        "signoff_utc": _utc_now(),
        "signoff_by": args.signoff_by,
        "signoff_lane": "commander_direct_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "thematic_n": sum(
            1
            for it in gold.get("items") or []
            if isinstance(it, dict) and (it.get("gold_verse_ids_human") or [])
        ),
        "q01_theology_primary": True,
        "note": "Direct commander ack on gold human JSON; distinct from btrack_operator_proxy_ack on bridges.",
    }
    args.signoff_json.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_json.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "signoff_lane": "commander_direct_v1"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
