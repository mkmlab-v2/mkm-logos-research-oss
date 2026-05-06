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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def build_logos_response_v2(mkm: dict[str, Any], *, corpus_profile_id: str) -> dict[str, Any]:
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

    chronicle_rows: list[dict[str, str]] = []
    for item in evidence[:3]:
        if not isinstance(item, dict):
            continue
        note = str(item.get("note") or "evidence_ref")
        ref = str(item.get("ref") or "")
        if not ref:
            continue
        chronicle_rows.append(
            {
                "summary": f"{note} 관측 포인터",
                "period_or_ref": "ops_snapshot_latest",
                "evidence_pointer": ref,
                "confidence_band": "mid",
            }
        )
    if not chronicle_rows:
        chronicle_rows.append(
            {
                "summary": "기본 운영 포인터",
                "period_or_ref": "ops_snapshot_latest",
                "evidence_pointer": "docs/final/artifacts/mkm_logos_response_v2_latest.json",
                "confidence_band": "low",
            }
        )

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
            f"{template_text} (reason: {reason}) 본 문서는 연구 해설이며 실행 신호로 사용하지 않는다."
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
        "--raw-format",
        choices=("fenced", "json"),
        default="fenced",
        help="fenced adds prose + ```json block to exercise extractor.",
    )
    args = ap.parse_args()

    mkm_path = args.mkm_json if args.mkm_json.is_absolute() else ROOT / args.mkm_json
    if not mkm_path.is_file():
        print(f"ERROR: missing mkm logos source: {mkm_path}")
        return 2
    mkm = _read_json(mkm_path)

    doc = build_logos_response_v2(mkm, corpus_profile_id=args.corpus_profile_id)
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
