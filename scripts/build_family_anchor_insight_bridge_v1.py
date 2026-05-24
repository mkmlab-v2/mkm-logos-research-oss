#!/usr/bin/env python3
"""Build family-anchor insight bridge + magic-sphere envelope for mkmlife / RAG pipeline.

Reads family_anchor lived calibration + v4-minimal guide (+ optional myeongni full report).
Emits:
  - semantic_rag_bridge_insight_bundle_v1 (B-track slots, no LLM)
  - three_lens_sphere_envelope_v1-compatible family envelope (LensReportCard tabs)

Does not promote to Track A, clinical, or live trading.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ANCHOR = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_our_daughter_v1_latest.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/daughter_2026_integrated_guide_v4_minimal_latest.json"
DEFAULT_MYEONGNI = ROOT / "reports/tmp_daughter_myeongni_full_v1.json"
DEFAULT_BRIDGE_OUT = ROOT / "docs/final/artifacts/family_anchor_insight_bridge_v1_latest.json"
DEFAULT_ENVELOPE_OUT = ROOT / "docs/final/artifacts/family_anchor_sphere_envelope_v1_latest.json"
DEFAULT_ONE_QUESTION_OUT = ROOT / "reports/family_anchor_one_question_context_latest.json"
DEFAULT_EXPLORE_OUT = ROOT / "docs/final/artifacts/family_orb_explore_layer_v1_latest.json"
DEFAULT_GOVERNANCE_OUT = ROOT / "docs/final/artifacts/family_lens_fusion_governance_v1_latest.json"
DEFAULT_MONTHLY_SEQUENTIAL = ROOT / "docs/final/artifacts/daughter_2026_monthly_sequential_v1_latest.json"
DEFAULT_SHOWROOM_URLS = ROOT / "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data"
BRIDGE_SCHEMA = ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json"
HUB_V6 = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"
HUB_TOPOLOGY = "https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html"
HUB_MKMLIFE = "https://mkmlife.com/oracle-sphere"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise SystemExit(f"invalid json object: {path}")
    return doc


def _join_lines(parts: list[str], *, max_len: int = 1200) -> str:
    text = "\n".join(p for p in parts if p).strip()
    return text[:max_len] if len(text) > max_len else text


def _myeongni_body(v4: dict[str, Any], myeongni: dict[str, Any] | None) -> str:
    b2 = v4.get("block_2_myeongni_peaks_2026") or {}
    b1 = v4.get("block_1_core_v3_lived") or {}
    lines = [
        "[FACT/HYPO · 명리] v4-minimal 핵심월만 — 12칸 풀스토리 없음.",
        _join_lines(b1.get("school_teacher") or [], max_len=400),
        _join_lines(b1.get("study_engine") or [], max_len=400),
    ]
    wealth = b2.get("wealth_peak_months")
    romance = b2.get("romance_peer_peak_months")
    if wealth:
        lines.append(f"재물(용돈) 핵심월: {wealth}")
    if romance:
        lines.append(f"또래 호감 핵심월: {romance}")
    sewoon = b2.get("annual_sewoon_fact") or {}
    if sewoon:
        lines.append(f"2026 연운: {sewoon.get('pillar')} ({sewoon.get('stem_ten_god')})")
    if myeongni:
        pillars = myeongni.get("pillars") or {}
        if isinstance(pillars, dict):
            lines.append(
                "네 기둥 [FACT]: "
                + " · ".join(str(pillars.get(k, "")) for k in ("year", "month", "day", "hour"))
            )
    lines.append("연인·투자·담임=연애 단정 금지.")
    return _join_lines(lines)


def _sasang_body(v4: dict[str, Any], anchor: dict[str, Any]) -> str:
    b3 = v4.get("block_3_sasang_lifestyle_hyo") or {}
    lines = ["[HYPO · 사상·생활] 병증·약리·월별 한증 금지."]
    lines.extend(b3.get("four_lines_ko") or [])
    for axis in anchor.get("supplementary_axes") or []:
        if isinstance(axis, dict) and axis.get("axis") == "sasang_lifestyle":
            obs = axis.get("lifestyle_observed_v2")
            if isinstance(obs, dict):
                lines.append(
                    f"관찰: 키 {obs.get('height_cm')}cm · 댄스 {obs.get('dance')} · 수면 {obs.get('sleep')}"
                )
    return _join_lines(lines)


def _logos_body(v4: dict[str, Any]) -> str:
    b4 = v4.get("block_4_logos_non_gating") or {}
    lines = ["[NON_GATING · Logos] ○월 사건·연애·재물 단정 없음."]
    lines.extend(b4.get("two_lines_ko") or [])
    return _join_lines(lines)


def build_rag_evidence(anchor: dict[str, Any], v4: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    idx = 0

    def add(source_id: str, snippet: str, band: str = "A") -> None:
        nonlocal idx
        if len(out) >= 24:
            return
        out.append(
            {
                "source_id": f"family_anchor:{source_id}:{idx}"[:512],
                "snippet": snippet[:8000],
                "confidence_band": band,
            }
        )
        idx += 1

    for i, g in enumerate(anchor.get("interpretation_guardrails_ko") or []):
        add(f"guardrail_{i}", str(g), "A")
    for i, g in enumerate(v4.get("block_5_forbidden", {}).get("items_ko") or []):
        add(f"forbidden_{i}", str(g), "A")
    add("v4_compact", str(v4.get("report_ko_compact") or "")[:2000], "B")
    return out


def build_structured_slots(v4: dict[str, Any]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    mapping = [
        ("core.v3_school", v4.get("block_1_core_v3_lived")),
        ("myeongni.peaks_2026", v4.get("block_2_myeongni_peaks_2026")),
        ("sasang.lifestyle_hyo", v4.get("block_3_sasang_lifestyle_hyo")),
        ("logos.non_gating", v4.get("block_4_logos_non_gating")),
        ("policy.forbidden", v4.get("block_5_forbidden")),
    ]
    for slot_id, block in mapping:
        if not isinstance(block, dict):
            continue
        text = json.dumps(block, ensure_ascii=False)
        slots.append({"slot_id": slot_id, "text": text[:4000]})
    if not slots:
        slots.append({"slot_id": "family.stub", "text": "family_anchor v4-minimal missing blocks"})
    return slots


def build_bridge_bundle(
    anchor: dict[str, Any],
    v4: dict[str, Any],
    *,
    anchor_path: Path,
) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from scripts.build_semantic_rag_bridge_insight_bundle_v1 import build_bundle

    summary = (
        f"anchor={anchor.get('anchor_id')} v{anchor.get('version')}; "
        f"v4-minimal; lens_stack=sequential_blocks; auto_apply=none"
    )
    bundle = build_bundle(
        calibration_kind="family_anchor_lived_calibration_v1",
        calibration_artifact=anchor_path,
        summary_line=summary[:512],
        rag_evidence=build_rag_evidence(anchor, v4),
        structured_slots=build_structured_slots(v4),
        lens_id="family_parenting",
        route_confidence=0.85,
        track="B-track",
        gating="advisory",
        hypothesis_label="[HYPO]",
    )
    bundle["bridge_meta"] = {
        "validation_ok": True,
        "validation_errors": [],
        "family_profile_id": anchor.get("anchor_id"),
        "v4_artifact_ref": _rel(DEFAULT_V4),
        "generator": "build_family_anchor_insight_bridge_v1.py",
    }
    return bundle


def build_sphere_envelope(
    anchor: dict[str, Any],
    v4: dict[str, Any],
    myeongni: dict[str, Any] | None,
    *,
    anchor_path: Path,
    bridge_path: Path,
    explore_layer_ref: str | None = None,
) -> dict[str, Any]:
    b1 = v4.get("block_1_core_v3_lived") or {}
    return {
        "schema": "three_lens_sphere_envelope_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "labels": ["HYPO", "NON_GATING", "research_only"],
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "profile_mode": "family_anchor",
        "profile_id": anchor.get("anchor_id"),
        "field": {
            "regime_id": str(anchor.get("anchor_id") or "family_anchor"),
            "regime_label_ko": "가족 · 2026 육아 통합 가이드 v4-minimal [HYPO]",
            "evidence_path": _rel(anchor_path),
            "prophecy_headline_active_rate": None,
        },
        "lenses": {
            "myeongni": {
                "available": True,
                "title_ko": "명리 · 학교·재물·또래",
                "body_ko": _myeongni_body(v4, myeongni),
                "non_gating": True,
                "artifact_path": _rel(DEFAULT_MYEONGNI),
                "evidence_tier": "hypo_research_only",
            },
            "sasang": {
                "available": True,
                "title_ko": "사상 · 생활·체력",
                "body_ko": _sasang_body(v4, anchor),
                "non_gating": True,
                "artifact_path": _rel(DEFAULT_V4),
                "evidence_tier": "hypo_research_only",
            },
            "logos": {
                "available": True,
                "title_ko": "성경 · 리듬·화법",
                "body_ko": _logos_body(v4),
                "non_gating": True,
                "artifact_path": _rel(bridge_path),
                "evidence_tier": "hypo_research_only",
            },
        },
        "conflict_resolver": {
            "summary_ko": (
                "렌즈는 탭별 독립 표기 · 순차 블록(v3→명리→사상→Logos). "
                "월별 3렌즈 합선·단일 예언 점수 없음."
            ),
            "minority_lens_ids": [],
            "agreement_rate": 1.0,
            "conflict_count": 0,
        },
        "final_action": "WATCH",
        "parenting_guardrail_ko": _join_lines(b1.get("study_engine") or [], max_len=300),
        "hub_links": {
            "jemaai_logos_v6_product": HUB_V6,
            "jemaai_meaning_topology_graph": HUB_TOPOLOGY,
            "mkmlife_oracle_sphere": HUB_MKMLIFE,
        },
        "graph_viz": {
            "node_count_display": 0,
            "graph_slice_path": _rel(DEFAULT_V4),
        },
        "rag_layers": {
            "lexical": ["family_anchor_guardrails"],
            "semantic": ["family_anchor_insight_bridge_v1"],
            "temporal": ["daughter_myeongni_monthly_peaks"],
            "constitutional": ["family_lived_calibration"],
        },
        "inputs_manifest": [
            {"path": _rel(anchor_path), "present": anchor_path.is_file()},
            {"path": _rel(DEFAULT_V4), "present": DEFAULT_V4.is_file()},
            {"path": _rel(DEFAULT_MYEONGNI), "present": DEFAULT_MYEONGNI.is_file()},
            {"path": _rel(bridge_path), "present": True},
        ]
        + (
            [
                {
                    "path": _rel(DEFAULT_MONTHLY_SEQUENTIAL),
                    "present": DEFAULT_MONTHLY_SEQUENTIAL.is_file(),
                }
            ]
            if DEFAULT_MONTHLY_SEQUENTIAL.is_file()
            else []
        ),
        "insight_bridge_ref": _rel(bridge_path),
        "monthly_sequential_ref": _rel(DEFAULT_MONTHLY_SEQUENTIAL)
        if DEFAULT_MONTHLY_SEQUENTIAL.is_file()
        else None,
        "layer_b_explore": {
            "default_enabled": False,
            "enable_query_flag": "explore=1",
            "rag_graph_runtime": False,
            "explore_layer_ref": explore_layer_ref or _rel(DEFAULT_EXPLORE_OUT),
            "governance_ref": _rel(DEFAULT_GOVERNANCE_OUT),
        },
    }


def _write_explore_layer_artifacts(
    v4: dict[str, Any],
    *,
    explore_out: Path,
    governance_out: Path,
    strict_schema: bool,
) -> None:
    from scripts.build_family_orb_explore_layer_v1 import (
        GOV_SCHEMA_PATH,
        SCHEMA_PATH,
        build_explore_layer,
        build_governance,
        _validate,
    )

    showroom_path = DEFAULT_SHOWROOM_URLS
    if not showroom_path.is_file():
        raise SystemExit(f"missing showroom urls: {showroom_path}")
    showroom = _read(showroom_path)
    profile_id = str(v4.get("anchor_id") or "family_anchor_our_daughter_v1")
    explore_ref = _rel(explore_out)
    gov_ref = _rel(governance_out)
    explore = build_explore_layer(v4, showroom, governance_ref=gov_ref)
    governance = build_governance(profile_id=profile_id, explore_ref=explore_ref)
    for doc, path, schema in (
        (explore, explore_out, SCHEMA_PATH),
        (governance, governance_out, GOV_SCHEMA_PATH),
    ):
        errs = _validate(doc, schema)
        if errs and strict_schema:
            raise SystemExit(f"explore layer schema validation failed: {errs}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(path)}")


def build_one_question_context(envelope: dict[str, Any], bridge: dict[str, Any]) -> dict[str, Any]:
    myeongni = envelope.get("lenses", {}).get("myeongni") or {}
    logos = envelope.get("lenses", {}).get("logos") or {}
    return {
        "schema": "family_anchor_one_question_context_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "preview_only": True,
        "track_a_auto_order_forbidden": True,
        "generated_at_utc": _now(),
        "profile_id": envelope.get("profile_id"),
        "concept_ko": "가족 프로필 · v4-minimal 3렌즈 탭 (명리·사상·Logos) — 원퀘스천 보조",
        "hero_ko": envelope.get("parenting_guardrail_ko") or "11:30 취침·루틴 = 학습·컨디션 연료 [HYPO]",
        "lens_preview_ko": {
            "myeongni": (myeongni.get("body_ko") or "")[:500],
            "sasang": (envelope.get("lenses", {}).get("sasang") or {}).get("body_ko", "")[:500],
            "logos": (logos.get("body_ko") or "")[:500],
        },
        "final_action_parenting": envelope.get("final_action"),
        "upstream": {
            "envelope_path": "docs/final/artifacts/family_anchor_sphere_envelope_v1_latest.json",
            "bridge_path": "docs/final/artifacts/family_anchor_insight_bridge_v1_latest.json",
            "bridge_schema": bridge.get("schema"),
        },
        "disclaimer_ko": "[HYPO][NON_GATING] 미성년·가족 양육 가드레일. 연인·투자·임상·실매매 단정 없음.",
    }


def _validate_bridge(bundle: dict[str, Any]) -> list[str]:
    if not BRIDGE_SCHEMA.is_file():
        return ["schema file missing"]
    try:
        import jsonschema  # type: ignore

        schema = json.loads(BRIDGE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(bundle, schema)
        return []
    except ImportError:
        return []
    except Exception as exc:
        return [str(exc)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor-json", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--bridge-out", type=Path, default=DEFAULT_BRIDGE_OUT)
    ap.add_argument("--envelope-out", type=Path, default=DEFAULT_ENVELOPE_OUT)
    ap.add_argument("--one-question-out", type=Path, default=DEFAULT_ONE_QUESTION_OUT)
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    ap.add_argument("--strict-schema", action="store_true")
    ap.add_argument("--skip-explore-layer", action="store_true")
    args = ap.parse_args()

    anchor_path = args.anchor_json if args.anchor_json.is_absolute() else ROOT / args.anchor_json
    v4_path = args.v4_json if args.v4_json.is_absolute() else ROOT / args.v4_json
    myeongni_path = args.myeongni_json if args.myeongni_json.is_absolute() else ROOT / args.myeongni_json

    anchor = _read(anchor_path)
    v4 = _read(v4_path)
    myeongni = _read(myeongni_path) if myeongni_path.is_file() else None

    bridge = build_bridge_bundle(anchor, v4, anchor_path=anchor_path)
    errors = _validate_bridge(bridge)
    if errors:
        bridge.setdefault("bridge_meta", {})["validation_ok"] = False
        bridge["bridge_meta"]["validation_errors"] = errors[:32]
        if args.strict_schema:
            raise SystemExit(f"schema validation failed: {errors}")
    else:
        bridge.setdefault("bridge_meta", {})["validation_ok"] = True

    bridge_out = args.bridge_out if args.bridge_out.is_absolute() else ROOT / args.bridge_out
    envelope_out = args.envelope_out if args.envelope_out.is_absolute() else ROOT / args.envelope_out
    one_q_out = args.one_question_out if args.one_question_out.is_absolute() else ROOT / args.one_question_out

    explore_out = DEFAULT_EXPLORE_OUT
    governance_out = DEFAULT_GOVERNANCE_OUT
    if not args.skip_explore_layer:
        _write_explore_layer_artifacts(
            v4,
            explore_out=explore_out,
            governance_out=governance_out,
            strict_schema=args.strict_schema,
        )

    envelope = build_sphere_envelope(
        anchor,
        v4,
        myeongni,
        anchor_path=anchor_path,
        bridge_path=bridge_out,
        explore_layer_ref=_rel(explore_out),
    )
    one_q = build_one_question_context(envelope, bridge)

    for path, doc in (
        (bridge_out, bridge),
        (envelope_out, envelope),
        (one_q_out, one_q),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(path)}")

    if args.copy_mkmlife_public:
        MKMLIFE_PUBLIC.mkdir(parents=True, exist_ok=True)
        for name, doc in (
            ("family_anchor_insight_bridge_v1.json", bridge),
            ("family_anchor_sphere_envelope_v1.json", envelope),
            ("family_anchor_one_question_context_v1.json", one_q),
        ):
            dest = MKMLIFE_PUBLIC / name
            dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {_rel(dest)}")
        if not args.skip_explore_layer and explore_out.is_file() and governance_out.is_file():
            for name, src in (
                ("family_orb_explore_layer_v1.json", explore_out),
                ("family_lens_fusion_governance_v1.json", governance_out),
            ):
                dest = MKMLIFE_PUBLIC / name
                dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"Wrote {_rel(dest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
