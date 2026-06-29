#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_reasoning_theatre_v1 from envelope + insight ([HYPO], artifact-bound)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "magic_orb_reasoning_theatre_v1"
VERSION = "1.0.0"
GENERATOR = "build_magic_orb_reasoning_theatre_v1.py@1.0.0"

DEFAULT_DISCLAIMER_KO = (
    "관측·해석 연출입니다. [HYPO][NON_GATING] — LLM 내부 생각이 아니라 "
    "MKM 파이프라인 단계(필드·렌즈·충돌·블룸)의 아티팩트 매핑입니다. "
    "투자·실매매·의료·처방 근거 아님."
)

STEP_DEFS: list[dict[str, Any]] = [
    {"id": "ingest", "label_ko": "질문 흡수", "depth": 0.12, "duration_ms": 900, "orbit_hue": 270},
    {"id": "field", "label_ko": "필드 · 레짐", "depth": 0.28, "duration_ms": 1100, "orbit_hue": 248},
    {"id": "retrieve", "label_ko": "맥락 검색", "depth": 0.38, "duration_ms": 1200, "orbit_hue": 210},
    {
        "id": "interpretation_panorama",
        "label_ko": "해석 파노라마",
        "depth": 0.45,
        "duration_ms": 1100,
        "orbit_hue": 280,
    },
    {
        "id": "lens_logos",
        "label_ko": "성경 · 연대기",
        "depth": 0.52,
        "duration_ms": 1400,
        "orbit_hue": 195,
        "lens_id": "logos",
    },
    {
        "id": "lens_myeongni",
        "label_ko": "명리 · 주기",
        "depth": 0.62,
        "duration_ms": 1400,
        "orbit_hue": 265,
        "lens_id": "myeongni",
    },
    {
        "id": "lens_sasang",
        "label_ko": "사상 · 강도",
        "depth": 0.72,
        "duration_ms": 1400,
        "orbit_hue": 42,
        "lens_id": "sasang",
    },
    {"id": "conflict", "label_ko": "렌즈 조율", "depth": 0.82, "duration_ms": 1300, "orbit_hue": 300},
    {"id": "bloom", "label_ko": "맥락 맵 개화", "depth": 0.9, "duration_ms": 1500, "orbit_hue": 175},
    {"id": "resolve", "label_ko": "관측 안정", "depth": 0.98, "duration_ms": 1000, "orbit_hue": 220},
]

LENS_STEP_IDS = {"lens_logos", "lens_myeongni", "lens_sasang"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lens_available(envelope: dict[str, Any] | None, lens_id: str) -> bool:
    if not envelope:
        return lens_id == "logos"
    lenses = envelope.get("lenses") or {}
    row = lenses.get(lens_id)
    if not isinstance(row, dict):
        return False
    return bool(row.get("available"))


def _evidence_ref(envelope: dict[str, Any] | None, insight: dict[str, Any] | None, step_id: str) -> str | None:
    if step_id == "field" and envelope:
        field = envelope.get("field") or {}
        path = field.get("evidence_path")
        if path:
            return str(path)
    if step_id == "interpretation_panorama" and insight:
        fs = insight.get("four_slot_response_v1") or {}
        imp = (fs.get("slots") or {}).get("imagination_path") or {}
        n = len(imp.get("items") or [])
        return f"four_slot.imagination_path.items={n}" if n else "four_slot"
    if step_id == "retrieve" and insight:
        rag = insight.get("rag_evidence") or []
        if rag and isinstance(rag[0], dict):
            return str(rag[0].get("source_id") or "") or None
    if step_id.startswith("lens_") and envelope:
        lens_id = step_id.replace("lens_", "")
        lenses = envelope.get("lenses") or {}
        row = lenses.get(lens_id) or {}
        if isinstance(row, dict) and row.get("evidence_tier"):
            return str(row.get("evidence_tier"))
    if step_id == "conflict" and envelope:
        cr = envelope.get("conflict_resolver") or {}
        if cr.get("summary_ko"):
            return "conflict_resolver.summary_ko"
    if step_id == "bloom" and insight:
        bloom = insight.get("graph_bloom") or {}
        if bloom.get("schema") == "magic_orb_graph_bloom_v1":
            stats = bloom.get("stats") or {}
            nc = stats.get("node_count")
            return f"graph_bloom.nodes={nc}" if nc is not None else "graph_bloom"
    return None


def build_reasoning_theatre(
    *,
    seed_query: str,
    envelope: dict[str, Any] | None = None,
    insight: dict[str, Any] | None = None,
    active_step_id: str = "ingest",
    public_logos_only: bool = False,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for row in STEP_DEFS:
        step_id = str(row["id"])
        if step_id in LENS_STEP_IDS:
            lens_id = str(row["lens_id"])
            if public_logos_only and lens_id != "logos":
                continue
            if not _lens_available(envelope, lens_id):
                continue
        item = dict(row)
        ref = _evidence_ref(envelope, insight, step_id)
        if ref:
            item["evidence_ref"] = ref
        if step_id.startswith("lens_"):
            item["available"] = _lens_available(envelope, str(item["lens_id"]))
        steps.append(item)

    if active_step_id not in {s["id"] for s in steps}:
        active_step_id = steps[0]["id"] if steps else "ingest"

    final_action = None
    if envelope and envelope.get("final_action"):
        final_action = str(envelope["final_action"])

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "non_gating": True,
        "hypothesis_tier": "B",
        "disclaimer_ko": DEFAULT_DISCLAIMER_KO,
        "seed_query": seed_query.strip()[:800],
        "active_step_id": active_step_id,
        "steps": steps,
        "source_refs": {
            "envelope_schema": (envelope or {}).get("schema"),
            "insight_schema": (insight or {}).get("schema"),
            "graph_bloom_schema": ((insight or {}).get("graph_bloom") or {}).get("schema"),
        },
        "generator": GENERATOR,
    }
    if final_action:
        out["final_action"] = final_action
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-query", default="위기 가운데 언약의 안정과 신실")
    ap.add_argument("--envelope", type=Path, default=ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json")
    ap.add_argument("--insight", type=Path, default=ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json")
    ap.add_argument("--active-step", default="lens_logos")
    ap.add_argument("--public-logos-only", action="store_true", default=True)
    ap.add_argument("--full-lens", action="store_true", help="Include myeongni/sasang when envelope allows")
    ap.add_argument("--out", type=Path, default=ROOT / "docs/final/artifacts/magic_orb_reasoning_theatre_v1_latest.json")
    ap.add_argument("--out-public", type=Path, default=ROOT / "projects/mkm/mkm-life/public/data/magic_orb_reasoning_theatre_v1_latest.json")
    args = ap.parse_args()

    envelope = json.loads(args.envelope.read_text(encoding="utf-8")) if args.envelope.is_file() else None
    insight = json.loads(args.insight.read_text(encoding="utf-8")) if args.insight.is_file() else None
    public_only = args.public_logos_only and not args.full_lens

    doc = build_reasoning_theatre(
        seed_query=args.seed_query,
        envelope=envelope,
        insight=insight,
        active_step_id=args.active_step,
        public_logos_only=public_only,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_public.parent.mkdir(parents=True, exist_ok=True)
    args.out_public.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.out_public}")
    print(f"steps={len(doc['steps'])} active={doc['active_step_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
