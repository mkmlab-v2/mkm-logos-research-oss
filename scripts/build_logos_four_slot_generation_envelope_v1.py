#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-generation four-slot output contract — Fact/Corpus/Imagination/Gap before LLM fill."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIGEST = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
DEFAULT_SHADOW = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"

SCHEMA_VERSION = "logos_four_slot_generation_envelope_v1"
POLICY_ID = "four_slot_semantic_constraint_v1"
GENERATOR = "build_logos_four_slot_generation_envelope_v1.py@1.0.0"

SLOT_ORDER = ("fact_locked", "corpus_bound", "imagination_path", "unknown_gap")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(
    *,
    digest: dict[str, Any],
    shadow: dict[str, Any],
    enable_tier15_llm_fill: bool = False,
) -> dict[str, Any]:
    verified = bool((shadow.get("rail_status") or {}).get("verified_anchor_achieved"))
    entries = digest.get("panorama_entries") or []
    primary = next(
        (e for e in entries if e.get("anchor_ref") == digest.get("primary_anchor_ref")),
        entries[0] if entries else {},
    )
    anchor = primary.get("anchor_corpus") or {}
    corpus_snippet = str(anchor.get("text_snippet") or "")
    school_summaries = [
        {
            "anchor_ref": e.get("anchor_ref"),
            "school_id": s.get("school_id"),
            "label_ko": s.get("label_ko"),
            "utterance_class": s.get("utterance_class"),
            "reading_preview_ko": str(s.get("reading_ko") or "")[:160],
        }
        for e in entries
        for s in e.get("school_lanes") or []
        if s.get("utterance_class") == "imagination_path"
    ][:12]

    slots: dict[str, Any] = {
        "fact_locked": {
            "required": False,
            "fill_policy": "only_if_verified_anchor",
            "content": None if not verified else {"verified_anchor": True},
            "must_not_hallucinate": True,
        },
        "corpus_bound": {
            "required": True,
            "fill_policy": "resolver_or_empty",
            "content": {
                "anchor_ref": primary.get("anchor_ref"),
                "text_snippet": corpus_snippet,
                "found": anchor.get("found", False),
            },
            "must_not_hallucinate": True,
        },
        "imagination_path": {
            "required": True,
            "fill_policy": "curated_school_lanes_only",
            "content": {
                "school_panorama": school_summaries,
                "parallel_required": True,
                "human_adoption_required": True,
            },
            "must_not_present_as_fact": True,
        },
        "unknown_gap": {
            "required": True,
            "fill_policy": "explicit_gap_if_missing_fact",
            "content": {
                "gaps": [
                    {
                        "kind": "dss_job_cross_ref",
                        "in_repo": False,
                        "note_ko": "DSS·CROSS_REF Job 미연결 — 단정 금지.",
                    },
                    {
                        "kind": "why_question_causality",
                        "note_ko": "「왜」인과 서사 자동 조립 금지 — boundary_proof HOLD.",
                    },
                ],
            },
            "must_not_hallucinate": True,
        },
    }

    why_query = "왜" in str(shadow.get("query_ko") or digest.get("issue_id") or "")
    enforcement = {
        "generation_constraint": "four_slot_mandatory",
        "if_fact_locked_empty_return_gap": True,
        "if_why_without_corpus_causality": "route_imagination_and_gap" if why_query else "standard",
        "bias_parallel_schools": True,
        "llm_autofill_for_schools": bool(enable_tier15_llm_fill),
    }

    llm_fill_policy: dict[str, Any] | None = None
    if enable_tier15_llm_fill:
        llm_fill_policy = {
            "enabled": True,
            "cost_tier": "tier_15",
            "allowed_slots": ["imagination_path", "unknown_gap"],
            "forbidden_slots": ["fact_locked", "corpus_bound"],
            "requires_human_gate_ack": True,
            "requires_env": "MKM_FOUR_SLOT_LLM_FILL_ALLOWED",
            "max_chars_per_item": 480,
            "forbidden_phrases": list(
                (
                    "Fact-Lock 100%",
                    "환각 제거",
                    "확정적으로",
                    "반드시 받은 이유는",
                )
            ),
            "product_sku": "ask_one_premium_report",
            "track_a_blocked": True,
        }
        slots["imagination_path"]["fill_policy"] = "curated_school_lanes_plus_tier15_llm"
    else:
        llm_fill_policy = {
            "enabled": False,
            "cost_tier": "tier_0",
            "product_sku": "oracle_sphere_public_demo",
        }

    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "policy_id": POLICY_ID,
        "issue_id": digest.get("issue_id") or shadow.get("issue_id"),
        "query_ko": shadow.get("query_ko"),
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "note_ko": (
                "생성 전 4슬롯 계약. LLM은 빈 fact_locked를 사실로 채우지 말 것. "
                "학파 내용은 큐레이션 시드만 — live 신학 생성 금지."
            ),
        },
        "slot_order": list(SLOT_ORDER),
        "slots": slots,
        "enforcement": enforcement,
        "llm_fill_policy_v1": llm_fill_policy,
        "fact_lock": {
            "track": "B",
            "send_gate": "HOLD",
            "verified_anchor": verified,
        },
        "reproduce": {
            "command": "py scripts/build_logos_four_slot_generation_envelope_v1.py",
            "tier15_command": (
                "py scripts/build_logos_four_slot_generation_envelope_v1.py --enable-tier15-llm-fill"
            ),
        },
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build four-slot generation envelope v1.")
    ap.add_argument("--digest-json", type=Path, default=DEFAULT_DIGEST)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument(
        "--enable-tier15-llm-fill",
        action="store_true",
        help="Enable tier_15 post-LLM fill policy (imagination_path/unknown_gap only; HOLD).",
    )
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    doc = build(
        digest=_load(_p(args.digest_json)),
        shadow=_load(_p(args.shadow_json)),
        enable_tier15_llm_fill=bool(args.enable_tier15_llm_fill),
    )
    out = _p(args.out_artifact)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
