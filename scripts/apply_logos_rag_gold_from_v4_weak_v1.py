#!/usr/bin/env python3
"""Fill human gold from v4 weak_gold [HYPO] for parallel L2 eval (commander-delegated)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    args = ap.parse_args()

    v4 = json.loads(args.v4_json.read_text(encoding="utf-8-sig"))
    weak_by_id = {
        str(x["id"]): list(x.get("gold_verse_ids_weak") or [])
        for x in v4.get("items") or []
        if isinstance(x, dict) and x.get("id")
    }
    gold = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    n = 0
    for it in gold.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        wg = weak_by_id.get(qid) or []
        if not wg:
            continue
        it["gold_verse_ids_human"] = wg
        it["adjudication_status"] = "commander_signed_v1"
        it["adjudication_note"] = "Delegated: v4 gold_verse_ids_weak [HYPO] for L2 parallel eval."
        n += 1
    gold["status"] = "commander_weak_gold_proxy_v1"
    gold["note"] = "[HYPO] weak thematic gold from v4; not adjudicated verse labels."
    gold["updated_at_utc"] = _utc_now()
    args.gold_json.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "filled": n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
