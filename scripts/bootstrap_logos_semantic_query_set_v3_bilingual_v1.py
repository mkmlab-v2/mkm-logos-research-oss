#!/usr/bin/env python3
"""Materialize logos_semantic_query_set_v3_bilingual_v1.json from v3 EN + v4 KO map."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_logos_rag_retrieval_round_v1 import _load_queries  # noqa: E402

DEFAULT_V3 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v3-json", type=Path, default=DEFAULT_V3)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    en_list = _load_queries(args.v3_json)
    v4 = json.loads(args.v4_json.read_text(encoding="utf-8-sig"))
    ko_by_en: dict[str, dict[str, Any]] = {}
    for it in v4.get("items") or []:
        if not isinstance(it, dict):
            continue
        en = str(it.get("query_en") or "").strip()
        if en:
            ko_by_en[en] = it

    items: list[dict[str, Any]] = []
    missing: list[str] = []
    for i, en in enumerate(en_list, start=1):
        src = ko_by_en.get(en)
        if not src:
            missing.append(en)
            continue
        items.append(
            {
                "id": f"q{i:02d}",
                "query_en": en,
                "query_ko": str(src.get("query_ko") or "").strip(),
                "gold_verse_ids_weak": list(src.get("gold_verse_ids_weak") or []),
                "gold_note": src.get("gold_note")
                or "[HYPO] thematic weak labels — paired from v4; not human adjudication",
            }
        )

    doc = {
        "schema": "logos_semantic_query_set_v3_bilingual_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "ts_utc": _utc_now(),
        "paired_with": str(args.v3_json.relative_to(ROOT)).replace("\\", "/"),
        "ko_source": str(args.v4_json.relative_to(ROOT)).replace("\\", "/"),
        "note": "v3 EN probes with embedded query_ko (v4 gloss). Default pilot route ko_only.",
        "items": items,
        "legacy_queries_en": en_list,
        "legacy_queries_ko": [it["query_ko"] for it in items],
    }
    if missing:
        doc["missing_en"] = missing

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": len(missing) == 0,
                "output": str(args.output_json),
                "items": len(items),
                "missing": len(missing),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
