#!/usr/bin/env python3
"""Merge docs/final/fixtures magic_orb queries into mkmlife public JSON (consumer fields preserved)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_queries_v1.json"

CONSUMER_LABELS = {
    "job_suffering_reason": "고난·해석 경로를 나란히 관측하기",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=FIXTURE)
    ap.add_argument("--public-json", type=Path, default=PUBLIC)
    args = ap.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    public_path = args.public_json
    public = (
        json.loads(public_path.read_text(encoding="utf-8"))
        if public_path.is_file()
        else {"schema": "magic_orb_question_insight_queries_v1", "items": []}
    )

    by_id = {str(it.get("id")): it for it in public.get("items") or [] if isinstance(it, dict)}
    for row in fixture.get("items") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        qid = str(row["id"])
        merged = {**by_id.get(qid, {}), **row}
        label = CONSUMER_LABELS.get(qid)
        if label:
            merged["consumer_query_ko"] = label
            merged.setdefault(
                "consumer_facade",
                {
                    "schema": "saving_the_news_public_copy_facade_v1",
                    "version": "1.0.0",
                    "display_field": "consumer_query_ko",
                    "api_field": "query_ko",
                },
            )
        by_id[qid] = merged

    out = {
        **public,
        "schema": fixture.get("schema") or public.get("schema"),
        "hypothesis_tier": fixture.get("hypothesis_tier", "B"),
        "research_only": True,
        "non_gating": True,
        "items": list(by_id.values()),
    }
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(public_path), "items": len(out["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
