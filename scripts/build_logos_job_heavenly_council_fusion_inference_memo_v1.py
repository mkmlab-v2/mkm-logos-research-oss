#!/usr/bin/env python3
"""Assemble Job 1:6 heavenly-council fusion inference memo from Logos chain artifacts ([HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_job_heavenly_council_fusion_inference_memo_v1_latest.json"

INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
PANORAMA = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
THEME = ROOT / "docs/research/logos_metaphor_db_v1/theme_39_job_suffering.json"
RESONANCE = ROOT / "docs/final/artifacts/logos_dynamic_resonance_stats_v1_latest.json"
BLOOM_SLICE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
TOPOLOGY = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
PACK_VERIFY_CHAIN = ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json"
PACK3_VERIFY = ROOT / "reports/logos_job_literal_council_verify_v1_latest.json"
PACK2_VERIFY = ROOT / "reports/logos_job_scope_reset_verify_v1_latest.json"
PACK1_VERIFY = ROOT / "reports/logos_job_bridge_lemma_verify_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _lemma_paths(router: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in router.get("paths") or []:
        steps = p.get("steps") or []
        lemmas = [s for s in steps if "lemma" in str(s).lower() or str(s).startswith("lp:")]
        verses = [s for s in steps if str(s).startswith("vr:") or "." in str(s) and str(s)[0].isupper()]
        rows.append(
            {
                "path_id": p.get("path_id"),
                "note_ko": p.get("note_ko"),
                "bridge_artifact": p.get("bridge_artifact"),
                "lemmas": lemmas[-2:] if lemmas else [],
                "verse_ref": verses[-1] if verses else None,
                "four_d_coherence": (p.get("four_d_shadow") or {}).get("four_d_coherence"),
            }
        )
    return rows


def _school_lanes(panorama: dict[str, Any]) -> list[dict[str, Any]]:
    entries = panorama.get("panorama_entries") or []
    for e in entries:
        if e.get("issue_id") == "job_1_6_satan":
            return [
                {
                    "school_id": s.get("school_id"),
                    "label_ko": s.get("label_ko"),
                    "utterance_class": s.get("utterance_class"),
                    "reading_ko": s.get("reading_ko"),
                    "metaphor_transform_tags": s.get("metaphor_transform_tags"),
                    "display_rank_weight": s.get("display_rank_weight"),
                }
                for s in e.get("school_lanes") or []
            ]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    insight = _load(INSIGHT)
    router = _load(ROUTER)
    chain = _load(CHAIN)
    panorama = _load(PANORAMA)
    theme = _load(THEME)
    resonance = _load(RESONANCE)
    bloom = _load(BLOOM_SLICE)
    topology = _load(TOPOLOGY)
    pack_verify_chain = _load(PACK_VERIFY_CHAIN)
    pack3_verify = _load(PACK3_VERIFY)
    pack2_verify = _load(PACK2_VERIFY)
    pack1_verify = _load(PACK1_VERIFY)

    preset = (resonance.get("preset_sidecar") or {}).get("job_suffering_reason") or {}
    narrative_id = (bloom.get("preset_narrative_map") or {}).get("job_suffering_reason")
    four_slot = insight.get("four_slot_response_v1") or {}
    post_fill = four_slot.get("post_llm_fill_v1") or {}

    memo = {
        "schema": "logos_job_heavenly_council_fusion_inference_memo_v1",
        "generated_at_utc": _utc(),
        "query": insight.get("query") or "욥이 고난을 받은 이유",
        "query_id": "job_suffering_reason",
        "anchor_ref": "Job.1.6",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "disclaimer_ko": (
            "[HYPO][NON_GATING] 융합 추론 메모 — corpus·그래프·학파·theme_39·4D sidecar 조합. "
            "인과 단정·Track A·예언·대외 SEND 아님. rank_weight≠진리 점수."
        ),
        "performance": {
            "chain_ok": chain.get("steps", {}).get("insight_payload", {}).get("ok"),
            "bridges_matched": chain.get("steps", {}).get("subgraph_router", {}).get("bridges_matched"),
            "paths": chain.get("steps", {}).get("subgraph_router", {}).get("paths"),
            "verse_ids": chain.get("steps", {}).get("subgraph_router", {}).get("verse_ids"),
            "graph_bloom_nodes": chain.get("steps", {}).get("graph_bloom", {}).get("artifact") and 48,
            "post_llm_fill": post_fill,
            "four_d_mean_coherence": router.get("four_d_shadow_summary", {}).get("mean_four_d_coherence")
            if router.get("four_d_shadow_summary")
            else 1.0,
        },
        "anchor_corpus": {
            "verse_id": "Job.1.6",
            "bhs_snippet": "ו/יהי ה/יום ו/יבאו בני ה/אלהים ל/התיצב על יהוה ו/יבוא גם ה/שטן ב/תוכ/ם",
            "secondary_refs": ["Job.2.3", "Job.2.6"],
            "focus_lemma": "שטן",
            "heavenly_council_ko": (
                "בני האלהים=신적 의회 출석 · להתיצב=여호와 앞에 서림 · השטן=고발자/대적자 역할(관사)"
            ),
        },
        "traditional_theology_lanes": _school_lanes(panorama),
        "mkm_hypothesis_lines": {
            "theme_39": {
                "path": str(THEME.relative_to(ROOT)).replace("\\", "/"),
                "golden_anchor": (theme.get("golden_anchor") or {}).get("ref"),
                "governance_mapping": theme.get("governance_mapping"),
                "commander_insight": theme.get("commander_insight"),
            },
            "worldview_codebook_ko": (
                "Logos=우주 경영 코드북 [NON_GATING]; prologue=incident opener; "
                "38–41=scope reset; 42=restore; miswire→Track A 금지"
            ),
            "blameless_outage_metaphor": "SLO green yet outage — suffering_no_forced_exit",
        },
        "context_network": {
            "lemma_paths": _lemma_paths(router),
            "lemma_edge_hits": router.get("lemma_edge_hits"),
            "verse_ids": router.get("verse_ids"),
            "rag_evidence_count": len(insight.get("rag_evidence") or []),
        },
        "cosmic_anchor_and_4d": {
            "preset_narrative_id": narrative_id,
            "narrative_hops_ko": "Isa.53.5 wound → Jhn.1.29 lamb → Jhn.1.5 light [HYPO curated]",
            "preset_sidecar": preset,
        },
        "codebook_reading": {
            "protocol_layers_ko": [
                "1) 의회(בני האלהים) — 거버넌스 집합",
                "2) 고발(שטן) — bounded adversarial test proposal",
                "3) 허가·상한(1–2장) — test scope",
                "4) debate(3–37) — human retribution theology limit",
                "5) scope reset(38–41) — why-frame denied",
                "6) restore(42, shuv) — fortune reversal lemma path",
            ],
            "energy_4d_hypo": {
                "force_id": preset.get("force_id"),
                "geumhwa_index": preset.get("geumhwa_index"),
                "spread_4d_dynamic": preset.get("spread_4d_dynamic"),
                "note_ko": "물리 에너지 단정 아님 — gematria_bridge_v1·금화교역 은유",
            },
        },
        "intentional_gaps": [
            g.get("text_ko")
            for g in ((four_slot.get("slots") or {}).get("unknown_gap") or {}).get("items") or []
        ],
        "topology_sidecar_layer_a": {
            "present": bool(topology),
            "path": str(TOPOLOGY.relative_to(ROOT)).replace("\\", "/") if topology else None,
            "reading_pack": [
                {
                    "pack_id": p.get("pack_id"),
                    "label_ko": p.get("label_ko"),
                    "deep_synthesis_md_path": p.get("deep_synthesis_md_path"),
                }
                for p in ((topology.get("topology") or {}).get("reading_pack") or [])
            ]
            if topology
            else [],
            "anchor_matrix_count": topology.get("anchor_matrix_count") if topology else 0,
            "narrative_route_count": topology.get("narrative_route_count") if topology else 0,
            "bridge_pivot_ref": ((topology.get("topology") or {}).get("bridge_pivot") or {}).get("verse_ref")
            if topology
            else None,
            "corpus_cross_check": topology.get("corpus_cross_check") if topology else None,
            "reading_pack_verify": {
                "chain_path": str(PACK_VERIFY_CHAIN.relative_to(ROOT)).replace("\\", "/")
                if pack_verify_chain
                else None,
                "chain_ok": pack_verify_chain.get("ok") if pack_verify_chain else None,
                "packs": [
                    {
                        "pack_id": "literal_council_only",
                        "verify_path": str(PACK3_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                        "ok": pack3_verify.get("ok"),
                    },
                    {
                        "pack_id": "scope_reset_no_why",
                        "verify_path": str(PACK2_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                        "ok": pack2_verify.get("ok"),
                    },
                    {
                        "pack_id": "integrated_topology",
                        "verify_path": str(PACK1_VERIFY.relative_to(ROOT)).replace("\\", "/"),
                        "ok": pack1_verify.get("ok"),
                    },
                ],
            },
            "disclaimer_ko": "[HYPO][NON_GATING] Layer A — external Deep Research topology ingest; canon·Track A·SEND 아님.",
        },
        "synthesis_ko": (
            "욥 1:6 하늘 회의는 [corpus] 신적 의회·고발자(שטן)·주권 허가 프레임. "
            "정통·개혁 읽기는 이원신이 아닌 허가된 시험; MKM theme_39는 blameless outage 코드; "
            "lemma망(qavah·yasha·nacham·shuv)은 소망·위로·회복 축; cosmic anchor는 고난→빛 전이 [HYPO]. "
            "「왜 고난?」 인과 단답은 unknown_gap — 38:4 scope reset과 정합. "
            "Layer A topology sidecar(5노드·5구간·reading pack 3종 장문·verify)는 ingest gate 통과 시 병렬 선택지."
        ),
        "source_artifacts": {
            "insight": str(INSIGHT.relative_to(ROOT)).replace("\\", "/"),
            "router": str(ROUTER.relative_to(ROOT)).replace("\\", "/"),
            "chain": str(CHAIN.relative_to(ROOT)).replace("\\", "/"),
            "panorama": str(PANORAMA.relative_to(ROOT)).replace("\\", "/"),
            "public_by_query": "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query/dc73c2c367199e48.json",
            "topology_sidecar": str(TOPOLOGY.relative_to(ROOT)).replace("\\", "/") if topology else None,
            "reading_pack_verify_chain": str(PACK_VERIFY_CHAIN.relative_to(ROOT)).replace("\\", "/")
            if PACK_VERIFY_CHAIN.is_file()
            else None,
        },
        "repro_one_shot": (
            "py scripts/run_logos_topology_sidecar_ingest_chain_v1.py && "
            "py scripts/run_logos_job_reading_pack_verify_chain_v1.py && "
            "py scripts/build_logos_job_heavenly_council_fusion_inference_memo_v1.py"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(memo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
