#!/usr/bin/env python3
"""Merge chronology eras into showroom_meaning_topology_qa_presets_v1.json (O-P6)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _bridges_for_era(bridges: list[dict], era_id: str) -> list[dict]:
    return [b for b in bridges if b.get("era_id") == era_id]


def build_era_answer(era: dict, bridges: list[dict]) -> str:
    era_bridges = _bridges_for_era(bridges, era["era_id"])
    parts = [f"[HYPO] 연대기 **{era.get('label_ko', era['era_id'])}** 구간입니다."]
    if era.get("notes_ko"):
        parts.append(era["notes_ko"])
    tags = era.get("theme_tags") or []
    if tags:
        parts.append("테마 태그: " + ", ".join(tags) + ".")
    obs = era.get("regime_tags_observational") or []
    if obs:
        parts.append("관측 레짐 태그(비게이팅): " + ", ".join(obs) + ".")
    refs = era.get("verse_refs") or []
    if refs:
        shown = refs[:5]
        tail = f" 외 {len(refs) - 5}건" if len(refs) > 5 else ""
        parts.append("연결 구절: " + ", ".join(shown) + tail + ".")
    if era_bridges:
        parts.append(f"현대 공명 브리지 {len(era_bridges)}건:")
        for b in era_bridges[:4]:
            parts.append("· " + (b.get("rationale_ko") or b.get("bridge_kind") or "bridge"))
    parts.append(
        "구슬·그래프에서 **era** 노드를 강조했습니다. "
        "투자·확정 예언·실매매 신호가 **아닙니다** (NON_GATING)."
    )
    return "\n\n".join(parts)


def era_preset(era: dict, bridges: list[dict]) -> dict:
    era_id = era["era_id"]
    keywords = [era_id, f"연대기 {era.get('label_ko', '')}"]
    keywords.extend(era.get("theme_tags") or [])
    keywords.extend(era.get("regime_tags_observational") or [])
    return {
        "id": f"era_{era_id}",
        "preset_kind": "chronology_era",
        "prompt_ko": f"연대기: {era.get('label_ko', era_id)}",
        "answer_ko": build_era_answer(era, bridges),
        "highlight_node_ids": list(era.get("verse_refs") or []) + [f"era::{era_id}"],
        "keywords": [k for k in keywords if k],
    }


def merge_presets(doc: dict, chrono: dict) -> tuple[dict, int]:
    bridges = chrono.get("modern_bridges") or []
    eras = chrono.get("eras") or []
    presets = list(doc.get("presets") or [])
    by_id = {p["id"]: i for i, p in enumerate(presets) if p.get("id")}
    added = 0
    for era in eras:
        eid = era.get("era_id")
        if not eid:
            continue
        pid = f"era_{eid}"
        entry = era_preset(era, bridges)
        if pid in by_id:
            presets[by_id[pid]] = entry
        else:
            presets.append(entry)
            by_id[pid] = len(presets) - 1
            added += 1
    doc["presets"] = presets
    doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["chronology_overlay_source"] = chrono.get("schema", "logos_chronology_showroom_overlay_v1")
    return doc, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chrono-json",
        type=Path,
        default=Path("projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_overlay_v1.json"),
    )
    parser.add_argument(
        "--presets-json",
        type=Path,
        default=Path("projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    chrono = json.loads(args.chrono_json.read_text(encoding="utf-8"))
    doc = json.loads(args.presets_json.read_text(encoding="utf-8"))
    merged, added = merge_presets(doc, chrono)
    if args.dry_run:
        print(json.dumps({"would_write": str(args.presets_json), "eras": len(chrono.get("eras") or []), "added": added}, ensure_ascii=False))
        return 0
    args.presets_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.presets_json} (+{added} new era presets, total presets={len(merged['presets'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
