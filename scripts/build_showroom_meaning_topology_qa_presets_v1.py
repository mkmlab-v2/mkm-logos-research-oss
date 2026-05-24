#!/usr/bin/env python3
"""Build showroom Q&A preset pack from meaning topology graph slice ([HYPO] demo only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_CHRONOLOGY = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)
OUT_MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
OUT_ART = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _nodes_by_kind(doc: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"verse": [], "theme": [], "regime": [], "other": []}
    for n in doc.get("nodes") or []:
        k = str(n.get("kind") or "other")
        out.setdefault(k, []).append(str(n["id"]))
    return out


def _daniel_aramaic_ids(doc: dict) -> list[str]:
    ids: list[str] = []
    for n in doc.get("nodes") or []:
        if n.get("kind") != "verse":
            continue
        ref = str(n.get("ref") or n.get("label") or "")
        if ref.startswith("Dan.2."):
            ids.append(str(n["id"]))
    return ids


def _era_presets(chrono: dict | None, doc: dict) -> list[dict]:
    if not chrono:
        return []
    node_ids = {str(n["id"]) for n in doc.get("nodes") or []}
    out: list[dict] = []
    for era in chrono.get("eras") or []:
        refs = [r for r in (era.get("verse_refs") or []) if r in node_ids]
        era_nid = f"era::{era.get('era_id')}"
        highlights = list(dict.fromkeys(refs + ([era_nid] if era_nid in node_ids else [])))
        if not highlights and not refs:
            highlights = [str(n["id"]) for n in (doc.get("nodes") or []) if n.get("kind") == "theme"][:2]
        label = str(era.get("label_ko") or era.get("era_id") or "")
        notes = str(era.get("notes_ko") or "")[:280]
        body = f"[HYPO] 연대기 **{label}** 구간입니다. {notes}".strip()
        out.append(
            {
                "id": f"era_{era.get('era_id', 'x')}",
                "prompt_ko": label,
                "answer_ko": f"{body} 투자·실매매·확정 예언·신학적 단정이 아닙니다.",
                "answer_ko_product": body,
                "highlight_node_ids": highlights,
                "keywords": [str(era.get("era_id") or ""), label[:12]],
            }
        )
    return out


def build_presets(doc: dict, *, chrono: dict | None = None) -> dict:
    by_kind = _nodes_by_kind(doc)
    daniel = _daniel_aramaic_ids(doc)
    theme_ids = by_kind.get("theme") or []
    regime_ids = by_kind.get("regime") or []
    hub = theme_ids + regime_ids + daniel[:12]

    return {
        "schema_version": "showroom_meaning_topology_qa_presets_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "no_trade_signals": True,
            "note_ko": "데모 프리셋 응답입니다. 실시간 LLM·실매매·종교적 단정이 아닙니다.",
            "note_ko_product": "Curated preset · research_only · NON_GATING · not investment advice.",
        },
        "graph_slice_path": "showroom_meaning_topology_graph_slice_v1.json",
        "presets": [
            {
                "id": "p1_empire_transition",
                "prompt_ko": "제국·왕조 전환(imperial / empire transition)과 연결된 구절은?",
                "answer_ko": (
                    "[HYPO] insight 허브 기준으로 **imperial_transition** 테마와 **empire_transition** "
                    "레짐이 다니엘 2장 구절 클러스터와 엣지로 연결됩니다. "
                    "이 화면은 연구용 부분 그래프이며 투자·매매·신학적 진리 단정이 아닙니다."
                ),
                "answer_ko_product": (
                    "[HYPO] **imperial_transition** 테마와 **empire_transition** 레짐이 "
                    "다니엘 2장 구절 클러스터와 그래프 엣지로 연결됩니다."
                ),
                "highlight_node_ids": list(
                    dict.fromkeys(theme_ids + regime_ids + daniel)
                ),
                "keywords": ["제국", "왕조", "empire", "imperial", "transition", "다니엘", "daniel"],
            },
            {
                "id": "p2_daniel2_cluster",
                "prompt_ko": "다니엘 2장(10–19절) 주변 구절만 보여줘",
                "answer_ko": (
                    "[HYPO] 아람어·히브리 렌즈 **Dan.2.10–Dan.2.19** 구절 노드와 "
                    "cross_lens_confirm 엣지가 강조됩니다. 전체 1,192노드 그래프가 아닌 **캡된 서브그래프**입니다."
                ),
                "highlight_node_ids": daniel,
                "keywords": ["다니엘", "dan.2", "daniel", "10", "19", "구절"],
            },
            {
                "id": "p3_theme_regime",
                "prompt_ko": "테마(theme)와 레짐(regime) 허브만 설명해줘",
                "answer_ko": (
                    "[HYPO] **theme::imperial_transition** · **regime::empire_transition** 두 허브가 "
                    "시드 후보이며, 주변 verse 노드로 의미 연결이 투영됩니다. 운영 게이트·주문 트리거와 무관합니다."
                ),
                "answer_ko_product": (
                    "[HYPO] **theme::imperial_transition** · **regime::empire_transition** 허브와 "
                    "연결된 verse 노드로 의미 경로가 투영됩니다."
                ),
                "highlight_node_ids": theme_ids + regime_ids,
                "keywords": ["테마", "레짐", "theme", "regime", "허브"],
            },
            {
                "id": "p4_full_map",
                "prompt_ko": "전체 부분 그래프 구조를 한눈에 보여줘",
                "answer_ko": (
                    f"[HYPO] 현재 슬라이스는 **{doc.get('stats', {}).get('node_count', '?')}노드 · "
                    f"{doc.get('stats', {}).get('edge_count', '?')}엣지**입니다. "
                    "verse·theme·regime 종류별 색으로 구분됩니다."
                ),
                "highlight_node_ids": [str(n["id"]) for n in (doc.get("nodes") or [])],
                "keywords": ["전체", "구조", "망", "그래프", "overview"],
            },
        ] + _era_presets(chrono, doc),
        "fallback": {
            "answer_ko": (
                "[HYPO] 질문과 키워드가 프리셋과 맞지 않습니다. 왼쪽 **제안 질문**을 선택하거나 "
                "「제국」「다니엘」「theme」 등을 포함해 보세요. 본선 Q&A API 연동 전 **데모 프리셋**입니다."
            ),
            "highlight_node_ids": hub[:8],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--no-chronology", action="store_true")
    ap.add_argument("--out-mvp", type=Path, default=OUT_MVP)
    ap.add_argument("--out-artifact", type=Path, default=OUT_ART)
    args = ap.parse_args()
    doc = _load(args.slice_json)
    chrono = None
    if not args.no_chronology and args.chronology_json.is_file():
        chrono = _load(args.chronology_json)
    payload = build_presets(doc, chrono=chrono)
    from compute_logos_reasoning_path_v1 import attach_paths_to_presets

    payload = attach_paths_to_presets(payload, doc)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.out_mvp.parent.mkdir(parents=True, exist_ok=True)
    args.out_mvp.write_text(text, encoding="utf-8")
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "out_mvp": str(args.out_mvp), "presets": len(payload["presets"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
