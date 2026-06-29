#!/usr/bin/env python3
"""Build Q&A node insight cards from Job reading-pack slice ([HYPO], B-track).

Reproducible:
  py scripts/build_showroom_qa_node_insight_cards_v1.py
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

from scripts.core.showroom_router_psalm_seed_v1 import (  # noqa: E402
    THEME_ID,
    THEME_LABEL,
    collect_psalm_refs_from_presets,
    default_psalm_router_refs,
)
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_JOB_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_job_reading_pack_slice_v1.json"
)
DEFAULT_PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
DEFAULT_OUT_MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_qa_node_insight_cards_v1.json"
)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/showroom_qa_node_insight_cards_v1_latest.json"

PACK_URL = "public_showroom_logos_job_reading_pack_v1.html?preset=job_suffering_reason"
PSALM_PRESET_URL = "public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason"
EXCERPT_MAX = 420

PSALM_STUB_KO: dict[str, str] = {
    "Ps.27.14": "[HYPO] 인내·소망 라우터 스텁 — Job spine과 hope·endurance 테마 허브를 잇는 seed 노드입니다.",
    "Ps.23.3": "[HYPO] 회복·목자 이미지 라우터 스텁 — Job.42.10 회복 경로와 연결됩니다.",
    "Ps.37.7": "[HYPO] 침잠·기다림 라우터 스텁 — Daniel 클러스터와 bridge로 등장합니다.",
    "Ps.89.28": "[HYPO] 언약·왕조 라우터 스텁 — empire transition preset path에 등장합니다.",
    "Ps.103.8": "[HYPO] 긍휼·인내 라우터 스텁 — Job 회복·hope spine 교차점입니다.",
}


def _short_excerpt(text: str, *, ref: str) -> str:
    text = re.sub(r"\[internal-ssot\]", "", text)
    text = re.sub(r"\[internal-script\]", "", text)
    idx = text.find(ref.replace(".", " "))
    if idx < 0:
        idx = text.find(ref)
    chunk = text[idx:] if idx >= 0 else text
    chunk = re.sub(r"\s+", " ", chunk).strip()
    if len(chunk) > EXCERPT_MAX:
        chunk = chunk[: EXCERPT_MAX - 1].rstrip() + "…"
    return chunk


def _ref_excerpt_from_presets(canon: str, presets_doc: dict[str, Any] | None) -> str:
    if not presets_doc:
        return PSALM_STUB_KO.get(canon, f"[HYPO] Psalm router stub {canon} · research demo only.")
    for preset in presets_doc.get("presets") or []:
        rp = preset.get("router_path_v1") or {}
        refs = {canonical_verse_ref(str(r)) for r in rp.get("verse_refs") or []}
        if canon not in refs:
            continue
        note = str(rp.get("note_ko") or preset.get("answer_ko_product") or preset.get("answer_ko") or "")
        if note:
            return _short_excerpt(note, ref=canon)
        path_label = str((rp.get("reasoning_path_v1") or {}).get("path_label_ko") or rp.get("path_label_ko") or "")
        if path_label:
            return _short_excerpt(f"[HYPO] Router path: {path_label}", ref=canon)
    return PSALM_STUB_KO.get(canon, f"[HYPO] Psalm router stub {canon} · research demo only.")


def append_psalm_insight_cards(
    cards: dict[str, Any],
    presets_doc: dict[str, Any] | None,
) -> None:
    psalm_refs = collect_psalm_refs_from_presets(presets_doc) if presets_doc else []
    if not psalm_refs:
        psalm_refs = default_psalm_router_refs()
    seen: set[str] = set()
    for raw in psalm_refs:
        canon = canonical_verse_ref(raw)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        vid = f"showroom_psalm_verse::{canon}"
        excerpt = _ref_excerpt_from_presets(canon, presets_doc)
        cards[vid] = {
            "kind": "psalm_verse",
            "ref": canon,
            "title_ko": canon,
            "theme_id": THEME_ID,
            "excerpt_ko": excerpt,
            "preset_url": PSALM_PRESET_URL,
            "governance": "[HYPO][NON_GATING]",
        }
        cards[canon] = cards[vid]

    if THEME_ID not in cards:
        cards[THEME_ID] = {
            "kind": "theme",
            "title_ko": THEME_LABEL,
            "excerpt_ko": (
                "[HYPO] Job·Daniel spine과 연결되는 hope·endurance·psalm 라우터 허브. "
                "프리셋 Path에서 Psalm 구절이 bridge 노드로 등장합니다."
            ),
            "preset_url": PSALM_PRESET_URL,
            "governance": "[HYPO][NON_GATING]",
        }


def build_insight_cards(
    job_doc: dict[str, Any],
    presets_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packs = job_doc.get("reading_packs") or []
    pack_by_id = {str(p.get("pack_id")): p for p in packs}
    default_pack = pack_by_id.get("literal_council_only") or (packs[0] if packs else {})

    cards: dict[str, Any] = {}
    for stage in job_doc.get("narrative_route_public") or []:
        stage_id = str(stage.get("stage_id") or "")
        sid = f"stage::job::{stage_id}"
        pack_id = "literal_council_only" if stage_id == "prologue_heavenly_council" else "integrated_topology"
        pack = pack_by_id.get(pack_id) or default_pack
        excerpt_src = str(pack.get("card_excerpt_ko") or pack.get("summary_ko") or "")
        cards[sid] = {
            "kind": "stage",
            "stage_id": stage_id,
            "title_ko": stage.get("label_ko"),
            "bottleneck_ko": stage.get("bottleneck_ko"),
            "pack_id": pack.get("pack_id"),
            "pack_label_ko": pack.get("label_ko"),
            "excerpt_ko": _short_excerpt(excerpt_src, ref=str(stage.get("verse_refs", ["Job"])[0])),
            "pack_url": PACK_URL,
            "governance": "[HYPO][NON_GATING]",
        }
        for raw_ref in stage.get("verse_refs") or []:
            canon = canonical_verse_ref(str(raw_ref))
            vid = f"showroom_job_verse::{canon}"
            cards[vid] = {
                "kind": "verse",
                "ref": canon,
                "stage_id": stage_id,
                "title_ko": canon,
                "bottleneck_ko": stage.get("bottleneck_ko"),
                "pack_id": pack.get("pack_id"),
                "pack_label_ko": pack.get("label_ko"),
                "excerpt_ko": _short_excerpt(excerpt_src, ref=canon),
                "pack_url": PACK_URL,
                "governance": "[HYPO][NON_GATING]",
            }
            cards[canon] = cards[vid]

    anchor = canonical_verse_ref(str(job_doc.get("anchor_ref") or "Job.1.6"))
    if anchor:
        aid = f"showroom_job_verse::{anchor}"
        if aid not in cards:
            pack = pack_by_id.get("literal_council_only") or default_pack
            cards[aid] = {
                "kind": "verse",
                "ref": anchor,
                "title_ko": anchor + " (anchor)",
                "pack_id": pack.get("pack_id"),
                "pack_label_ko": pack.get("label_ko"),
                "excerpt_ko": _short_excerpt(str(pack.get("card_excerpt_ko") or ""), ref=anchor),
                "pack_url": PACK_URL,
                "governance": "[HYPO][NON_GATING]",
            }

    append_psalm_insight_cards(cards, presets_doc)

    return {
        "schema_version": "showroom_qa_node_insight_cards_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "source_job_slice": "showroom_logos_job_reading_pack_slice_v1.json",
        "source_presets": "showroom_meaning_topology_qa_presets_v1.json" if presets_doc else None,
        "card_count": len(cards),
        "cards": cards,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-slice-json", type=Path, default=DEFAULT_JOB_SLICE)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--out-mvp", type=Path, default=DEFAULT_OUT_MVP)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    args = ap.parse_args()

    if not args.job_slice_json.is_file():
        print(f"FAIL: missing {args.job_slice_json}", file=sys.stderr)
        return 1

    job_doc = json.loads(args.job_slice_json.read_text(encoding="utf-8"))
    presets_doc = None
    if args.presets_json.is_file():
        presets_doc = json.loads(args.presets_json.read_text(encoding="utf-8"))
    doc = build_insight_cards(job_doc, presets_doc)
    doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["reproducible_command"] = "py scripts/build_showroom_qa_node_insight_cards_v1.py"
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    args.out_mvp.parent.mkdir(parents=True, exist_ok=True)
    args.out_mvp.write_text(text, encoding="utf-8")
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(text, encoding="utf-8")
    print(f"WROTE: {args.out_mvp} cards={doc['card_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
