#!/usr/bin/env python3
"""Build logos_concept_bridge_v1 via Gemini batch (research JSON) [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_digital_trust_gemini_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_concept_bridge_v1.schema.json"
DEFAULT_RAW = ROOT / "reports/gemini_batch/logos_concept_bridge_gemini_v1_raw.txt"
SCHEMA = "logos_concept_bridge_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_STUDIO_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model response")
    return json.loads(text[start : end + 1])


def _prompt(concept_ko: str, concept_id: str) -> str:
    return f"""You are a B-track research assistant for MKM Logos GraphRAG (NOT prophecy, NOT trading).

Output ONE JSON object only (no markdown outside JSON) matching schema logos_concept_bridge_v1:
- schema: "logos_concept_bridge_v1"
- hypothesis_tier: "[HYPO]"
- policy: research_only true, non_gating true, no_prophecy_claim true, human_signoff_completed false
- query: concept_id "{concept_id}", label_ko "{concept_ko}"
- nodes: kinds modern_concept, function, lemma_proxy, verse_ref (3-4 paths worth)
- paths: each path_id, steps (node_id chain), note_ko one sentence
- graph_rag_hooks.seed_verse_ids: use format hebrew::Book.ch.v or greek::Book.ch.v or aramaic::Book.ch.v
- known_limitations: 2-3 strings admitting educational proxy, not morphology verified

FORBIDDEN keys: prophecy_hit_rate, topology_overlap_percent, hit_at_1, trading_signal.

Modern concept (Korean): {concept_ko}
Use 3 paths linking concept → functions → lemma_proxy → verse_ref (Job/Zech/Dan/Rev/Ps/Jer acceptable).
"""


def _template_fallback_regime_watchfulness(concept_ko: str, concept_id: str) -> dict[str, Any]:
    """Fallback for bridge #5 — q08 regime transition watchfulness."""
    nodes = [
        {
            "node_id": concept_id,
            "kind": "modern_concept",
            "label_ko": concept_ko,
            "label_en": "watchfulness under regime transition",
        },
        {
            "node_id": "function:stay_awake",
            "kind": "function",
            "label_ko": "깨어 있음·경계",
            "rationale_ko": "Matt 24 밤샘 경계 은유",
        },
        {
            "node_id": "function:sober_alert",
            "kind": "function",
            "label_ko": "근신·깨어 대기",
            "rationale_ko": "1Pet 5 적의 대비",
        },
        {
            "node_id": "lemma:greek:gregoreo_proxy",
            "kind": "lemma_proxy",
            "label_ko": "gregoreo (proxy)",
            "rationale_ko": "깨어 있음 앵커",
        },
        {
            "node_id": "lemma:greek:nepsis_proxy",
            "kind": "lemma_proxy",
            "label_ko": "nepsis (proxy)",
            "rationale_ko": "근신 앵커",
        },
        {"node_id": "verse:Matt.24.42", "kind": "verse_ref", "verse_id": "greek::Matt.24.42", "label_ko": "마 24:42"},
        {"node_id": "verse:1Pet.5.8", "kind": "verse_ref", "verse_id": "greek::1Pet.5.8", "label_ko": "벧전 5:8"},
        {"node_id": "verse:Mark.13.33", "kind": "verse_ref", "verse_id": "greek::Mark.13.33", "label_ko": "막 13:33"},
    ]
    paths = [
        {
            "path_id": "path_stay_awake",
            "steps": [concept_id, "function:stay_awake", "lemma:greek:gregoreo_proxy", "verse:Matt.24.42"],
            "note_ko": "깨어 있음 → 마태 24",
        },
        {
            "path_id": "path_sober_alert",
            "steps": [concept_id, "function:sober_alert", "lemma:greek:nepsis_proxy", "verse:1Pet.5.8"],
            "note_ko": "근신·대비 → 벧전 5",
        },
        {
            "path_id": "path_watch_transition",
            "steps": [concept_id, "function:stay_awake", "lemma:greek:gregoreo_proxy", "verse:Mark.13.33"],
            "note_ko": "체제 전환·경계 → 마가 13",
        },
    ]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "gemini_batch_skipped_template_fallback",
            "human_reviewed": False,
            "llm_api_called": False,
        },
        "query": {"concept_id": concept_id, "label_ko": concept_ko},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {
            "seed_verse_ids": ["greek::Matt.24.42", "greek::1Pet.5.8", "greek::Mark.13.33"]
        },
        "known_limitations": [
            "Template fallback for regime watchfulness (q08 gold align); not live Gemini output.",
            "lemma_proxy labels are educational anchors only.",
        ],
    }


def _template_fallback_mercy_compassion(concept_ko: str, concept_id: str) -> dict[str, Any]:
    """Fallback for bridge #6 — q03 mercy after turmoil."""
    nodes = [
        {
            "node_id": concept_id,
            "kind": "modern_concept",
            "label_ko": concept_ko,
            "label_en": "mercy after turmoil and loss",
        },
        {
            "node_id": "function:comfort_in_valley",
            "kind": "function",
            "label_ko": "골짜기·두려움 속 위로",
            "rationale_ko": "Ps 23 목자 은유",
        },
        {
            "node_id": "function:strength_in_weakness",
            "kind": "function",
            "label_ko": "약함 속 힘·두려움 없음",
            "rationale_ko": "Isa 41 격려 담화",
        },
        {
            "node_id": "function:blessed_mourning",
            "kind": "function",
            "label_ko": "애통·위로받음",
            "rationale_ko": "Matt 5 산상 수훈",
        },
        {
            "node_id": "lemma:hebrew:naham_proxy",
            "kind": "lemma_proxy",
            "label_ko": "naham (proxy)",
            "rationale_ko": "위로 앵커",
        },
        {
            "node_id": "lemma:greek:parakaleo_proxy",
            "kind": "lemma_proxy",
            "label_ko": "parakaleo (proxy)",
            "rationale_ko": "권면·위로 앵커",
        },
        {"node_id": "verse:Ps.23.4", "kind": "verse_ref", "verse_id": "hebrew::Ps.23.4", "label_ko": "시 23:4"},
        {"node_id": "verse:Isa.41.10", "kind": "verse_ref", "verse_id": "hebrew::Isa.41.10", "label_ko": "사 41:10"},
        {"node_id": "verse:Matt.5.4", "kind": "verse_ref", "verse_id": "greek::Matt.5.4", "label_ko": "마 5:4"},
    ]
    paths = [
        {
            "path_id": "path_valley_comfort",
            "steps": [concept_id, "function:comfort_in_valley", "lemma:hebrew:naham_proxy", "verse:Ps.23.4"],
            "note_ko": "골짜기·위로 → 시편 23",
        },
        {
            "path_id": "path_strength_fear_not",
            "steps": [concept_id, "function:strength_in_weakness", "lemma:hebrew:naham_proxy", "verse:Isa.41.10"],
            "note_ko": "두려움 없음 → 이사야 41",
        },
        {
            "path_id": "path_mourning_comforted",
            "steps": [concept_id, "function:blessed_mourning", "lemma:greek:parakaleo_proxy", "verse:Matt.5.4"],
            "note_ko": "애통·위로 → 마태 5",
        },
    ]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "gemini_batch_skipped_template_fallback",
            "human_reviewed": False,
            "llm_api_called": False,
        },
        "query": {"concept_id": concept_id, "label_ko": concept_ko},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {
            "seed_verse_ids": ["hebrew::Ps.23.4", "hebrew::Isa.41.10", "greek::Matt.5.4"]
        },
        "known_limitations": [
            "Template fallback for mercy/compassion (q03 gold align); not live Gemini output.",
            "lemma_proxy labels are educational anchors only.",
        ],
    }


def _template_fallback_wisdom_uncertainty(concept_ko: str, concept_id: str) -> dict[str, Any]:
    """Fallback for bridge #7 — q04 wisdom under uncertainty."""
    nodes = [
        {
            "node_id": concept_id,
            "kind": "modern_concept",
            "label_ko": concept_ko,
            "label_en": "wisdom for uncertainty and fear",
        },
        {
            "node_id": "function:trust_not_lean",
            "kind": "function",
            "label_ko": "스스로 의지하지 않음",
            "rationale_ko": "Prov 3 신뢰·인도 은유",
        },
        {
            "node_id": "function:ask_wisdom",
            "kind": "function",
            "label_ko": "지혜 구함·주시는 자",
            "rationale_ko": "Jas 1 구하라 담화",
        },
        {
            "node_id": "function:fear_no_evil",
            "kind": "function",
            "label_ko": "두려움 속 신뢰",
            "rationale_ko": "Ps 56 두려움·신뢰",
        },
        {
            "node_id": "lemma:hebrew:chokmah_proxy",
            "kind": "lemma_proxy",
            "label_ko": "chokmah (proxy)",
            "rationale_ko": "지혜 앵커",
        },
        {
            "node_id": "lemma:greek:sophia_proxy",
            "kind": "lemma_proxy",
            "label_ko": "sophia (proxy)",
            "rationale_ko": "지혜·은혜 앵커",
        },
        {"node_id": "verse:Prov.3.5", "kind": "verse_ref", "verse_id": "hebrew::Prov.3.5", "label_ko": "잠 3:5"},
        {"node_id": "verse:Jas.1.5", "kind": "verse_ref", "verse_id": "greek::Jas.1.5", "label_ko": "약 1:5"},
        {"node_id": "verse:Ps.56.3", "kind": "verse_ref", "verse_id": "hebrew::Ps.56.3", "label_ko": "시 56:3"},
    ]
    paths = [
        {
            "path_id": "path_trust_guidance",
            "steps": [concept_id, "function:trust_not_lean", "lemma:hebrew:chokmah_proxy", "verse:Prov.3.5"],
            "note_ko": "의지·인도 → 잠언 3",
        },
        {
            "path_id": "path_ask_wisdom",
            "steps": [concept_id, "function:ask_wisdom", "lemma:greek:sophia_proxy", "verse:Jas.1.5"],
            "note_ko": "지혜 구함 → 야고보 1",
        },
        {
            "path_id": "path_fear_trust",
            "steps": [concept_id, "function:fear_no_evil", "lemma:hebrew:chokmah_proxy", "verse:Ps.56.3"],
            "note_ko": "두려움·신뢰 → 시편 56",
        },
    ]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "gemini_batch_skipped_template_fallback",
            "human_reviewed": False,
            "llm_api_called": False,
        },
        "query": {"concept_id": concept_id, "label_ko": concept_ko},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {
            "seed_verse_ids": ["hebrew::Prov.3.5", "greek::Jas.1.5", "hebrew::Ps.56.3"]
        },
        "known_limitations": [
            "Template fallback for wisdom/uncertainty (q04 gold align); not live Gemini output.",
            "lemma_proxy labels are educational anchors only.",
        ],
    }


def _template_fallback_digital_trust(concept_ko: str, concept_id: str) -> dict[str, Any]:
    """Deterministic fallback when API unavailable (--dry-run)."""
    nodes = [
        {
            "node_id": concept_id,
            "kind": "modern_concept",
            "label_ko": concept_ko,
            "label_en": "digital trust and data integrity",
        },
        {
            "node_id": "function:sealed_record",
            "kind": "function",
            "label_ko": "봉인·기록의 무결성",
            "rationale_ko": "Zech 3 돌에 새김 은유",
        },
        {
            "node_id": "function:honest_scales",
            "kind": "function",
            "label_ko": "정직한 저울·거짓 없음",
            "rationale_ko": "레 19 공정 은유",
        },
        {
            "node_id": "lemma:hebrew:emet_proxy",
            "kind": "lemma_proxy",
            "label_ko": "emet (proxy)",
            "rationale_ko": "신실·진리 앵커",
        },
        {
            "node_id": "lemma:hebrew:hotam_proxy",
            "kind": "lemma_proxy",
            "label_ko": "hotam (proxy)",
            "rationale_ko": "인장·봉인 앵커",
        },
        {"node_id": "verse:Zech.3.9", "kind": "verse_ref", "verse_id": "hebrew::Zech.3.9", "label_ko": "스가랴 3:9"},
        {"node_id": "verse:Lev.19.36", "kind": "verse_ref", "verse_id": "hebrew::Lev.19.36", "label_ko": "레 19:36"},
    ]
    paths = [
        {
            "path_id": "path_sealed_record",
            "steps": [concept_id, "function:sealed_record", "lemma:hebrew:hotam_proxy", "verse:Zech.3.9"],
            "note_ko": "봉인·기록 → 스가랴 3",
        },
        {
            "path_id": "path_honest_scales",
            "steps": [concept_id, "function:honest_scales", "lemma:hebrew:emet_proxy", "verse:Lev.19.36"],
            "note_ko": "정직·저울 → 레위기 19",
        },
    ]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "gemini_batch_skipped_template_fallback",
            "human_reviewed": False,
            "llm_api_called": False,
        },
        "query": {"concept_id": concept_id, "label_ko": concept_ko},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {"seed_verse_ids": ["hebrew::Zech.3.9", "hebrew::Lev.19.36"]},
        "known_limitations": [
            "Dry-run template fallback; not live Gemini output.",
            "lemma_proxy labels are educational anchors only.",
        ],
    }


def _template_fallback(concept_ko: str, concept_id: str) -> dict[str, Any]:
    if concept_id == "concept:regime_transition_watchfulness":
        return _template_fallback_regime_watchfulness(concept_ko, concept_id)
    if concept_id == "concept:mercy_after_turmoil":
        return _template_fallback_mercy_compassion(concept_ko, concept_id)
    if concept_id == "concept:wisdom_under_uncertainty":
        return _template_fallback_wisdom_uncertainty(concept_ko, concept_id)
    return _template_fallback_digital_trust(concept_ko, concept_id)


def _normalize_doc(doc: dict[str, Any], *, concept_ko: str, concept_id: str, api_called: bool, method: str) -> dict[str, Any]:
    doc["schema"] = SCHEMA
    doc["hypothesis_tier"] = "[HYPO]"
    doc.setdefault("version", "1.0.0")
    doc["generated_at_utc"] = _utc_now()
    policy = doc.setdefault("policy", {})
    if not isinstance(policy, dict):
        policy = {}
        doc["policy"] = policy
    policy["research_only"] = True
    policy["non_gating"] = True
    policy["no_prophecy_claim"] = True
    policy.setdefault("human_signoff_completed", False)
    policy["generation_method"] = method
    policy["llm_api_called"] = api_called
    policy.setdefault("human_reviewed", False)
    q = doc.setdefault("query", {})
    if not isinstance(q, dict):
        q = {}
        doc["query"] = q
    q.setdefault("concept_id", concept_id)
    q.setdefault("label_ko", concept_ko)
    doc.pop("prophecy_hit_rate", None)
    doc.pop("topology_overlap_percent", None)
    return doc


def _call_gemini(prompt: str, *, timeout_s: int) -> str:
    from google import genai
    from google.genai import types

    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    timeout_ms = max(10_000, int(timeout_s) * 1000)
    client = genai.Client(
        api_key=key,
        vertexai=False,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    cfg = types.GenerateContentConfig(
        temperature=0.2,
        system_instruction=(
            "Return valid JSON only for logos_concept_bridge_v1. "
            "B-track research only; no prophecy or trading claims."
        ),
    )
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=cfg,
    )
    return (resp.text or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--concept-ko", default="디지털 신뢰·데이터 무결성")
    ap.add_argument("--concept-id", default="concept:digital_trust_data_integrity")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--raw-out", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--dry-run", action="store_true", help="template fallback, no API")
    ap.add_argument("--strict-api", action="store_true", help="fail on API error (no template fallback)")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    if args.dry_run:
        doc = _template_fallback(args.concept_ko, args.concept_id)
        method = "gemini_batch_skipped_template_fallback"
        api_called = False
    else:
        try:
            raw = _call_gemini(_prompt(args.concept_ko, args.concept_id), timeout_s=args.timeout)
            args.raw_out.parent.mkdir(parents=True, exist_ok=True)
            args.raw_out.write_text(raw + "\n", encoding="utf-8")
            doc = _extract_json(raw)
            method = "gemini_batch_v1"
            api_called = True
        except Exception as exc:
            if args.strict_api:
                print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
                return 2
            doc = _template_fallback(args.concept_ko, args.concept_id)
            method = "gemini_batch_api_error_template_fallback"
            api_called = False
            lim = doc.setdefault("known_limitations", [])
            if isinstance(lim, list):
                lim.append(f"Gemini API error fallback: {exc!s}"[:200])

    doc = _normalize_doc(
        doc,
        concept_ko=args.concept_ko,
        concept_id=args.concept_id,
        api_called=api_called,
        method=method,
    )

    jsonschema = __import__("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)

    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "paths": len(doc.get("paths") or []),
                "generation_method": doc["policy"]["generation_method"],
                "llm_api_called": doc["policy"]["llm_api_called"],
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
