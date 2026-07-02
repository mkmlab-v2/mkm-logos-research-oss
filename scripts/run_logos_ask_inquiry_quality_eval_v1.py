#!/usr/bin/env python3
"""Ask inquiry_report_v1 quality eval — hub match, topic mismatch rate, stub route detection."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_golden_200_anchor_registry_v1 import build_registry
from scripts.logos_studio_query_topic_guard_v1 import detect_query_topic_mismatch, query_flags

DEFAULT_FIXTURE = ROOT / "docs/final/fixtures/logos_ask_inquiry_gold_eval_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_ask_inquiry_quality_eval_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/logos_ask_inquiry_quality_eval_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def match_hub(query: str, registry: dict[str, Any]) -> str | None:
    q = _norm(query)
    best_id: str | None = None
    best_score = 0
    for entry in registry.get("entries") or []:
        score = 0
        for marker in entry.get("query_markers_ko") or []:
            m = _norm(marker)
            if len(m) >= 2 and m in q:
                score += 2
        if entry.get("hub_id") == "gen2_eve_creation":
            if any(x in q for x in ("네피림", "nephilim", "genesis 6", "gen 6")):
                score = 0
        if score > best_score:
            best_score = score
            best_id = str(entry.get("hub_id"))
    return best_id if best_score >= 2 else None


def eval_item(item: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    query = str(item.get("query_ko") or "")
    stub_refs = list(item.get("stub_path_verse_refs") or [])
    preset_id = item.get("stub_preset_id")
    conflict = None
    if item.get("conflict_group_id"):
        conflict = {
            "groups": [
                {
                    "conflict_group_id": item["conflict_group_id"],
                    "schools": [{"verse_refs": stub_refs}],
                }
            ]
        }
    path = {"verse_refs": stub_refs, "steps": []}
    mismatch = detect_query_topic_mismatch(
        query,
        conflict=conflict,
        path=path,
        preset_id=str(preset_id) if preset_id else None,
    )
    hub_id = match_hub(query, registry)
    flags = query_flags(query)
    expect_mismatch = bool(item.get("expect_mismatch_on_stub_path"))
    mismatch_ok = bool(mismatch) == expect_mismatch
    hub_ok = (item.get("matched_hub_id") is None and hub_id is None) or (
        item.get("matched_hub_id") == hub_id
    )
    return {
        "id": item.get("id"),
        "query_ko": query,
        "matched_hub_id": hub_id,
        "expected_hub_id": item.get("matched_hub_id"),
        "hub_match_ok": hub_ok,
        "topic_mismatch_detected": bool(mismatch),
        "mismatch_code": (mismatch or {}).get("code"),
        "expect_mismatch_on_stub_path": expect_mismatch,
        "mismatch_expect_ok": mismatch_ok,
        "query_flags": flags,
        "pass": hub_ok and mismatch_ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    args = ap.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8-sig"))
    registry = build_registry()
    rows = [eval_item(item, registry) for item in fixture.get("items") or []]
    passed = sum(1 for r in rows if r.get("pass"))
    mismatch_cases = [r for r in rows if r.get("expect_mismatch_on_stub_path")]
    mismatch_hits = sum(1 for r in mismatch_cases if r.get("topic_mismatch_detected"))
    mismatch_rate = (
        round(mismatch_hits / len(mismatch_cases), 4) if mismatch_cases else None
    )

    report = {
        "schema": "logos_ask_inquiry_quality_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "non_gating": True,
        "fixture": str(args.fixture.relative_to(ROOT)).replace("\\", "/"),
        "items_total": len(rows),
        "items_passed": passed,
        "topic_mismatch_rate_on_stub_paths": mismatch_rate,
        "topic_mismatch_cases": len(mismatch_cases),
        "topic_mismatch_hits": mismatch_hits,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    jsonl_row = {
        "ts_utc": _utc(),
        "items_passed": passed,
        "items_total": len(rows),
        "topic_mismatch_rate": mismatch_rate,
        "failed_ids": [r["id"] for r in rows if not r.get("pass")],
    }
    with args.jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(jsonl_row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": passed == len(rows),
                "passed": passed,
                "total": len(rows),
                "mismatch_rate": mismatch_rate,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
