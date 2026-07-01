#!/usr/bin/env python3
"""Build Golden-200 anchor registry SSOT — traffic short-head tollgates, not 31k verse index."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_golden_200_anchor_registry_v1_latest.json"
PUBLIC_MIRROR = ROOT / "projects/no1kmedi/public/data/logos_studio/golden_200_anchor_registry_v1.json"
FAILURE_LOG = ROOT / "reports/logos_ask_inquiry_quality_eval_v1.jsonl"

DEFAULT_CONTRACT: dict[str, Any] = {
    "max_verse_refs": 24,
    "min_distinct_books": 1,
    "forced_fit_forbidden": True,
    "research_only": True,
    "non_gating": True,
    "send_gate": "HOLD",
}

SEED_ENTRIES: list[dict[str, Any]] = [
    {
        "hub_id": "antichrist_666",
        "priority_band": "P0",
        "query_markers_ko": [
            "666",
            "적그리스도",
            "안티크라이스트",
            "계시록 13",
            "짐승의 숫자",
            "마귀의 숫자",
        ],
        "expected_books": ["Rev", "1John", "2Thess"],
        "blocked_stub_books": ["Job", "Ps", "Jer"],
        "primary_verse_refs": ["Rev.13.18", "1John.2.18", "1John.4.3", "2Thess.2.3"],
        "preset_override_ids": ["topic_rev_12_anchor", "topic_rev_1_anchor", "topic_1john_5_anchor"],
        "blocked_preset_ids": ["job_job_suffering_reason", "job_existential_suffering"],
        "reading_pack_artifact": "showroom_logos_antichrist_666_reading_pack_slice_v1_latest.json",
        "hub_spoke_contract": dict(DEFAULT_CONTRACT),
    },
    {
        "hub_id": "passion_crown",
        "priority_band": "P0",
        "query_markers_ko": ["가시면류관", "면류관", "가시 관", "crown of thorns"],
        "expected_books": ["Matt", "Mark", "John"],
        "blocked_stub_books": ["Job", "Ps", "Jer"],
        "primary_verse_refs": ["Matt.27.29", "Mark.15.17", "John.19.2", "John.19.5"],
        "preset_override_ids": ["topic_john_19_anchor", "topic_john_1_anchor"],
        "blocked_preset_ids": ["job_job_suffering_reason"],
        "reading_pack_artifact": "showroom_logos_passion_crown_reading_pack_slice_v1_latest.json",
        "hub_spoke_contract": dict(DEFAULT_CONTRACT),
    },
    {
        "hub_id": "gen2_eve_creation",
        "priority_band": "P0",
        "query_markers_ko": ["하와", "갈비", "갈비뼈", "측", "돕는 배필", "eve", "rib"],
        "expected_books": ["Gen"],
        "book_chapter_rules": [
            {"book": "Gen", "expected_chapters": [2], "blocked_chapters": [6]},
        ],
        "primary_verse_refs": ["Gen.2.21", "Gen.2.22", "Gen.2.23", "Gen.2.24"],
        "preset_override_ids": ["topic_gen_2_anchor"],
        "reading_pack_artifact": "showroom_logos_gen2_eve_reading_pack_slice_v1_latest.json",
        "hub_spoke_contract": dict(DEFAULT_CONTRACT),
    },
    {
        "hub_id": "job_suffering",
        "priority_band": "P1",
        "query_markers_ko": ["욥기", "욥의 고난", "고난의 이유", "job suffering"],
        "expected_books": ["Job"],
        "primary_verse_refs": ["Job.1.21", "Job.2.10", "Job.42.5"],
        "preset_override_ids": ["job_job_suffering_reason", "job_existential_suffering"],
        "reading_pack_artifact": "showroom_logos_job_reading_pack_slice_v1_latest.json",
        "hub_spoke_contract": dict(DEFAULT_CONTRACT),
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _books_from_refs(refs: list[str]) -> set[str]:
    books: set[str] = set()
    for ref in refs:
        m = re.match(r"^([A-Za-z][A-Za-z0-9]*)\.", ref)
        if m:
            books.add(m.group(1))
    return books


def validate_hub_spoke_contract(entry: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    contract = entry.get("hub_spoke_contract") or {}
    if not contract.get("forced_fit_forbidden"):
        errs.append(f"{entry['hub_id']}: forced_fit_forbidden must be true")
    refs = entry.get("primary_verse_refs") or []
    max_refs = int(contract.get("max_verse_refs") or 24)
    if len(refs) > max_refs:
        errs.append(f"{entry['hub_id']}: primary_verse_refs exceeds max_verse_refs")
    min_books = int(contract.get("min_distinct_books") or 1)
    if len(_books_from_refs(refs)) < min_books:
        errs.append(f"{entry['hub_id']}: primary_verse_refs book diversity below min")
    return errs


def merge_failure_log_hits(entries: list[dict[str, Any]]) -> dict[str, int]:
    hits: dict[str, int] = {}
    if not FAILURE_LOG.is_file():
        return hits
    for line in FAILURE_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        hub = str(row.get("hub_id") or row.get("matched_hub_id") or "")
        if hub:
            hits[hub] = hits.get(hub, 0) + 1
    return hits


def build_registry() -> dict[str, Any]:
    failure_hits = merge_failure_log_hits(SEED_ENTRIES)
    entries: list[dict[str, Any]] = []
    for raw in SEED_ENTRIES:
        entry = dict(raw)
        entry["failure_log_hits"] = failure_hits.get(entry["hub_id"], 0)
        errs = validate_hub_spoke_contract(entry)
        if errs:
            raise ValueError("; ".join(errs))
        entries.append(entry)

    entries.sort(key=lambda e: (e["priority_band"], -e.get("failure_log_hits", 0), e["hub_id"]))

    return {
        "schema": "logos_golden_200_anchor_registry_v1",
        "version": "1.0.0",
        "max_slots": 200,
        "scope_ko": (
            "트래픽·실패로그 기반 short-head tollgate 최대 200슬롯. "
            "31k 구절 색인·~1000 테마 전체와 동일 개념이 아님 — Hub-Spoke reading pack 앵커만."
        ),
        "priority_bands": {
            "P0": "Ask 실패·고트래픽·topic_mismatch 재발 — citation lock Hub 우선",
            "P1": "Showroom Hub pack 준비·embedding 라우트 검증",
            "P2": "후보 백로그·수동 승격 대기",
        },
        "entries": entries,
        "generated_at_utc": _utc(),
        "traffic_merge": {
            "failure_log_path": str(FAILURE_LOG.relative_to(ROOT)).replace("\\", "/"),
            "failure_log_present": FAILURE_LOG.is_file(),
            "merged_hub_hits": failure_hits,
        },
    }


def main() -> int:
    doc = build_registry()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PUBLIC_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_MIRROR.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT),
                "public": str(PUBLIC_MIRROR),
                "entries": len(doc["entries"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
