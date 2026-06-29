#!/usr/bin/env python3
"""Classify Logos Studio presets into slots + insight card overlay [HYPO].

Reproducible:
  py scripts/build_logos_studio_preset_taxonomy_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json"

SLOT_LABELS_KO = {
    "era": "시대(era)",
    "theme_cluster": "테마·레짐 클러스터",
    "job_verse": "욥기·고난 spine",
    "verse_anchor": "구절 앵커",
    "school_gap": "학파·갭 (placeholder)",
}

GAP_DEFAULT_KO = (
    "전량 TSK 교차참조(63,779)는 Tier C 로드맵 — 본 스튜디오는 큐레이션 프리셋·부분 그래프입니다."
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_slot(preset_id: str) -> str:
    if preset_id.startswith("era_"):
        return "era"
    if preset_id.startswith("job_"):
        return "job_verse"
    if preset_id.startswith("bigset_topic_"):
        return "school_gap"
    if preset_id.startswith("topic_"):
        return "verse_anchor"
    if re.match(r"^p[1-4]_", preset_id):
        return "theme_cluster"
    return "verse_anchor"


def _verse_anchors(preset: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    rp = preset.get("router_path_v1") if isinstance(preset.get("router_path_v1"), dict) else {}
    for raw in rp.get("verse_refs") or []:
        canon = canonical_verse_ref(str(raw))
        if canon and canon not in refs:
            refs.append(canon)
    for nid in preset.get("highlight_node_ids") or []:
        s = str(nid)
        m = re.search(r"::([A-Za-z]+\.\d+\.\d+)$", s)
        if m:
            canon = canonical_verse_ref(m.group(1))
            if canon and canon not in refs:
                refs.append(canon)
    return refs[:8]


def _one_liner(preset: dict[str, Any]) -> str:
    product = str(preset.get("answer_ko_product") or "").strip()
    if product:
        return re.sub(r"^\[HYPO\]\s*", "", product)[:220]
    ans = str(preset.get("answer_ko") or "").strip()
    return re.sub(r"^\[HYPO\]\s*", "", ans)[:220]


def build_taxonomy(presets_path: Path) -> dict[str, Any]:
    doc = json.loads(presets_path.read_text(encoding="utf-8-sig"))
    presets = doc.get("presets") if isinstance(doc.get("presets"), list) else []
    by_slot: dict[str, list[str]] = {k: [] for k in SLOT_LABELS_KO}
    cards: dict[str, Any] = {}
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        pid = str(preset.get("id") or "")
        if not pid:
            continue
        slot = classify_slot(pid)
        by_slot.setdefault(slot, []).append(pid)
        cards[pid] = {
            "preset_id": pid,
            "slot": slot,
            "slot_label_ko": SLOT_LABELS_KO.get(slot, slot),
            "one_liner_ko": _one_liner(preset),
            "verse_anchors": _verse_anchors(preset),
            "gap_ko": GAP_DEFAULT_KO,
            "governance": "[HYPO][NON_GATING]",
        }
    return {
        "schema": "logos_studio_preset_taxonomy_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "preset_count": len(cards),
        "slot_taxonomy": {
            "slots": [
                {"id": sid, "label_ko": SLOT_LABELS_KO[sid], "preset_ids": sorted(ids)}
                for sid, ids in by_slot.items()
                if ids
            ],
            "target_preset_count_roadmap": 50,
            "current_preset_count": len(cards),
        },
        "insight_cards": cards,
        "honesty": {
            "curated_demo_only": True,
            "live_llm": False,
            "tsk_full_cross_ref": False,
        },
        "source_presets": str(presets_path.relative_to(ROOT)).replace("\\", "/"),
        "reproduce": "py scripts/build_logos_studio_preset_taxonomy_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.presets.is_file():
        print(f"missing presets: {args.presets}", file=sys.stderr)
        return 1
    doc = build_taxonomy(args.presets)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} presets={doc['preset_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
