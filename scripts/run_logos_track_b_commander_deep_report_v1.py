#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logos Track B — 지휘관 심층 리포트 v1 (결정론 골격만, LLM 없음).

기존 Logos 독립 렌즈 + (선택) 융합 스텁·시장 사상 렌즈 메타를 읽어
5개 핵심 축 섹션 스텁을 생성한다. 본문 해석·다단 검색은 지휘관/후속 에이전트.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.track_b_commander_gate_v1 import HUMAN_COMMANDER_GATE_V1

DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_FUSION = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "docs" / "final" / "artifacts" / "market_sasang_lens_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_track_b_commander_deep_report_latest.json"
DEFAULT_DISTILL = ROOT / "docs" / "final" / "artifacts" / "logos_deep_research_distill_latest.json"
ENVELOPE_PATH = ROOT / "data" / "logos" / "logos_track_b_commander_deep_report_envelope_v1.json"

ARTIFACT_SCHEMA = "logos_track_b_commander_deep_report_v1"
ENGINE_VERSION = "1.1.0"


def load_envelope() -> dict[str, Any]:
    doc = json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))
    if doc.get("schema") != "logos_track_b_commander_deep_report_envelope_v1":
        raise ValueError("envelope schema must be logos_track_b_commander_deep_report_envelope_v1")
    return doc


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _is_real_verse_id(vid: str) -> bool:
    return bool(vid.strip()) and not vid.strip().startswith("sample-")


def _verse_ids_from_distill(distill_doc: dict[str, Any] | None, *, limit: int = 32) -> list[str]:
    if not distill_doc:
        return []
    out: list[str] = []
    refs = distill_doc.get("evidence_refs")
    if isinstance(refs, list):
        for er in refs:
            if isinstance(er, dict):
                vid = er.get("verse_id")
                if isinstance(vid, str) and _is_real_verse_id(vid):
                    out.append(vid.strip())
    return out[:limit]


def _verse_ids_from_logos(doc: dict[str, Any], *, limit: int = 24) -> list[str]:
    out: list[str] = []
    refs = doc.get("evidence_refs")
    if isinstance(refs, list):
        for er in refs:
            if isinstance(er, dict):
                vid = er.get("verse_id")
                if isinstance(vid, str) and vid.strip() and _is_real_verse_id(vid):
                    out.append(vid.strip())
    return out[:limit]


def _graph_paths_from_distill(distill_doc: dict[str, Any] | None, *, limit: int = 8) -> list[dict[str, Any]]:
    if not distill_doc:
        return []
    paths = distill_doc.get("graph_paths")
    if not isinstance(paths, list):
        return []
    return [p for p in paths if isinstance(p, dict)][:limit]


def _build_axes(
    logos_doc: dict[str, Any],
    fusion_doc: dict[str, Any] | None,
    market_doc: dict[str, Any] | None,
    distill_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph_paths = _graph_paths_from_distill(distill_doc)
    distill_ids = _verse_ids_from_distill(distill_doc)
    if distill_ids:
        verse_ids = list(distill_ids)
        for p in graph_paths:
            for vid in p.get("verse_ids") or []:
                if isinstance(vid, str) and _is_real_verse_id(vid) and vid not in verse_ids:
                    verse_ids.append(vid)
    else:
        verse_ids = _verse_ids_from_logos(logos_doc)
        for p in graph_paths:
            for vid in p.get("verse_ids") or []:
                if isinstance(vid, str) and _is_real_verse_id(vid) and vid not in verse_ids:
                    verse_ids.append(vid)
    n_ev = len(verse_ids)
    scores = logos_doc.get("scores") if isinstance(logos_doc.get("scores"), dict) else {}
    ds = float(scores.get("direction_score") or 0.0)
    cf = float(scores.get("confidence") or 0.0)

    cs = (fusion_doc or {}).get("consensus") if isinstance((fusion_doc or {}).get("consensus"), dict) else {}
    cons_sign = str(cs.get("consensus_sign") or "neutral")
    agr = cs.get("agreement_rate")

    ms_note = ""
    if market_doc and market_doc.get("schema") == "market_sasang_lens_v1":
        fb = market_doc.get("fusion_bridge") if isinstance(market_doc.get("fusion_bridge"), dict) else {}
        ms_note = (
            f"시장 사상 렌즈 방향 힌트={fb.get('direction_hint')!s}, "
            f"veto={bool((market_doc.get('veto') or {}).get('force_hold'))}."
        )

    return {
        "axis_01_original_language_semantics": {
            "title_ko": "원어·어휘층 (레마·의미역)",
            "deterministic_stub_ko": (
                f"[HYPO] 본 축은 히브리/헬라 어근·의미역 후보를 원문 근거와 함께 정리하는 자리다. "
                f"현재 배치에서 evidence_refs 기준 앵커 수={n_ev}. "
                "게마트리아·숫자 읽기는 동일 문단에 불확실성 라벨을 붙일 것."
            ),
            "evidence_verse_ids": verse_ids,
        },
        "axis_02_genre_register": {
            "title_ko": "문맥·문학 장르",
            "deterministic_stub_ko": (
                "[HYPO] 시·법·예언·편지 등 장르 약속에 따른 허용 해석 범위를 여기에 적는다. "
                f"Logos 렌즈 direction_score={ds:.6f}, confidence={cf:.6f}는 배치 요약일 뿐 교리 단정이 아님."
            ),
        },
        "axis_03_cross_reference_echo": {
            "title_ko": "교차 참조·구조적 에코",
            "deterministic_stub_ko": (
                "동일 공동체·동일 문헌 군 내 반복 모티프와 verse_id 앵커를 표 형태로 확장한다. "
                f"graph_paths(증류)={len(graph_paths)}. "
                f"샘플 verse_id: {', '.join(verse_ids[:8]) if verse_ids else '(없음)'}"
            ),
            "graph_path_count": len(graph_paths),
            "graph_path_sample_verse_ids": verse_ids[:16],
        },
        "axis_04_history_redaction_hypo": {
            "title_ko": "역사·편집·수용층 [HYPO]",
            "deterministic_stub_ko": (
                "[HYPO] 연대·편집층·수용사 추정은 가설로 두고, 확인 가능한 고고·문헌 근거만 병기한다."
            ),
        },
        "axis_05_lens_conflict_map": {
            "title_ko": "타 렌즈 충돌 지도",
            "deterministic_stub_ko": (
                f"융합 스텁 consensus_sign={cons_sign}, agreement_rate={agr!s}. "
                f"{ms_note} 명리·사상·로고스는 합선 금지—방향 불일치는 ‘충돌 지도’로만 기록."
            ),
        },
    }


def build_payload(
    *,
    logos_doc: dict[str, Any],
    fusion_doc: dict[str, Any] | None,
    market_doc: dict[str, Any] | None,
    logos_path: str,
    fusion_path: str,
    market_path: str,
    distill_doc: dict[str, Any] | None = None,
    distill_path: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    axes = _build_axes(logos_doc, fusion_doc, market_doc, distill_doc)
    env = load_envelope()
    labels = list(env.get("labels_default") or [])
    return {
        "schema": ARTIFACT_SCHEMA,
        "version": ENGINE_VERSION,
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autotrigger_forbidden": True,
        "labels": labels,
        "human_commander_gate_v1": dict(HUMAN_COMMANDER_GATE_V1),
        "envelope": {
            "schema": env.get("schema"),
            "version": env.get("version"),
            "source_track": env.get("source_track"),
            "hypothesis_tier": env.get("hypothesis_tier"),
            "human_review_required": env.get("human_review_required"),
            "disclaimer_ko": env.get("disclaimer_ko"),
            "manifest_pointer": env.get("manifest_pointer"),
        },
        "machine_role_ko": (
            "본 JSON은 골격·앵커·메타만 제공한다. 심층 서술·다단 검색·장문 생성은 "
            "지휘관 승인 하 Track B 후속 작업."
        ),
        "report_axes_v1": axes,
        "graph_paths_sample": _graph_paths_from_distill(distill_doc, limit=12),
        "distill_digest": {
            "path": distill_path,
            "evidence_ref_count": len((distill_doc or {}).get("evidence_refs") or []),
            "epistemic_uncertainty": (distill_doc or {}).get("epistemic_uncertainty"),
            "review_gate_status": ((distill_doc or {}).get("review_gate") or {}).get("status"),
        }
        if distill_doc
        else None,
        "inputs_digest": {
            "logos_lens_schema": logos_doc.get("schema"),
            "logos_lens_version": logos_doc.get("version"),
            "logos_input_path": logos_path,
            "fusion_stub_schema": (fusion_doc or {}).get("schema"),
            "fusion_stub_version": (fusion_doc or {}).get("version"),
            "fusion_input_path": fusion_path,
            "market_sasang_schema": (market_doc or {}).get("schema"),
            "market_sasang_input_path": market_path if market_doc else None,
        },
        "note": (
            "logos_track_b_commander_deep_report_v1: deterministic shell; no LLM; "
            "not live trigger; commander adopts or discards."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit Logos Track B commander deep-report skeleton v1.")
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--fusion", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--market-sasang", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--no-fusion", action="store_true", help="Ignore fusion stub file.")
    ap.add_argument("--no-market-sasang", action="store_true", help="Ignore market sasang lens file.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--distill-json", type=Path, default=None, help="Optional enriched distill JSON")
    args = ap.parse_args()

    logos_doc = _read_json(args.logos)
    if not logos_doc or logos_doc.get("schema") != "logos_independent_lens_v0":
        print(f"missing or invalid logos lens: {args.logos}")
        return 2

    fusion_doc = None if args.no_fusion else _read_json(args.fusion)
    market_doc = None if args.no_market_sasang else _read_json(args.market_sasang)

    distill_doc = _read_json(args.distill_json) if args.distill_json else None
    if args.distill_json and not distill_doc:
        print(f"warn: distill json missing or invalid: {args.distill_json}")

    payload = build_payload(
        logos_doc=logos_doc,
        fusion_doc=fusion_doc,
        market_doc=market_doc,
        logos_path=str(args.logos.resolve()),
        fusion_path=str(args.fusion.resolve()),
        market_path=str(args.market_sasang.resolve()),
        distill_doc=distill_doc,
        distill_path=str(args.distill_json.resolve()) if args.distill_json else None,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
