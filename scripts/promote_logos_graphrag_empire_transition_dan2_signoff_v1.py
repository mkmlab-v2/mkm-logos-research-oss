#!/usr/bin/env python3
"""Human sign-off promotion: Dan.2 trial GraphRAG → SSOT + 6-topic fixture merge [HYPO]."""
from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT / "reports/logos_graphrag_2026_empire_transition_dan2_trial_v1_latest.json"
TARGET = ROOT / "reports/logos_graphrag_2026_empire_transition_dan2_latest.json"
SIGNOFF = ROOT / "reports/logos_graphrag_empire_transition_dan2_promotion_signoff_v1_latest.json"
TOPICS_FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
GOLD_FIXTURE = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"

TOPIC_ENTRY = {
    "topic_id": "empire_transition_dan2",
    "seed_verse_ids": ["Dan.2.10", "Dan.2.31"],
    "graphrag_ref": "reports/logos_graphrag_2026_empire_transition_dan2_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonicalize_promoted(trial: dict[str, Any], ts: str) -> dict[str, Any]:
    out = deepcopy(trial)
    out["generated_at_utc"] = ts
    out.pop("trial_meta", None)
    verse_ids: list[str] = []
    seen: set[str] = set()
    for vid in out.get("verse_ids") or []:
        raw = str(vid)
        canon = raw.replace("aramaic::", "") if raw.startswith("aramaic::") else raw
        if canon and canon not in seen:
            seen.add(canon)
            verse_ids.append(canon)
    for seed in TOPIC_ENTRY["seed_verse_ids"]:
        if seed not in seen:
            seen.add(seed)
            verse_ids.insert(0, seed)
    out["verse_ids"] = verse_ids
    for path in out.get("paths") or []:
        if not isinstance(path, dict):
            continue
        note = str(path.get("note_ko") or "")
        if "human sign-off promoted" not in note:
            path["note_ko"] = f"{note.rstrip()} [HYPO] human sign-off promoted."
    out["promotion_signoff"] = {
        "schema": "logos_graphrag_empire_transition_dan2_promotion_signoff_v1",
        "approved_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gap_closed_seeds": TOPIC_ENTRY["seed_verse_ids"],
        "topic_id": TOPIC_ENTRY["topic_id"],
        "approver": "human_signoff",
        "track_wall": "B_track_not_track_A",
        "source_trial": str(TRIAL.relative_to(ROOT)).replace("\\", "/"),
    }
    return out


def _merge_topics_fixture(ts: str) -> dict[str, Any]:
    fixture = _read(TOPICS_FIXTURE)
    topics = list(fixture.get("topics") or [])
    existing_ids = {str(t.get("topic_id")) for t in topics if isinstance(t, dict)}
    if TOPIC_ENTRY["topic_id"] not in existing_ids:
        topics.append(deepcopy(TOPIC_ENTRY))
    fixture["topics"] = topics
    fixture["generated_at_utc"] = ts
    fixture["note"] = (
        "KOSPI June 6-topic crosswalk + Dan.2 empire_transition (human sign-off merged)."
    )
    return fixture


def _promote_gold_q12(ts: str) -> dict[str, Any]:
    gold = _read(GOLD_FIXTURE)
    items = list(gold.get("items") or [])
    for item in items:
        if str(item.get("id")) != "q12":
            continue
        item["eval_tier"] = "gold_required"
        item["gate"] = {
            "router_path_hit_min": 1,
            "router_verse_hit_min": 1,
            "ann_top8_hit_min": 0,
        }
        item["notes_ko"] = (
            "[HYPO] Dan.2 empire_transition — human sign-off promoted; "
            "gold_required eval; not Track A / live trading trigger."
        )
        item["promotion_signoff_utc"] = ts
        break
    gold["items"] = items
    return gold


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-trial", type=Path, default=TRIAL)
    ap.add_argument("--target-json", type=Path, default=TARGET)
    ap.add_argument("--out-signoff", type=Path, default=SIGNOFF)
    ap.add_argument("--topics-fixture", type=Path, default=TOPICS_FIXTURE)
    ap.add_argument("--gold-fixture", type=Path, default=GOLD_FIXTURE)
    ap.add_argument(
        "--acknowledge",
        action="store_true",
        help="Required once: commander human sign-off for Dan.2 q12 promotion.",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-promote even if signoff exists.")
    args = ap.parse_args()

    ts = _utc_now()
    if args.out_signoff.is_file() and not args.force and not args.dry_run:
        existing = _read(args.out_signoff)
        if existing.get("ok"):
            print(json.dumps({"ok": True, "skipped": True, "signoff": str(args.out_signoff)}))
            return 0

    if not args.acknowledge and not args.dry_run:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing --acknowledge (human sign-off gate for Dan.2 q12)",
                }
            )
        )
        return 2

    trial = _read(args.from_trial)
    if not trial.get("paths"):
        print(json.dumps({"ok": False, "error": f"missing trial graphrag: {args.from_trial}"}))
        return 1

    promoted = _canonicalize_promoted(trial, ts)
    topics = _merge_topics_fixture(ts)
    gold = _promote_gold_q12(ts)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "would_write_target": str(args.target_json),
                    "topic_count": len(topics.get("topics") or []),
                    "q12_eval_tier": "gold_required",
                }
            )
        )
        return 0

    backup = None
    if args.target_json.is_file():
        backup = args.target_json.with_suffix(args.target_json.suffix + ".pre_dan2_promotion.bak")
        shutil.copy2(args.target_json, backup)

    args.target_json.parent.mkdir(parents=True, exist_ok=True)
    args.target_json.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.topics_fixture.write_text(json.dumps(topics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.gold_fixture.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "logos_graphrag_empire_transition_dan2_promotion_signoff_v1",
        "approved_at_utc": ts,
        "ok": True,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "target": str(args.target_json.relative_to(ROOT)).replace("\\", "/"),
        "topics_fixture": str(args.topics_fixture.relative_to(ROOT)).replace("\\", "/"),
        "gold_fixture_q12": "q12 gold_required",
        "backup": str(backup.relative_to(ROOT)).replace("\\", "/") if backup and backup.is_file() else None,
        "gap_closed_seeds": TOPIC_ENTRY["seed_verse_ids"],
    }
    args.out_signoff.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "target": str(args.target_json),
                "signoff": str(args.out_signoff),
                "topics": len(topics.get("topics") or []),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
