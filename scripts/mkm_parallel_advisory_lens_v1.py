#!/usr/bin/env python3
"""Parallel advisory lens core — balanced 4-perspective slices, elastic exclusion [HYPO]."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/mkm_parallel_advisory_lens_manifest_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_SCIENCE_KOSPI = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_SASANG_INTERPRETIVE_BUNDLE = (
    ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _read_jsonl_row_for_date(path: Path, session_date: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and str(obj.get("session_date") or "")[:10] == session_date:
            return obj
    return None


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    doc = _read(path)
    if not doc:
        raise FileNotFoundError(f"manifest missing: {path}")
    return doc


def resolve_active_lenses(
    manifest: dict[str, Any],
    *,
    domain_id: str,
    exclude_lenses: list[str] | None = None,
    include_lenses: list[str] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    profile = (manifest.get("domain_profiles") or {}).get(domain_id) or {}
    default = list(profile.get("default_active_lenses") or [])
    excluded: list[dict[str, Any]] = []

    active = list(default)
    if include_lenses:
        active = [l for l in include_lenses if l in default or l == "science"]
    for lens_id in exclude_lenses or []:
        if lens_id in active:
            active.remove(lens_id)
            excluded.append({"lens_id": lens_id, "reason": "commander_exclude"})

    if profile.get("status") == "stub_hold" and domain_id != "finance":
        if "science" in active:
            active.remove("science")
            excluded.append({"lens_id": "science", "reason": "science_pack_stub_hold"})

    charter_dash = {
        "music": ["sasang", "myeongni", "logos"],
        "rib55": ["sasang", "myeongni", "logos"],
    }
    for lens_id in charter_dash.get(domain_id, []):
        if lens_id in active:
            active.remove(lens_id)
            excluded.append({"lens_id": lens_id, "reason": "domain_charter_dash"})

    return active, excluded


def build_science_finance_slice(
    session_date: str,
    *,
    science_jsonl: Path = DEFAULT_SCIENCE_KOSPI,
) -> dict[str, Any]:
    row = _read_jsonl_row_for_date(science_jsonl, session_date)
    if not row:
        return {
            "lens_id": "science",
            "domain_id": "finance",
            "pack_id": "science@finance",
            "non_gating": True,
            "status": "missing_corpus_row",
            "direction_sign": "neutral",
            "confidence": 0.0,
            "components_summary": None,
            "honest_note_ko": "해당 일자 science_core 행 없음 — 통찰에서 과장 금지",
        }
    scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
    direction = str(row.get("direction") or "neutral")
    sign = direction if direction in ("bull", "bear", "neutral") else "neutral"
    return {
        "lens_id": "science",
        "domain_id": "finance",
        "pack_id": "science@finance",
        "non_gating": True,
        "status": "ok",
        "direction_score": scores.get("direction_score"),
        "confidence": scores.get("confidence"),
        "direction_sign": sign,
        "components_summary": {
            k: (row.get("components") or {}).get(k, {}).get("mode")
            for k in ("price", "macro", "news")
            if isinstance((row.get("components") or {}).get(k), dict)
        },
        "science_core_pointer": str(science_jsonl.as_posix()),
        "session_date": session_date,
        "honest_note_ko": "정량 science_core 시각 — 인문 3렌즈 우위 아님",
    }


def build_science_stub_slice(domain_id: str, *, seed_path: Path) -> dict[str, Any]:
    seed = _read(seed_path) or {}
    anchors = seed.get("anchor_nodes") if isinstance(seed.get("anchor_nodes"), list) else []
    paths = seed.get("graph_paths") if isinstance(seed.get("graph_paths"), list) else []
    status = seed.get("status") or ("corpus_seed_v1" if anchors else "stub_hold")
    return {
        "lens_id": "science",
        "domain_id": domain_id,
        "pack_id": f"science@{domain_id}",
        "non_gating": True,
        "status": status,
        "direction_sign": "neutral",
        "confidence": 0.0,
        "query_ko": seed.get("query_ko"),
        "horizon_contract": seed.get("horizon_contract"),
        "anchor_nodes": anchors,
        "graph_paths": paths,
        "corpus_pointer": seed.get("corpus_pointer"),
        "anchor_count": len(anchors),
        "honest_note_ko": (
            "코퍼스 seed — 구조·관측 앵커만, 수치·방향·게이트 단정 금지"
            if anchors
            else "코퍼스 stub — 수치·방향 단정 금지"
        ),
    }


def _lens_slice_from_fusion(fusion: dict[str, Any], lens_id: str) -> dict[str, Any] | None:
    if lens_id == "field":
        f = fusion.get("field")
        return dict(f) if isinstance(f, dict) else None
    lenses = fusion.get("lenses") if isinstance(fusion.get("lenses"), dict) else {}
    sl = lenses.get(lens_id)
    if not isinstance(sl, dict):
        return None
    out = dict(sl)
    out.setdefault("non_gating", lens_id != "field")
    out["honest_note_ko"] = (
        "인문 렌즈 시각 — Final Action·매매 방향 합산 금지"
        if lens_id in ("sasang", "myeongni", "logos")
        else out.get("honest_note_ko")
    )
    return out


HUMANIST_LENS_TIERS: dict[str, str] = {
    "sasang": "A/B",
    "myeongni": "B",
    "logos": "C",
}

DISK_EPISTEMIC_ANCHORS = {
    "direction_fusion_holdout_pp": {"min": 0.0, "max": -0.2917, "note": "shock WF holdout vs active"},
    "graphrag_fusion_ablation_pp": -0.1875,
    "field_band_oos_pp": 0.186,
    "field_band_status": "research_only_HOLD",
}


def _extract_pyobyeong_dr_pointer(bundle: dict[str, Any]) -> dict[str, Any] | None:
    for sec in bundle.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        ptr = sec.get("pyobyeong_dr_pointer_v1")
        if isinstance(ptr, dict):
            return dict(ptr)
    return None


def load_sasang_interpretive_bundle(
    path: Path = DEFAULT_SASANG_INTERPRETIVE_BUNDLE,
) -> dict[str, Any] | None:
    return _read(path)


def build_sasang_interpretive_advisory_enrichment(
    bundle: dict[str, Any] | None,
    *,
    bundle_pointer: str = "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
) -> dict[str, Any] | None:
    if not bundle:
        return None
    syn = bundle.get("synthesis_v1") if isinstance(bundle.get("synthesis_v1"), dict) else {}
    pyo = _extract_pyobyeong_dr_pointer(bundle)
    return {
        "schema": "sasang_interpretive_advisory_enrichment_v1",
        "bundle_pointer": bundle_pointer,
        "bundle_version": bundle.get("version"),
        "rail": bundle.get("rail"),
        "decision_authority": bundle.get("decision_authority"),
        "send_gate": bundle.get("send_gate") or "HOLD",
        "non_gating": True,
        "gating_eligible": False,
        "in_sample_narrative": True,
        "synthesis_v1": {
            "how_to_synthesize_ko": syn.get("how_to_synthesize_ko"),
            "axis_order_rationale_ko": syn.get("axis_order_rationale_ko"),
            "disagreement_protocol_ko": syn.get("disagreement_protocol_ko"),
            "forbidden_synthesis_ko": syn.get("forbidden_synthesis_ko"),
        },
        "pyobyeong_dr_pointer_v1": pyo,
        "human_commander_gate_v1": bundle.get("human_commander_gate_v1"),
        "honest_note_ko": (
            "사상 통찰 번들 축·금지합성 — direction merge·Track A·실매매 트리거 금지"
        ),
    }


def enrich_sasang_slice_with_interpretive_bundle(
    sl: dict[str, Any],
    bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(sl)
    enrichment = build_sasang_interpretive_advisory_enrichment(bundle)
    if enrichment:
        out["interpretive_bundle_enrichment"] = enrichment
    return out


def _tag_humanist_slice(sl: dict[str, Any], lens_id: str) -> dict[str, Any]:
    out = dict(sl)
    out["in_sample_narrative"] = True
    out["epistemic_tier"] = HUMANIST_LENS_TIERS.get(lens_id, "B")
    out["non_gating"] = True
    out["gating_eligible"] = False
    out.setdefault("tags", []).append("[NON_GATING]")
    if "tags" in out and isinstance(out["tags"], list):
        tags = list(out["tags"])
        if "[NON_GATING]" not in tags:
            tags.append("[NON_GATING]")
        out["tags"] = tags
    return out


def build_in_sample_narrative(slices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    narrative: dict[str, Any] = {
        "schema": "mkm_in_sample_narrative_v1",
        "gating_eligible": False,
        "non_gating": True,
        "epistemic_moat": True,
    }
    for lid in ("sasang", "myeongni", "logos"):
        sl = slices.get(lid)
        if not sl:
            continue
        tagged = _tag_humanist_slice(sl, lid)
        narrative[f"{lid}_narrative"] = {
            "lens_id": lid,
            "epistemic_tier": tagged.get("epistemic_tier"),
            "direction_sign": tagged.get("direction_sign"),
            "honest_note_ko": tagged.get("honest_note_ko"),
            "slice": tagged,
        }
    return narrative


def build_execution_plane(slices: dict[str, Any]) -> dict[str, Any]:
    field = slices.get("field") or {}
    science = slices.get("science") or {}
    return {
        "schema": "mkm_execution_plane_v1",
        "field_signal": {
            **field,
            "role": "field_regime_observation",
            "gating_eligible": True,
            "note_ko": "유일 게이팅 후보 — Track A auto·oracle 승격 금지",
        }
        if field
        else None,
        "science_signal": {
            **science,
            "role": "science_advisory_slice",
            "gating_eligible": False,
            "non_gating": True,
            "note_ko": "advisory science@domain — Field science_core 정량과 별개",
        }
        if science
        else None,
    }


def validate_epistemic_wiring(brief: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    isn = brief.get("in_sample_narrative")
    if not isinstance(isn, dict):
        errors.append("missing in_sample_narrative")
    elif isn.get("gating_eligible"):
        errors.append("in_sample_narrative.gating_eligible must be false")
    else:
        for lid in ("sasang", "myeongni", "logos"):
            key = f"{lid}_narrative"
            block = isn.get(key)
            if isinstance(block, dict) and block.get("slice", {}).get("gating_eligible"):
                errors.append(f"{key}.slice.gating_eligible must be false")

    ep = brief.get("execution_plane")
    if not isinstance(ep, dict):
        errors.append("missing execution_plane")
    else:
        sci = ep.get("science_signal")
        if isinstance(sci, dict) and sci.get("gating_eligible"):
            errors.append("execution_plane.science_signal must not be gating")

    pls = brief.get("parallel_lens_slices") or {}
    for lid in ("sasang", "myeongni", "logos"):
        sl = pls.get(lid)
        if isinstance(sl, dict):
            if not sl.get("in_sample_narrative"):
                errors.append(f"parallel_lens_slices.{lid} missing in_sample_narrative tag")
            if sl.get("gating_eligible"):
                errors.append(f"parallel_lens_slices.{lid} gating_eligible must be false")
    return errors


def build_conflict_surface(
    slices: dict[str, dict[str, Any]],
    *,
    fusion: dict[str, Any] | None,
) -> dict[str, Any]:
    signs: dict[str, str | None] = {}
    for lid, sl in slices.items():
        if lid == "field":
            continue
        signs[lid] = str(sl.get("direction_sign") or "neutral") if sl else None

    unique_signs = {s for s in signs.values() if s and s != "neutral"}
    disagree = len(unique_signs) > 1
    conflicts: list[str] = []
    if fusion and isinstance(fusion.get("fusion_resolution"), dict):
        conflicts = list(fusion["fusion_resolution"].get("conflict_ids") or [])

    return {
        "lens_signs": signs,
        "perspectives_disagree": disagree,
        "conflict_ids": conflicts,
        "no_lens_supremacy": True,
        "verdict_ko": (
            "렌즈 간 시각 불일치 — 단일 '옳은' 렌즈 없음, 병렬 해설 유지"
            if disagree or conflicts
            else "렌즈 시각 대체로 정렬 — 그래도 방향 merge·매매 트리거 금지"
        ),
    }


def build_advisory_ko(
    conflict: dict[str, Any],
    *,
    domain_id: str,
    active_lenses: list[str],
    excluded: list[dict[str, Any]],
) -> str:
    parts = [
        f"[Advisory·{domain_id}] 활성 렌즈: {', '.join(active_lenses)}.",
        conflict.get("verdict_ko") or "",
    ]
    if excluded:
        ex = ", ".join(f"{e.get('lens_id')}({e.get('reason')})" for e in excluded)
        parts.append(f"제외·보류: {ex}.")
    parts.append("균형 보도 — 어느 한 렌즈가 항상 옳다고 가정하지 않음.")
    return " ".join(p for p in parts if p)


def build_parallel_advisory_brief(
    *,
    manifest: dict[str, Any],
    fusion: dict[str, Any],
    domain_id: str = "finance",
    session_date: str | None = None,
    exclude_lenses: list[str] | None = None,
    include_lenses: list[str] | None = None,
) -> dict[str, Any]:
    anchor = session_date or str(fusion.get("session_anchor") or "")
    if not anchor:
        ev_anchor = (fusion.get("field") or {}).get("session_date")
        anchor = str(ev_anchor) if ev_anchor else ""

    active, excluded = resolve_active_lenses(
        manifest, domain_id=domain_id, exclude_lenses=exclude_lenses, include_lenses=include_lenses
    )

    slices: dict[str, dict[str, Any]] = {}
    if "field" in active or (manifest.get("domain_profiles") or {}).get(domain_id, {}).get("field_layer") == "required":
        field_sl = _lens_slice_from_fusion(fusion, "field")
        if field_sl:
            slices["field"] = field_sl

    sasang_bundle = load_sasang_interpretive_bundle() if "sasang" in active else None

    for lid in ("sasang", "myeongni", "logos"):
        if lid not in active:
            continue
        sl = _lens_slice_from_fusion(fusion, lid)
        if sl:
            tagged = _tag_humanist_slice(sl, lid)
            if lid == "sasang":
                tagged = enrich_sasang_slice_with_interpretive_bundle(tagged, sasang_bundle)
            slices[lid] = tagged
        else:
            excluded.append({"lens_id": lid, "reason": "fusion_slice_missing"})

    if "science" in active:
        profile = (manifest.get("domain_profiles") or {}).get(domain_id) or {}
        if domain_id == "finance":
            slices["science"] = build_science_finance_slice(anchor)
        else:
            ptr = Path(str(profile.get("science_pointer") or ""))
            if not ptr.is_absolute():
                ptr = ROOT / ptr
            slices["science"] = build_science_stub_slice(domain_id, seed_path=ptr)

    conflict = build_conflict_surface(slices, fusion=fusion)
    advisory = build_advisory_ko(conflict, domain_id=domain_id, active_lenses=active, excluded=excluded)
    in_sample = build_in_sample_narrative(slices)
    execution = build_execution_plane(slices)

    brief = {
        "schema": "mkm_parallel_advisory_brief_v1",
        "schema_rev": "1.1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "track_a_go": False,
        "domain_id": domain_id,
        "session_anchor": anchor or None,
        "balance_doctrine": manifest.get("balance_doctrine"),
        "epistemic_moat": {
            "contract": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md#9-epistemic-moat-인식론적-격벽",
            "anti_hype": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md#10-anti-hype-안티-하이프",
            "ontology": "docs/final/MKM_LENS_ONTOLOGY_CONSTITUTION_V1.md",
            "disk_anchors": DISK_EPISTEMIC_ANCHORS,
        },
        "shared_spine": manifest.get("shared_spine"),
        "active_lenses": active,
        "excluded_lenses": excluded,
        "execution_plane": execution,
        "in_sample_narrative": in_sample,
        "field_observation": slices.get("field"),
        "parallel_lens_slices": {k: v for k, v in slices.items() if k != "field"},
        "conflict_surface": conflict,
        "advisory_ko": advisory,
        "forbidden": manifest.get("output_contract", {}).get("forbidden_outputs"),
        "upstream_pointers": {
            "manifest": "docs/final/artifacts/mkm_parallel_advisory_lens_manifest_v1_latest.json",
            "fusion": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
            "contract": "docs/final/MKM_PARALLEL_ADVISORY_LENS_CONTRACT_V1.md",
            "sasang_interpretive_bundle": (
                "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
                if sasang_bundle
                else None
            ),
        },
        "interpretive_bundle_pointers": {
            "sasang": (
                "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
                if sasang_bundle
                else None
            ),
        },
        "reproduce": "py scripts/run_mkm_parallel_advisory_chain_v1.py",
    }
    wiring_errors = validate_epistemic_wiring(brief)
    brief["epistemic_wiring_ok"] = len(wiring_errors) == 0
    if wiring_errors:
        brief["epistemic_wiring_errors"] = wiring_errors
    return brief
