#!/usr/bin/env python3
"""Merge Isaiah YouTube 16-chapter presets into Logos Studio QA presets [HYPO].

Reproduce:
  py scripts/merge_logos_studio_isaiah_youtube_presets_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = ROOT / "reports/isaiah_youtube_16chapter_mkm_bridge_map_v1_latest.json"
DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_READING_PACK = (
    ROOT / "docs/final/artifacts/showroom_logos_isaiah_youtube_reading_pack_slice_v1_latest.json"
)

SPINE_KEYWORDS = [
    "이사야",
    "isaiah",
    "66장",
    "66권",
    "압축",
    "spine",
    "임마누엘",
    "53장",
    "위로하라",
    "새 하늘",
    "youtube",
    "16챕터",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _chapter_keywords(ch: dict[str, Any]) -> list[str]:
    title = str(ch.get("title_ko") or "")
    words = ["이사야", "isaiah", str(ch.get("chapter_id") or "")]
    for token in title.replace(":", " ").replace("—", " ").split():
        t = token.strip("[]()·")
        if len(t) >= 2:
            words.append(t)
    for ref in ch.get("anchor_verse_ids") or []:
        words.append(str(ref).replace(".", " "))
    return list(dict.fromkeys(words))[:16]


def _answer_ko(ch: dict[str, Any]) -> str:
    verdict = ch.get("mkm_verdict") or "partial"
    tier = ch.get("mkm_evidence_tier") or "B"
    paths = ch.get("mkm_paths") or []
    bridge_lines = []
    for p in paths[:3]:
        art = p.get("source_artifact") or ""
        note = p.get("note_ko") or ""
        bridge_lines.append(f"· {art}: {note}")
    flags = ch.get("overclaim_flags") or []
    flag_line = f"\n\n과장 플래그: {', '.join(flags)}" if flags else ""
    gap = ch.get("gap_notes_ko")
    gap_line = f"\n\nGAP: {gap}" if gap else ""
    return (
        f"[HYPO] 이사야 유튜브 **{ch.get('chapter_id')}** — MKM Logos bridge 매핑입니다. "
        f"판정 `{verdict}` · Tier {tier} · research_only · NON_GATING.\n\n"
        f"영상 주장: {ch.get('video_claim_ko')}\n\n"
        f"MKM 경로:\n" + "\n".join(bridge_lines) + flag_line + gap_line
    )


def build_chapter_preset(ch: dict[str, Any], graph_highlights: list[str]) -> dict[str, Any]:
    cid = str(ch.get("chapter_id") or "ch00")
    pid = f"isaiah_yt_{cid}"
    refs = [str(r) for r in (ch.get("anchor_verse_ids") or [])[:8]]
    primary = (ch.get("mkm_paths") or [{}])[0]
    return {
        "id": pid,
        "preset_kind": "isaiah_youtube_chapter",
        "isaiah_youtube_chapter_id": cid,
        "prompt_ko": f"{ch.get('title_ko')} — MKM Logos",
        "answer_ko": _answer_ko(ch),
        "answer_ko_product": (
            f"[HYPO] Isaiah YouTube {cid} · MKM bridge · {ch.get('mkm_verdict')} · NON_GATING."
        ),
        "highlight_node_ids": graph_highlights[:24],
        "keywords": _chapter_keywords(ch),
        "router_path_v1": {
            "schema_version": "logos_router_path_v1",
            "verse_refs": refs,
            "path_id": primary.get("path_id"),
            "note_ko": primary.get("note_ko"),
            "research_only": True,
            "send_gate": "HOLD",
        },
        "isaiah_youtube_bridge_map_ref": str(DEFAULT_BRIDGE.relative_to(ROOT)).replace("\\", "/"),
    }


def build_spine_preset(
    bridge_doc: dict[str, Any],
    chapter_ids: list[str],
    graph_highlights: list[str],
) -> dict[str, Any]:
    spine = bridge_doc.get("summary", {}).get("recommended_studio_spine") or [
        "Isa.6.8",
        "Isa.40.1",
        "Isa.53.5",
        "Isa.65.17",
        "Rev.21.2",
    ]
    return {
        "id": "isaiah_youtube_spine_v1",
        "preset_kind": "isaiah_youtube_spine",
        "prompt_ko": "이사야서 16챕터 — MKM Logos spine (유튜브 강해 대조)",
        "answer_ko": (
            "[HYPO] 이사야 유튜브 16챕터를 MKM Logos spine으로 압축한 프리셋입니다. "
            "5앵커(6:8→40:1→53:5→65:17→Rev.21.2)와 챕터별 `isaiah_yt_ch##` 프리셋을 함께 사용하세요. "
            "66=66 장↔권 1:1 압축은 Tier C 서사 — Fact-Lock 승격 금지."
        ),
        "answer_ko_product": "[HYPO] Isaiah YouTube 16-ch spine · 5 anchors · NON_GATING.",
        "highlight_node_ids": graph_highlights[:32],
        "keywords": SPINE_KEYWORDS,
        "isaiah_youtube_reading_pack_slice": "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json",
        "isaiah_youtube_reading_pack_url": (
            "public_showroom_logos_isaiah_youtube_reading_pack_v1.html?preset=isaiah_youtube_spine_v1"
        ),
        "isaiah_youtube_chapter_preset_ids": chapter_ids,
        "reasoning_path_v1": {
            "schema_version": "logos_reasoning_path_v1",
            "node_ids": [],
            "path_label_ko": " → ".join(spine),
        },
        "router_path_v1": {
            "schema_version": "logos_router_path_v1",
            "verse_refs": spine,
            "path_id": "path_isaiah_youtube_spine",
            "note_ko": "MKM 권장 독해 spine — reports/isaiah_youtube_16chapter_mkm_bridge_map_v1_latest.json",
            "research_only": True,
            "send_gate": "HOLD",
        },
    }


def _graph_highlights_for_refs(graph_doc: dict[str, Any], refs: list[str]) -> list[str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_studio_preset_graph_helpers_v1 import verse_node_ids  # noqa: E402

    return verse_node_ids(graph_doc, set(refs))


def merge_presets(
    presets_doc: dict[str, Any],
    bridge_doc: dict[str, Any],
    graph_doc: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    presets = list(presets_doc.get("presets") or [])
    by_id = {str(p.get("id")): i for i, p in enumerate(presets) if p.get("id")}
    added = 0
    chapter_ids: list[str] = []

    for ch in bridge_doc.get("chapters") or []:
        cid = str(ch.get("chapter_id") or "")
        if not cid:
            continue
        pid = f"isaiah_yt_{cid}"
        chapter_ids.append(pid)
        refs = [str(r) for r in (ch.get("anchor_verse_ids") or [])]
        highlights = _graph_highlights_for_refs(graph_doc, refs)
        entry = build_chapter_preset(ch, highlights)
        if pid in by_id:
            presets[by_id[pid]] = entry
        else:
            presets.append(entry)
            by_id[pid] = len(presets) - 1
            added += 1

    spine_refs = bridge_doc.get("summary", {}).get("recommended_studio_spine") or []
    spine_highlights = _graph_highlights_for_refs(graph_doc, [str(r) for r in spine_refs])
    spine = build_spine_preset(bridge_doc, chapter_ids, spine_highlights)
    spine_id = spine["id"]
    if spine_id in by_id:
        presets[by_id[spine_id]] = spine
    else:
        presets.append(spine)
        added += 1

    presets_doc["presets"] = presets
    presets_doc["isaiah_youtube_merge_source"] = str(DEFAULT_BRIDGE.relative_to(ROOT)).replace("\\", "/")
    presets_doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return presets_doc, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for path in (args.bridge, args.presets, args.graph_json):
        if not path.is_file():
            print(f"missing: {path}", file=sys.stderr)
            return 1
    if not DEFAULT_READING_PACK.is_file():
        print(f"warn: reading pack slice missing — run build_showroom_logos_isaiah_youtube_reading_pack_slice_v1.py first")
    bridge_doc = _load(args.bridge)
    presets_doc = _load(args.presets)
    graph_doc = _load(args.graph_json)
    merged, added = merge_presets(presets_doc, bridge_doc, graph_doc)
    total = len(merged.get("presets") or [])
    summary = {
        "added_or_updated": added,
        "total_presets": total,
        "isaiah_youtube_chapters": len(bridge_doc.get("chapters") or []),
        "spine_preset_id": "isaiah_youtube_spine_v1",
    }
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
