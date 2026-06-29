#!/usr/bin/env python3
"""Build L1-A inference graph overlay for showroom meaning-topology viz ([HYPO]/NON_GATING).

A1: four_d_families legend (INTERNAL_SEMANTIC_RAG_4D §2.1 separation)
A2: pipeline_stages + router/path eval snapshot (structural only)
A3: sidecar_freshness + observability pass pointer (passive wire)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"
OBS = ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"
SIDECAR = ROOT / "projects/mkm/mkm-life/public/data/logos_dynamic_resonance_sidecar_v1.json"
SIDECAR_STATS = ROOT / "docs/final/artifacts/logos_dynamic_resonance_stats_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_oracle_inference_graph_overlay_v1_latest.json"

FOUR_D_FAMILIES: list[dict[str, Any]] = [
    {
        "family_id": "myeongri_vector_4d",
        "label_ko": "명리 vector_4d",
        "role": "advisory",
        "gating": "non_gating",
        "color": "#9eb4d4",
        "note_ko": "개인·시점 명리 렌즈 — Logos 본문과 혼용 금지",
    },
    {
        "family_id": "logos_4d_state_v1",
        "label_ko": "logos_4d_state",
        "role": "advisory",
        "gating": "non_gating",
        "color": "#c5a057",
        "note_ko": "거시 내러티브 좌표 — gematria 커널과 별개",
    },
    {
        "family_id": "compression_slkm",
        "label_ko": "압축 S,L,K,M",
        "role": "code_seed",
        "gating": "blocked_from_logos_viz",
        "color": "#64748b",
        "note_ko": "Track A/B 압축 시드 축 — Prism·명리와 혼동 금지",
    },
    {
        "family_id": "prism_slkm",
        "label_ko": "Prism S/L/K/M",
        "role": "index_only",
        "gating": "not_a_vector",
        "color": "#475569",
        "note_ko": "Grand Index 파일 분류 라벨 — 역학 수치 아님",
    },
]

PIPELINE_STAGE_DEFS: list[dict[str, str]] = [
    {"stage_id": "semantic", "label_ko": "시맨틱·라우팅"},
    {"stage_id": "rag", "label_ko": "RAG 검색"},
    {"stage_id": "bridge", "label_ko": "번역 브리지"},
    {"stage_id": "logos_4d", "label_ko": "4D 보정"},
    {"stage_id": "router", "label_ko": "router·path"},
]

STAGE_BY_NODE_KIND: dict[str, list[str]] = {
    "verse": ["semantic", "rag", "bridge", "router"],
    "theme": ["semantic", "bridge", "logos_4d", "router"],
    "regime": ["semantic", "logos_4d", "router"],
    "other": ["semantic", "bridge", "router"],
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _parse_utc(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _freshness_block(sidecar: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    generated = (
        sidecar.get("generated_at_utc")
        or stats.get("generated_at_utc")
        or stats.get("snapshot", {}).get("generated_at_utc")
    )
    dt = _parse_utc(str(generated) if generated else None)
    now = datetime.now(timezone.utc)
    age_hours: float | None = None
    stale = False
    if dt:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = round((now - dt).total_seconds() / 3600.0, 2)
        stale = age_hours > 24 * 7
    preset_count = len(sidecar.get("preset_sidecar") or {})
    return {
        "sidecar_path": str(SIDECAR.relative_to(ROOT)).replace("\\", "/"),
        "generated_at_utc": generated,
        "age_hours": age_hours,
        "stale": stale,
        "preset_count": preset_count,
        "wire_status": "ok" if generated else "missing_sidecar",
    }


def build_overlay(*, root: Path = ROOT) -> dict[str, Any]:
    closure = _read_json(root / CLOSURE.relative_to(ROOT))
    obs = _read_json(root / OBS.relative_to(ROOT))
    sidecar = _read_json(root / SIDECAR.relative_to(ROOT))
    stats = _read_json(root / SIDECAR_STATS.relative_to(ROOT))

    path_eval = closure.get("narrative_path_eval") or {}
    router_hit = path_eval.get("router_hit_rate")
    pipeline_stages: list[dict[str, Any]] = []
    for stage in PIPELINE_STAGE_DEFS:
        sid = stage["stage_id"]
        status = "research_only"
        detail = ""
        if sid == "router" and router_hit is not None:
            status = "structural_ok" if float(router_hit) >= 0.99 else "watch"
            detail = f"router_hit_rate={router_hit} (structural overlap)"
        elif sid == "bridge":
            status = "schema_ok"
            detail = "semantic_rag_bridge_insight_bundle_v1"
        elif sid == "logos_4d":
            status = "advisory_only"
            detail = "logos_4d_state_v1 · NON_GATING"
        elif sid == "rag":
            detail = "offline corpus · premium multilens optional"
        pipeline_stages.append(
            {
                **stage,
                "status": status,
                "detail": detail,
            }
        )

    return {
        "schema": "logos_oracle_inference_graph_overlay_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "research_only": True,
        "hypothesis_class": "HYPO",
        "send_gate": "HOLD",
        "l1a_phases": {
            "A1_four_d_families": True,
            "A2_pipeline_path_overlay": True,
            "A3_sidecar_freshness_wire": True,
        },
        "four_d_families": FOUR_D_FAMILIES,
        "pipeline_stages": pipeline_stages,
        "stage_by_node_kind": STAGE_BY_NODE_KIND,
        "router_snapshot": {
            "path_ok_rate": path_eval.get("path_ok_rate"),
            "flow_pass_rate": path_eval.get("flow_pass_rate"),
            "sample_pass_rate": path_eval.get("sample_pass_rate"),
            "router_hit_rate": router_hit,
            "narrative_samples": closure.get("narrative_sample_count"),
            "meaning_graph_hit_anchors": closure.get("meaning_graph_hit_anchors"),
            "boundary_ko": "구조 overlap — 예언 적중·Track A 아님",
        },
        "passive_observability": {
            "observation_pass": obs.get("observation_pass"),
            "observations_pass_count": obs.get("observations_pass_count"),
            "observations_total": obs.get("observations_total"),
            "artifact": str(OBS.relative_to(ROOT)).replace("\\", "/"),
        },
        "sidecar_freshness": _freshness_block(sidecar, stats),
        "ssot_pointers": {
            "arch_outline": "docs/final/INTERNAL_SEMANTIC_RAG_4D_ARCH_OUTLINE_V1.md",
            "bridge_schema": "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json",
            "closure": str(CLOSURE.relative_to(ROOT)).replace("\\", "/"),
        },
        "boundary_ack": (
            "Inference overlay for research viz only — NOT prophecy accuracy, "
            "NOT Track A, NOT clinical efficacy."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_ART)
    args = ap.parse_args()

    doc = build_overlay()
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(
        f"Wrote {args.out_json} families={len(doc['four_d_families'])} "
        f"stages={len(doc['pipeline_stages'])} "
        f"sidecar_wire={doc['sidecar_freshness']['wire_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
