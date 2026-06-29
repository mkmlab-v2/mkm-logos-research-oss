#!/usr/bin/env python3
"""Merge BigSet conflict-topic presets into showroom QA presets (Phase A1).

Reproduce:
  py scripts/merge_logos_studio_bigset_topic_presets_v1.py
"""

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

from scripts.logos_studio_preset_graph_helpers_v1 import (  # noqa: E402
    parse_verse_tokens,
    verse_node_ids,
)

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_CONFLICT = ROOT / "docs/final/artifacts/bigset_multi_topic_conflict_surface_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"

BIGSET_TOPIC_SPECS: list[dict[str, Any]] = [
    {
        "id": "bigset_topic_benei_haelohim",
        "conflict_group_id": "MKM_CONCEPT_SONS_OF_GOD",
        "prompt_ko": "베네 하 엘로힘(Benei HaElohim)·하나님의 아들들은 누구인가?",
        "keywords": [
            "베네",
            "benei",
            "haelohim",
            "하나님의 아들",
            "sons of god",
            "sons-of-god",
            "beni ha elohim",
            "genesis 6",
            "창세기 6",
        ],
    },
    {
        "id": "bigset_topic_nephilim",
        "conflict_group_id": "MKM_CONCEPT_NEPHILIM",
        "prompt_ko": "네피림(Nephilim)과 거인 전통은 어떻게 해석되나?",
        "keywords": [
            "네피림",
            "nephilim",
            "거인",
            "giants",
            "genesis 6",
            "창세기 6",
            "하이브리드",
        ],
    },
    {
        "id": "bigset_topic_watchers",
        "conflict_group_id": "MKM_CONCEPT_NEPHILIM",
        "prompt_ko": "감시자(Watchers)·타락 천사 전통과 창세기 6의 연결은?",
        "keywords": [
            "감시자",
            "watchers",
            "watcher",
            "타락 천사",
            "타락한 천사",
            "fallen angels",
            "book of watchers",
            "에녹",
            "enoch",
            "인간 여성",
            "결혼",
            "고대 전통",
        ],
    },
    {
        "id": "bigset_topic_divine_council",
        "conflict_group_id": "MKM_CONCEPT_SONS_OF_GOD",
        "prompt_ko": "신의 회의(divine council)·시편 82·욥기 1장과 하나님의 아들들",
        "keywords": [
            "신의 회의",
            "divine council",
            "시편 82",
            "psalm 82",
            "욥기 1",
            "job 1",
            "하늘 회의",
            "beney elohim",
        ],
    },
    {
        "id": "bigset_topic_genesis6_schools",
        "conflict_group_id": "MKM_CONCEPT_SONS_OF_GOD",
        "prompt_ko": "창세기 6:1-4 학파 갈등(천사·세트 족속·판사설) 요약",
        "keywords": [
            "창세기 6:1",
            "genesis 6:1",
            "학파",
            "세트",
            "seth",
            "판사",
            "targum",
            "네오피티",
        ],
    },
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _group_index(conflict_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(g.get("conflict_group_id")): g for g in (conflict_doc.get("groups") or [])}


def _school_summary(group: dict[str, Any], *, max_schools: int = 4) -> list[str]:
    lines: list[str] = []
    for school in (group.get("schools") or [])[:max_schools]:
        tier = str(school.get("school_tier") or "?")
        text = str(school.get("interpretation_ko") or "").strip()
        if " | " in text:
            text = text.split(" | ", 1)[0].strip()
        if len(text) > 280:
            text = text[:277] + "…"
        trad = ", ".join((school.get("traditions") or [])[:2])
        suffix = f" ({trad})" if trad else ""
        lines.append(f"· [{tier}] {text}{suffix}")
    return lines


def _collect_verse_refs(group: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for school in group.get("schools") or []:
        for raw in school.get("verse_refs") or []:
            refs.extend(parse_verse_tokens(str(raw)))
    return list(dict.fromkeys(refs))[:12]


def build_bigset_preset(
    spec: dict[str, Any],
    group: dict[str, Any],
    graph_doc: dict[str, Any],
) -> dict[str, Any]:
    lexicon = str(group.get("lexicon_base") or spec["conflict_group_id"])
    verse_refs = _collect_verse_refs(group)
    highlights = verse_node_ids(graph_doc, set(verse_refs))
    if not highlights:
        highlights = verse_node_ids(graph_doc, {"Gen.6.3", "Gen.6.7", "Job.1.6"})
    school_lines = _school_summary(group)
    answer_ko = (
        f"[HYPO] BigSet 충돌면 **{lexicon}** ({spec['conflict_group_id']}) 큐레이션 프리셋입니다.\n\n"
        f"학파 병렬(단정·실매매·NON_GATING 아님):\n"
        + "\n".join(school_lines)
        + "\n\n연결 구절 앵커: "
        + (", ".join(verse_refs[:6]) if verse_refs else "Gen.6 · Job.1 (그래프 슬라이스)")
        + "."
    )
    answer_product = (
        f"[HYPO] BigSet conflict surface · {lexicon} · curated schools parallel · NON_GATING."
    )
    return {
        "id": spec["id"],
        "preset_kind": "bigset_conflict_topic",
        "bigset_conflict_group_id": spec["conflict_group_id"],
        "prompt_ko": spec["prompt_ko"],
        "answer_ko": answer_ko,
        "answer_ko_product": answer_product,
        "highlight_node_ids": highlights[:48],
        "keywords": list(spec.get("keywords") or []),
        "router_path_v1": {
            "schema_version": "logos_router_path_v1",
            "verse_refs": verse_refs[:8],
            "research_only": True,
            "send_gate": "HOLD",
        },
    }


def merge_bigset_presets(
    presets_doc: dict[str, Any],
    conflict_doc: dict[str, Any],
    graph_doc: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    groups = _group_index(conflict_doc)
    presets = list(presets_doc.get("presets") or [])
    by_id = {str(p.get("id")): i for i, p in enumerate(presets) if p.get("id")}
    added = 0
    for spec in BIGSET_TOPIC_SPECS:
        gid = spec["conflict_group_id"]
        group = groups.get(gid)
        if not group:
            continue
        entry = build_bigset_preset(spec, group, graph_doc)
        pid = entry["id"]
        if pid in by_id:
            presets[by_id[pid]] = entry
        else:
            presets.append(entry)
            by_id[pid] = len(presets) - 1
            added += 1
    presets_doc["presets"] = presets
    presets_doc["bigset_topic_merge_source"] = str(
        DEFAULT_CONFLICT.relative_to(ROOT)
    ).replace("\\", "/")
    presets_doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return presets_doc, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--conflict-json", type=Path, default=DEFAULT_CONFLICT)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    presets_doc = _load(args.presets)
    conflict_doc = _load(args.conflict_json)
    graph_doc = _load(args.graph_json)
    merged, added = merge_bigset_presets(presets_doc, conflict_doc, graph_doc)
    total = len(merged.get("presets") or [])
    summary = {"added": added, "total_presets": total, "bigset_specs": len(BIGSET_TOPIC_SPECS)}
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    args.presets.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mvp = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json"
    mvp.parent.mkdir(parents=True, exist_ok=True)
    mvp.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
