#!/usr/bin/env python3
"""Build era insight lattice JSON for v6 right pane ([HYPO], B-track, NON_GATING)."""
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

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_CHRONO = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)
OUT_MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_era_insight_lattice_v1.json"
)
OUT_ART = ROOT / "docs/final/artifacts/showroom_era_insight_lattice_v1_latest.json"
OUT_GENESIS = ROOT / "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json"

GENESIS_LEMMA_ROWS = [
    {
        "lemma_id": "H7225",
        "surface_form": "בְּרֵאשִׁ֖ית",
        "gloss_ko": "태초에",
        "hypothesis_class": "HYPO",
        "lemma_ssot": "heuristic_proxy",
    },
    {
        "lemma_id": "H1254",
        "surface_form": "בָּרָ֣א",
        "gloss_ko": "창조하셨다",
        "hypothesis_class": "HYPO",
        "lemma_ssot": "heuristic_proxy",
    },
]

FORBIDDEN_SUBSTRINGS = (
    "할루시네이션 0",
    "hallucination-free",
    "hallucination 0",
    "miss rate: 0",
    "100% 차단",
    "완벽한",
    "GO_SHOWROOM",
)

# PUBLIC_FACING §2 — no proprietary theory tokens on showroom lattice (api.jemaai.cloud).
PUBLIC_LATTICE_FORBIDDEN_INTERNAL = (
    "甲木",
    "금화",
    "금화교역",
    "보명지주",
    "병증약리",
    "보명지조",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _node_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(n["id"]): n for n in graph.get("nodes") or [] if n.get("id")}


def _evidence_for_highlight(
    highlight_ids: list[str],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for nid in highlight_ids:
        if str(nid).startswith("era::"):
            continue
        n = nodes.get(nid) or {}
        ref = canonical_verse_ref(str(n.get("ref") or n.get("label") or nid.split("::")[-1]))
        if not ref:
            continue
        is_stub = str(nid).startswith("showroom_era_verse::") or bool(n.get("schema") == "showroom_era_verse_node_v1")
        source = "showroom_stub" if is_stub else "corpus_graph"
        row = {
            "ref": ref,
            "node_id": nid,
            "source": source,
            "corpus_gap": is_stub,
        }
        snip = str(n.get("text_snippet_ko") or "").strip()
        if snip:
            row["snippet_ko"] = snip
        elif is_stub:
            row["snippet_ko"] = f"[corpus_pending] {ref} — showroom stub node; full corpus anchor pending."
        rows.append(row)
    return rows


def build_genesis_lattice(
    preset: dict[str, Any],
    graph: dict[str, Any],
    chrono: dict[str, Any] | None,
) -> dict[str, Any]:
    era_id = "genesis_order_and_fall"
    nodes = _node_by_id(graph)
    highlights = list(preset.get("highlight_node_ids") or [])
    evidence = _evidence_for_highlight(highlights, nodes)
    era = next((e for e in (chrono or {}).get("eras") or [] if e.get("era_id") == era_id), {})
    theme_tags = ", ".join(str(t) for t in (era.get("theme_tags") or preset.get("keywords") or [])[:4])

    gap_ko = (
        "창조(order) 클러스터와 타락(fall) 클러스터 사이의 **구조적 갭** — "
        "단일 인과·단일 공식으로 메우지 않음. [HYPO] bridge 질문만 제안."
    )
    gap_chips = [
        {
            "chip_id": "gap_order_fall",
            "label_ko": "order ↔ fall",
            "bridge_question_ko": "질서 선언(Gen.1)과 타락 서사(Gen.3) 사이를 한 공식으로 잇지 않는다 — 무엇이 관측만 가능한가?",
            "hypothesis_class": "HYPO",
        },
        {
            "chip_id": "gap_image_ethics",
            "label_ko": "image ↔ ethics",
            "bridge_question_ko": "인간 형상·창조 위임과 금지 계명 사이의 긴장 — 단일 도덕 공식으로 축소하지 않음.",
            "hypothesis_class": "HYPO",
        },
        {
            "chip_id": "gap_era_chronology",
            "label_ko": "era ↔ chronology",
            "bridge_question_ko": "연대기 era 허브와 절 단위 evidence path — community 요약과 local graph를 혼동하지 않음.",
            "hypothesis_class": "HYPO",
        },
    ]
    abstention = (
        "프리셋 매트릭스 밖 질의는 highlight·path를 비우고 abstention 카피만 출력. "
        "Dan.2 등 무관 클러스터로의 fallback 없음."
    )

    cards: list[dict[str, Any]] = [
        {
            "card_id": "field",
            "layer": "Field_Observation",
            "title_ko": "관측 국면 (display only)",
            "body_ko": (
                "쇼룸 전용 관측 프레임. regime_map 실물 게이트가 아니며 Final Action과 무관합니다. "
                "창세·타락 연대기 구간의 거시 서사 관측만 표시합니다."
            ),
            "badges": ["research_only", "NON_GATING", "display_only"],
            "gating_status": "NON_GATING",
            "display_only": True,
            "is_gating": False,
        },
        {
            "card_id": "logos",
            "layer": "Logos_Structure",
            "title_ko": "정경 근거 (Evidence path)",
            "body_ko": preset.get("answer_body_ko") or preset.get("answer_ko_product") or "",
            "badges": ["curated_preset", "matrix_bound"],
            "gating_status": "NON_GATING",
            "is_gating": False,
            "evidence_nodes": evidence,
        },
        {
            "card_id": "lemma",
            "layer": "L1_Lemma_Lexicon",
            "title_ko": "원어 코퍼스 지문 (heuristic proxy)",
            "body_ko": (
                "Gen.1.1 허브에 대한 교육용 Strong's proxy. "
                "lemma↔verse 대량 엣지는 Logos OL bridge Phase 1 GAP — morphology 검증 전."
            ),
            "badges": ["HYPO", "heuristic_proxy", "NON_GATING"],
            "gating_status": "NON_GATING",
            "is_gating": False,
            "lemma_rows": GENESIS_LEMMA_ROWS,
        },
        {
            "card_id": "parallel",
            "layer": "Parallel_Lenses",
            "title_ko": "보조 렌즈 슬롯 (비게이팅)",
            "body_ko": "보조 렌즈는 해설·비교용 placeholder이며 hot path·Final Action과 분리됩니다. 내부 이론·공식은 공개하지 않습니다.",
            "badges": ["NON_GATING", "HYPO", "placeholder"],
            "gating_status": "NON_GATING",
            "is_gating": False,
            "parallel_lenses": {
                "myeongri_ko": "[HYPO] 중기 방향 슬롯 — 관측 은유만, 레짐·가격 단정 없음.",
                "sasang_ko": "[HYPO] 단기 강도 슬롯 — wellness 메타포만, 임상·처방 단정 없음.",
            },
        },
        {
            "card_id": "gap",
            "layer": "Structural_Gap",
            "title_ko": "구조적 갭 · bridge 제안",
            "body_ko": gap_ko,
            "badges": ["HYPO", "research_only"],
            "gating_status": "NON_GATING",
            "is_gating": False,
            "gap_bridge_ko": gap_ko,
            "gap_chips": gap_chips,
        },
        {
            "card_id": "gate",
            "layer": "Abstention_Gate",
            "title_ko": "거절 회로 (matrix miss)",
            "body_ko": abstention,
            "badges": ["abstention", "matrix_bound"],
            "gating_status": "NON_GATING",
            "is_gating": False,
            "abstention_rule_ko": abstention,
            "verdict": "SHOWROOM_RENDER",
        },
    ]

    focus_map: dict[str, str] = {f"era::{era_id}": "field"}
    for ev in evidence:
        focus_map[str(ev["node_id"])] = "logos"
        if ev.get("corpus_gap"):
            focus_map[str(ev["node_id"])] = "logos"

    doc = {
        "schema_version": "showroom_era_insight_lattice_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "preset_id": str(preset.get("id") or f"era_{era_id}"),
        "era_id": era_id,
        "theme_tags": theme_tags,
        "cards": cards,
        "node_focus_map": focus_map,
        "reproducible_command": "py scripts/build_showroom_era_insight_lattice_v1.py",
    }
    return doc


def _assert_no_forbidden(doc: dict[str, Any]) -> None:
    blob = json.dumps(doc, ensure_ascii=False).lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad.lower() in blob:
            raise ValueError(f"forbidden substring in lattice: {bad}")
    for term in PUBLIC_LATTICE_FORBIDDEN_INTERNAL:
        if term in json.dumps(doc, ensure_ascii=False):
            raise ValueError(f"public lattice must not expose internal term: {term}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONO)
    ap.add_argument("--out-mvp", type=Path, default=OUT_MVP)
    ap.add_argument("--out-artifact", type=Path, default=OUT_ART)
    ap.add_argument("--out-genesis-artifact", type=Path, default=OUT_GENESIS)
    args = ap.parse_args()

    presets = _load(args.presets_json)
    graph = _load(args.slice_json)
    chrono = _load(args.chronology_json) if args.chronology_json.is_file() else None
    preset = next(
        (p for p in presets.get("presets") or [] if p.get("id") == "era_genesis_order_and_fall"),
        None,
    )
    if not preset:
        print("missing era_genesis_order_and_fall preset", file=sys.stderr)
        return 1

    doc = build_genesis_lattice(preset, graph, chrono)
    _assert_no_forbidden(doc)

    pack = {
        "schema_version": "showroom_era_insight_lattice_pack_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "research_only": True,
        "send_gate": "HOLD",
        "lattices": {
            "era_genesis_order_and_fall": doc,
        },
        "reproducible_command": doc["reproducible_command"],
    }

    text_pack = json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
    text_genesis = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_mvp.parent.mkdir(parents=True, exist_ok=True)
    args.out_mvp.write_text(text_pack, encoding="utf-8")
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(text_pack, encoding="utf-8")
    args.out_genesis_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_genesis_artifact.write_text(text_genesis, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out_mvp": str(args.out_mvp),
                "cards": len(doc["cards"]),
                "evidence_nodes": len(doc["cards"][1].get("evidence_nodes") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
