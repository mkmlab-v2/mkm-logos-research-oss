#!/usr/bin/env python3
"""Gate: Logos Studio conflict retrieval quality grid (Phase 1b).

Reproduce:
  py scripts/check_logos_studio_conflict_retrieval_gate_v1.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.retrieve_logos_studio_conflict_context_v1 import retrieve_conflict_context  # noqa: E402

OUT = ROOT / "docs/final/artifacts/logos_studio_conflict_retrieval_gate_v1_latest.json"

CASES: list[dict[str, Any]] = [
    {
        "id": "nephilim_ko",
        "query": "네피림이 뭐야?",
        "preset_id": None,
        "expect_groups": ["MKM_CONCEPT_NEPHILIM"],
        "forbid_groups": ["MKM_CONCEPT_SONS_OF_GOD"],
    },
    {
        "id": "benei_en",
        "query": "Benei HaElohim sons of God Genesis 6",
        "preset_id": None,
        "expect_groups": ["MKM_CONCEPT_SONS_OF_GOD"],
        "forbid_groups": [],
    },
    {
        "id": "watchers_ko",
        "query": "감시자 watchers 타락 천사",
        "preset_id": None,
        "expect_groups": ["MKM_CONCEPT_NEPHILIM"],
        "forbid_groups": [],
    },
    {
        "id": "job_suffering_positive",
        "query": "욥기에서 하나님은 왜 욥이 고통받게 하셨는가?",
        "preset_id": "job_job_suffering_reason",
        "expect_groups": ["MKM_CONCEPT_JOB_SUFFERING"],
        "match_mode": "preset_boost",
        "forbid_groups": ["MKM_CONCEPT_SONS_OF_GOD", "MKM_CONCEPT_NEPHILIM"],
    },
    {
        "id": "job_suffering_freeform",
        "query": "욥의 고난의 이유는?",
        "preset_id": None,
        "expect_groups": ["MKM_CONCEPT_JOB_SUFFERING"],
        "forbid_groups": ["MKM_CONCEPT_NEPHILIM"],
    },
    {
        "id": "preset_boost_nephilim",
        "query": "고대 전통",
        "preset_id": "bigset_topic_nephilim",
        "expect_groups": ["MKM_CONCEPT_NEPHILIM"],
        "match_mode": "preset_boost",
        "forbid_groups": [],
    },
    {
        "id": "hope_psalm_negative",
        "query": "소망과 인내 시편",
        "preset_id": "era_genesis_order_and_fall",
        "expect_groups": [],
        "forbid_groups": ["MKM_CONCEPT_NEPHILIM"],
    },
    {
        "id": "isaiah_youtube_spine_positive",
        "query": "이사야 66장 spine",
        "preset_id": "isaiah_youtube_spine_v1",
        "expect_groups": ["MKM_CONCEPT_ISAIAH_YOUTUBE"],
        "match_mode": "preset_boost",
        "forbid_groups": ["MKM_CONCEPT_NEPHILIM"],
    },
    {
        "id": "isaiah_youtube_freeform",
        "query": "이사야서 16챕터 유튜브 강해",
        "preset_id": None,
        "expect_groups": ["MKM_CONCEPT_ISAIAH_YOUTUBE"],
        "forbid_groups": ["MKM_CONCEPT_JOB_SUFFERING"],
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    doc = retrieve_conflict_context(
        case["query"],
        preset_id=case.get("preset_id"),
        use_embedding=False,
    )
    gids = [g.get("conflict_group_id") for g in doc.get("groups") or []]
    ok = doc.get("ok") is True
    if case.get("expect_groups"):
        ok = ok and all(eg in gids for eg in case["expect_groups"])
    if case.get("forbid_groups"):
        ok = ok and not any(fg in gids for fg in case["forbid_groups"])
    if case.get("match_mode"):
        ok = ok and doc.get("match_mode") == case["match_mode"]
    if not case.get("expect_groups") and not gids:
        ok = ok and doc.get("group_count", 0) == 0
    return {
        "id": case["id"],
        "ok": ok,
        "group_ids": gids,
        "match_mode": doc.get("match_mode"),
        "group_count": doc.get("group_count", 0),
    }


def main() -> int:
    rows = [_run_case(c) for c in CASES]
    passed = sum(1 for r in rows if r["ok"])
    doc = {
        "schema": "logos_studio_conflict_retrieval_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": passed == len(rows),
        "passed": passed,
        "total": len(rows),
        "cases": rows,
        "reproduce": "py scripts/check_logos_studio_conflict_retrieval_gate_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "passed": passed, "total": len(rows), "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
