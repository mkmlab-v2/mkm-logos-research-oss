#!/usr/bin/env python3
"""Build default raw/retry inputs for logos_response retry pipeline.

Purpose:
- Keep daily scheduler resilient even when no fresh LLM raw text was pushed.
- Convert deterministic `mkm_logos_response_v2_latest.json` into a
  `logos_response_v2` payload, then write:
  1) raw input text (optionally fenced/noisy style)
  2) retry fallback input text (strict JSON)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MKM = ART / "mkm_logos_response_v2_latest.json"
DEFAULT_RAW = ART / "logos_response_v1_llm_raw_latest.txt"
DEFAULT_RETRY = ART / "logos_response_v1_llm_retry_latest.txt"
DEFAULT_CHRONICLE_SIGNAL = ART / "chronicle_history_news_signal_stub_latest.json"
DEFAULT_CHRONICLE_HISTORY = ART / "chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_63779 = ART / "logos_63779_registry_v1_latest.json"
DEFAULT_MORPH = ART / "logos_morphology_registry_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _build_chronicle_rows(
    *,
    chronicle_signal: dict[str, Any] | None,
    chronicle_history_rows: list[dict[str, Any]],
    evidence_links: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    if isinstance(chronicle_signal, dict) and chronicle_signal:
        cw = chronicle_signal.get("chronicle_window") if isinstance(chronicle_signal.get("chronicle_window"), dict) else {}
        hw = chronicle_signal.get("history_pattern") if isinstance(chronicle_signal.get("history_pattern"), dict) else {}
        nw = chronicle_signal.get("news_context") if isinstance(chronicle_signal.get("news_context"), dict) else {}
        ca = chronicle_signal.get("context_metrics") if isinstance(chronicle_signal.get("context_metrics"), dict) else {}
        sa = chronicle_signal.get("signal_assessment") if isinstance(chronicle_signal.get("signal_assessment"), dict) else {}
        dl = chronicle_signal.get("decision_layer") if isinstance(chronicle_signal.get("decision_layer"), dict) else {}
        window_id = str(cw.get("window_id") or "chronicle_window")
        rows.append(
            {
                "summary": (
                    f"연대기신호 | 윈도우={window_id} "
                    f"| 관측점수={float(sa.get('composite_signal_score') or 0.0):.6f} "
                    f"| 뉴스커버리지={float(nw.get('coverage_score') or 0.0):.3f} "
                    f"| 레짐={str(ca.get('dual_regime_primary_id') or 'N/A')} "
                    f"| 최종판정={str(dl.get('final_decision') or 'N/A')}"
                ),
                "period_or_ref": f"{str(cw.get('start_utc') or '?')}..{str(cw.get('end_utc') or '?')}",
                "evidence_pointer": "docs/final/artifacts/chronicle_history_news_signal_stub_latest.json",
                "confidence_band": "mid",
            }
        )
        evidence_refs = hw.get("evidence_refs") if isinstance(hw.get("evidence_refs"), list) else []
        if evidence_refs:
            rows.append(
                {
                    "summary": (
                        f"역사패턴 | ID={str(hw.get('pattern_id') or 'N/A')} "
                        f"| 유사도={float(hw.get('similarity_score') or 0.0):.3f} "
                        f"| 소스신뢰도={float(nw.get('source_reliability_score') or 0.0):.3f} "
                        f"| 레짐={str(ca.get('dual_regime_primary_id') or 'N/A')}"
                    ),
                    "period_or_ref": f"news_window={str(nw.get('news_window_id') or '?')}",
                    "evidence_pointer": str(evidence_refs[0]),
                    "confidence_band": "mid",
                }
            )

    if chronicle_history_rows:
        tail = chronicle_history_rows[-1]
        rows.append(
            {
                "summary": (
                    f"히스토리꼬리 | 관측점수={float(tail.get('composite_signal_score') or 0.0):.6f} "
                    f"| 이력유사도={float(tail.get('history_similarity') or 0.0):.3f} "
                    f"| 레짐={str(tail.get('dual_regime_primary_id') or 'N/A')} "
                    f"| 최종판정={str(tail.get('final_decision') or 'N/A')}"
                ),
                "period_or_ref": str(tail.get("generated_at_utc") or "history_latest"),
                "evidence_pointer": "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl",
                "confidence_band": "mid",
            }
        )

    if not rows:
        for item in evidence_links[:3]:
            if not isinstance(item, dict):
                continue
            note = str(item.get("note") or "evidence_ref")
            ref = str(item.get("ref") or "")
            if not ref:
                continue
            rows.append(
                {
                    "summary": f"{note} 관측 포인터",
                    "period_or_ref": "ops_snapshot_latest",
                    "evidence_pointer": ref,
                    "confidence_band": "mid",
                }
            )
    return rows[:3]


def _build_63779_layers(registry_63779: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    deep_default = {
        "pattern_id": "63779_like_v1",
        "similarity_0_1": 0.0,
        "cohesion_ratio": 0.0,
        "cohesion_band": "<1x",
        "price_mapping_forbidden": True,
        "non_gating_only": True,
        "falsification_conditions": ["registry_63779_missing"],
        "commentary": "63779는 가격 매핑이 아닌 NON_GATING 패턴 식별자다.",
    }
    arch_default = {
        "phase_label": "balanced_tension",
        "chaos_score": 0.5,
        "order_score": 0.5,
        "tension_score": 0.5,
        "narrative_claim": "질서/혼돈 해석은 보조 프레임이며 실행 트리거가 아니다.",
        "falsification_conditions": ["registry_63779_missing"],
    }
    if not isinstance(registry_63779, dict):
        return deep_default, arch_default
    deep = registry_63779.get("deep_logos_tension_gematria")
    arch = registry_63779.get("archetypal_chaos_order_phase")
    if not isinstance(deep, dict):
        deep = deep_default
    if not isinstance(arch, dict):
        arch = arch_default
    deep = {**deep_default, **deep}
    arch = {**arch_default, **arch}
    return deep, arch


def _build_morphology_layer(registry_morph: dict[str, Any] | None) -> dict[str, Any]:
    default_layer = {
        "registry_id": "morphhb_hebrew_core_v1",
        "scope": "hebrew_morphology_only",
        "hebrew_atoms_total": 0,
        "matched_hebrew_atoms": 0,
        "unmatched_hebrew_atoms": 0,
        "coverage_ratio_0_1": 0.0,
        "resolved_multi_rows": 0,
        "index_unique_norm_keys": 0,
        "sampled_matched_rows": 0,
        "top_lemmas": [],
        "top_morph_tags": [],
        "interpretation_guard": "원어 형태소 레이어는 의미 해설 보조이며 가격/실행 트리거가 아니다.",
        "non_gating_only": True,
        "price_mapping_forbidden": True,
    }
    if not isinstance(registry_morph, dict):
        return default_layer
    layer = registry_morph.get("morphology_layer")
    if not isinstance(layer, dict):
        return default_layer
    return {**default_layer, **layer}


def build_logos_response_v2(
    mkm: dict[str, Any],
    *,
    corpus_profile_id: str,
    chronicle_signal: dict[str, Any] | None = None,
    chronicle_history_rows: list[dict[str, Any]] | None = None,
    registry_63779: dict[str, Any] | None = None,
    registry_morph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    core = mkm.get("core_layer") if isinstance(mkm.get("core_layer"), dict) else {}
    coord = mkm.get("coordinator_layer") if isinstance(mkm.get("coordinator_layer"), dict) else {}
    final_action = mkm.get("final_action") if isinstance(mkm.get("final_action"), dict) else {}
    response_layer = mkm.get("response_layer") if isinstance(mkm.get("response_layer"), dict) else {}
    evidence = mkm.get("evidence_links") if isinstance(mkm.get("evidence_links"), list) else []

    direction = float(core.get("direction_core") or 0.0)
    confidence = float(coord.get("confidence_adjusted") or core.get("confidence_core") or 0.0)
    resonance = float(core.get("archetype_resonance") or 0.0)
    failed = coord.get("failed_check_keys") if isinstance(coord.get("failed_check_keys"), list) else []
    failed = [str(x) for x in failed]

    chronicle_rows = _build_chronicle_rows(
        chronicle_signal=chronicle_signal,
        chronicle_history_rows=chronicle_history_rows or [],
        evidence_links=evidence,
    )
    deep_63779, arch_phase = _build_63779_layers(registry_63779)
    morphology_layer = _build_morphology_layer(registry_morph)

    risk_lines = [
        "해석은 NON_GATING 보조 레이어이며 운영/거래 트리거로 사용하지 않는다.",
        "교단·원문 비평 이견을 단일 결론으로 환원하면 과적합 위험이 있다.",
    ]
    for key in failed[:4]:
        risk_lines.append(f"코디네이터 실패 키 감지: {key}")

    text_critical_scope = (
        "정경 본문 중심 + 운영 문서 기반 2차 요약"
        if corpus_profile_id == "canon_only_v1"
        else "정경 + DSS/외경 참조 요약(운영 포인터 기반)"
    )
    decision = str(final_action.get("decision") or "WATCH")
    reason = str(final_action.get("reason") or "No reason")
    template_text = str(response_layer.get("template_text") or "")
    query_redef = (
        f"현재 질의는 코디네이터 결과({decision})와 관측 포인터를 이용해 상징·비평·수학화 해설을 구성하는 B-track 브리핑으로 재정의한다."
    )

    final_insight = (
        f"[NON_GATING 브리핑] 운영결론={decision} | 코어근거={reason} | "
        f"관측신뢰도={confidence:.3f} | 상징공명={resonance:.3f} | "
        "본 문서는 연구/해설 전용이며 실행 신호로 사용하지 않는다."
    )

    return {
        "schema": "logos_response_v2",
        "corpus_profile_id": corpus_profile_id,
        "query_redefinition": query_redef,
        "symbolic_anchors": [
            {
                "motif": "watchful_discernment",
                "core_meaning": "신호는 관측으로 유지하되 해석층을 구조화해 재평가 준비를 강화",
            },
            {
                "motif": "witness_evidence_chain",
                "core_meaning": "해석의 근거를 아티팩트 포인터로 고정해 감사 가능성 확보",
            },
        ],
        "gematria_layer": {
            "pattern_label": "ops_bridge_v1",
            "components": {
                "aggregation": round(_clip01((confidence + resonance) / 2), 6),
                "tension": round(_clip01(abs(direction)), 6),
                "transition": round(_clip01(confidence - abs(direction) * 0.2), 6),
            },
            "notes": "수학화 값은 해석 보조지표이며 결과 단정/예언 확정 근거가 아니다.",
        },
        "vector_4d": {
            "S_spirit": round(_clip01(0.45 + confidence * 0.4), 6),
            "L_logos": round(_clip01(0.5 + resonance * 0.4), 6),
            "K_kairos": round(_clip01(0.5 + direction * 0.25), 6),
            "M_material": round(_clip01(0.4 + abs(direction) * 0.3), 6),
            "phase_description": f"결정={decision}, 신뢰도={confidence:.3f}, 공명={resonance:.3f} 기반 운영 위상",
        },
        "chronicle_mapping": chronicle_rows,
        "risk_and_falsification": risk_lines,
        "final_insight_non_gating": (
            f"{final_insight} | 보조요약={template_text}" if template_text else final_insight
        ),
        "denominational_view": [
            {
                "tradition_label": "canonical_operational_reading",
                "interpretation_summary": "정경 중심 질서·경계 해석을 유지하며 운영 포인터와 분리해 기술한다.",
                "confidence_band": "mid",
            },
            {
                "tradition_label": "historical_critical_overlay",
                "interpretation_summary": "본문 형성 과정과 다중 전승 가능성을 열어둔 채 결론 단정을 유보한다.",
                "confidence_band": "low",
            },
        ],
        "text_critical_notes": {
            "source_scope": text_critical_scope,
            "variant_notes": "전승·번역 차이가 존재할 수 있으며 단일 판본 결론을 강제하지 않는다.",
            "uncertainty_notes": "운영 아티팩트 기반 2차 요약이므로 원문 비평의 최종 판단이 아니다.",
        },
        "mkm_interpretation_math": {
            "model_version": "mkm_logos_ops_bridge_v1",
            "symbolic_intensity": round(_clip01((confidence + resonance) / 2), 6),
            "covenant_tension": round(_clip01(abs(direction)), 6),
            "restoration_momentum": round(_clip01(max(0.0, direction)), 6),
            "commentary": "SLKM 수학화는 비교·조율용 보조 지표이며 미래 사건 단정에 사용하지 않는다.",
        },
        "deep_logos_tension_gematria": deep_63779,
        "archetypal_chaos_order_phase": arch_phase,
        "morphology_layer": morphology_layer,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mkm-json", type=Path, default=DEFAULT_MKM)
    ap.add_argument(
        "--corpus-profile-id",
        choices=("canon_only_v1", "canon_plus_dss_apocrypha_v1"),
        default="canon_only_v1",
    )
    ap.add_argument("--output-raw", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--output-retry", type=Path, default=DEFAULT_RETRY)
    ap.add_argument(
        "--chronicle-signal-json",
        type=Path,
        default=DEFAULT_CHRONICLE_SIGNAL,
        help="Chronicle/news matched signal JSON source to inject into chronicle_mapping.",
    )
    ap.add_argument(
        "--chronicle-history-jsonl",
        type=Path,
        default=DEFAULT_CHRONICLE_HISTORY,
        help="Chronicle/news history JSONL source to inject into chronicle_mapping.",
    )
    ap.add_argument(
        "--registry-63779-json",
        type=Path,
        default=DEFAULT_63779,
        help="Computed 63779 registry JSON source for deep logos fields.",
    )
    ap.add_argument(
        "--morphology-registry-json",
        type=Path,
        default=DEFAULT_MORPH,
        help="Computed morphology registry JSON source for morphology layer field.",
    )
    ap.add_argument(
        "--raw-format",
        choices=("fenced", "json"),
        default="fenced",
        help="fenced adds prose + ```json block to exercise extractor.",
    )
    args = ap.parse_args()

    mkm_path = args.mkm_json if args.mkm_json.is_absolute() else ROOT / args.mkm_json
    chronicle_signal_path = args.chronicle_signal_json if args.chronicle_signal_json.is_absolute() else ROOT / args.chronicle_signal_json
    chronicle_history_path = args.chronicle_history_jsonl if args.chronicle_history_jsonl.is_absolute() else ROOT / args.chronicle_history_jsonl
    registry_63779_path = args.registry_63779_json if args.registry_63779_json.is_absolute() else ROOT / args.registry_63779_json
    registry_morph_path = args.morphology_registry_json if args.morphology_registry_json.is_absolute() else ROOT / args.morphology_registry_json
    if not mkm_path.is_file():
        print(f"ERROR: missing mkm logos source: {mkm_path}")
        return 2
    mkm = _read_json(mkm_path)
    chronicle_signal = _read_json(chronicle_signal_path) if chronicle_signal_path.is_file() else None
    chronicle_history_rows = _read_jsonl(chronicle_history_path)
    registry_63779 = _read_json(registry_63779_path) if registry_63779_path.is_file() else None
    registry_morph = _read_json(registry_morph_path) if registry_morph_path.is_file() else None

    doc = build_logos_response_v2(
        mkm,
        corpus_profile_id=args.corpus_profile_id,
        chronicle_signal=chronicle_signal,
        chronicle_history_rows=chronicle_history_rows,
        registry_63779=registry_63779,
        registry_morph=registry_morph,
    )
    normalized = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    raw_out = args.output_raw if args.output_raw.is_absolute() else ROOT / args.output_raw
    retry_out = args.output_retry if args.output_retry.is_absolute() else ROOT / args.output_retry
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    retry_out.parent.mkdir(parents=True, exist_ok=True)

    if args.raw_format == "fenced":
        raw_text = (
            "MKM Logos auto-generated candidate (raw)\n\n"
            "```json\n"
            f"{normalized.rstrip()}\n"
            "```\n"
        )
    else:
        raw_text = normalized
    raw_out.write_text(raw_text, encoding="utf-8")
    retry_out.write_text(normalized, encoding="utf-8")

    print(json.dumps({"ok": True, "raw": str(raw_out), "retry": str(retry_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
