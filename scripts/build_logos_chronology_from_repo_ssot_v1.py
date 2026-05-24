#!/usr/bin/env python3
"""Build logos_chronology_v1_latest.json from in-repo SSOT (symbolic map, regime_map, showroom graph).

Does not invent commander-only narrative. Synthesizes [HYPO] observational eras and modern bridges
from logos_symbolic_event_map_v1, data/regimes/regime_map.json, and showroom meaning-topology slice.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SYMBOLIC_PATH = ROOT / "docs/final/artifacts/logos_symbolic_event_map_v1.json"
REGIME_PATH = ROOT / "data/regimes/regime_map.json"
GRAPH_SLICE_PATH = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"

POLICY = {
    "research_only": True,
    "non_gating": True,
    "no_trading_signal": True,
    "no_prophecy_certainty": True,
}

# symbol_id (logos_symbolic_event_map_v1) -> era definition
SYMBOL_ERAS: dict[str, dict[str, Any]] = {
    "exodus_liberation": {
        "era_id": "exodus_passage",
        "label_ko": "출애굽·해방 통과",
        "label_en": "Exodus liberation arc",
        "time": {"relative_phase": "exodus_liberation_arc"},
        "theme_tags": ["liberation", "passover", "boundary_crossing"],
        "verse_refs": ["aramaic::Exod.12.13", "aramaic::Exod.14.21"],
        "regime_tags_observational": ["empire_transition"],
        "notes_ko": "symbolic_event_map.exodus_liberation 키워드 매핑. 구조적 해방·경계 통과 은유; 시장 방향 단정 아님.",
    },
    "babel_confusion": {
        "era_id": "babel_dispersion",
        "label_ko": "바벨·언어·조율 붕괴",
        "label_en": "Babel coordination break",
        "theme_tags": ["confusion", "coordination_break", "volatility"],
        "verse_refs": ["aramaic::Gen.11.7"],
        "regime_tags_observational": ["caution", "risk"],
        "notes_ko": "symbolic_event_map.babel_confusion. 신용·지정학 키워드와의 상징 정렬만; 인과 단정 없음.",
    },
    "joseph_famine_storage": {
        "era_id": "joseph_storage_arc",
        "label_ko": "요셉·저장·기근 대비",
        "label_en": "Joseph storage against scarcity",
        "theme_tags": ["storage", "scarcity", "liquidity"],
        "verse_refs": ["aramaic::Gen.41.35", "aramaic::Gen.41.48"],
        "regime_tags_observational": ["imf", "caution"],
        "notes_ko": "symbolic_event_map.joseph_famine_storage (apocrypha lane weight 0.6). 유동성·소비 둔화 관측 태그.",
    },
    "jubilee_relief": {
        "era_id": "jubilee_relief_arc",
        "label_ko": "희년·부채·완화",
        "label_en": "Jubilee debt relief (DSS-weighted)",
        "theme_tags": ["jubilee", "debt_relief", "policy_easing"],
        "verse_refs": ["aramaic::Lev.25.10"],
        "regime_tags_observational": ["stability"],
        "notes_ko": "symbolic_event_map.jubilee_relief (dss lane). 긴축 완화·재고 키워드 상징층.",
    },
}

# Extra era from showroom graph slice / Q&A presets (Dan.2 cluster)
DANIEL_ERA: dict[str, Any] = {
    "era_id": "daniel_empire_metals",
    "label_ko": "다니엘 2·제국·금속 상 전환",
    "label_en": "Daniel 2 empire-metals transition",
    "time": {"relative_phase": "daniel_2_10_35_arc"},
    "theme_tags": ["imperial_transition", "empire_transition", "succession"],
    "verse_refs": [
        "aramaic::Dan.2.31",
        "aramaic::Dan.2.32",
        "aramaic::Dan.2.33",
        "aramaic::Dan.2.34",
        "aramaic::Dan.2.35",
        "aramaic::Dan.2.10",
        "aramaic::Dan.2.19",
    ],
    "regime_tags_observational": ["empire_transition", "it_bubble"],
    "notes_ko": "showroom_meaning_topology_qa_presets + graph_slice theme::imperial_transition / regime::empire_transition.",
}

# (era_id, bridge_kind, target_key, weight, rationale_ko)
BRIDGE_SPECS: list[tuple[str, str, str, float, str]] = [
    (
        "exodus_passage",
        "chronology_window",
        "post_gfc_repair",
        1.0,
        "post_gfc_repair 윈도우(2009–2014)와 회복·돌파 키워드의 구조적 유사 관측 [HYPO].",
    ),
    (
        "babel_dispersion",
        "regime_fingerprint",
        "lehman",
        0.9,
        "coordination_break vs lehman 레짐 지문 shadow 비교 (regime_map.lehman).",
    ),
    (
        "babel_dispersion",
        "chronology_window",
        "pandemic_shock",
        0.75,
        "pandemic_shock 윈도우와 변동성·risk-off 키워드 정렬 관측.",
    ),
    (
        "joseph_storage_arc",
        "regime_fingerprint",
        "imf",
        0.85,
        "저장·유동성 키워드 vs imf 레짐 관측 태그 (regime_map.imf).",
    ),
    (
        "jubilee_relief_arc",
        "chronology_window",
        "rate_hike_cycle",
        0.8,
        "rate_hike_cycle(2022–2024)와 긴축·완화 서사의 구조 비교용 [HYPO].",
    ),
    (
        "daniel_empire_metals",
        "regime_fingerprint",
        "it_bubble",
        0.88,
        "제국·금속 상승 서사 vs it_bubble 레짐 지문 (regime_map.it_bubble).",
    ),
    (
        "daniel_empire_metals",
        "regime_fingerprint",
        "covid",
        0.7,
        "급격한 판 전환·불확실성 vs covid 레짐 shadow.",
    ),
    (
        "daniel_empire_metals",
        "theme_only",
        "imperial_transition_hub",
        1.0,
        "theme::imperial_transition 허브만 — 주문·레짐 게이트 무관.",
    ),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_symbol_ids(symbolic: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for sym in symbolic.get("symbols") or []:
        if isinstance(sym, dict) and sym.get("symbol_id"):
            out.add(str(sym["symbol_id"]))
    return out


def _load_window_ids(symbolic: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for w in symbolic.get("chronology_windows") or []:
        if isinstance(w, dict) and w.get("window_id"):
            out.add(str(w["window_id"]))
    return out


def _load_regime_ids(regime_map: dict[str, Any]) -> set[str]:
    regimes = regime_map.get("regimes") or {}
    if not isinstance(regimes, dict):
        return set()
    return {str(k) for k in regimes.keys() if k and k != "unknown"}


def _graph_has_daniel_slice(path: Path) -> bool:
    if not path.is_file():
        return False
    doc = _read_json(path)
    nodes = doc.get("nodes") or []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or n.get("node_id") or "")
        if "Dan.2." in nid or nid in ("theme::imperial_transition", "regime::empire_transition"):
            return True
    return False


def _build_eras(symbol_ids: set[str], include_daniel: bool) -> list[dict[str, Any]]:
    eras: list[dict[str, Any]] = []
    for sid, template in SYMBOL_ERAS.items():
        if sid not in symbol_ids:
            continue
        era = dict(template)
        era["interpretation_class"] = "[HYPO]"
        eras.append(era)
    if include_daniel:
        daniel = dict(DANIEL_ERA)
        daniel["interpretation_class"] = "[HYPO]"
        eras.append(daniel)
    return eras


def _build_bridges(
    era_ids: set[str],
    window_ids: set[str],
    regime_ids: set[str],
) -> list[dict[str, Any]]:
    bridges: list[dict[str, Any]] = []
    for spec in BRIDGE_SPECS:
        era_id, kind, target, weight, rationale = spec
        if era_id not in era_ids:
            continue
        if kind == "theme_only":
            bridges.append(
                {
                    "era_id": era_id,
                    "bridge_kind": "theme_only",
                    "interpretation_class": "[HYPO]",
                    "resonance_weight": weight,
                    "rationale_ko": rationale,
                }
            )
            continue
        if kind == "chronology_window" and target not in window_ids:
            continue
        if kind == "regime_fingerprint" and target not in regime_ids:
            continue
        row: dict[str, Any] = {
            "era_id": era_id,
            "bridge_kind": kind,
            "interpretation_class": "[HYPO]",
            "resonance_weight": weight,
            "rationale_ko": rationale,
        }
        if kind == "chronology_window":
            row["window_id"] = target
        else:
            row["regime_id"] = target
        bridges.append(row)
    return bridges


def build_chronology(
    *,
    symbolic_path: Path = SYMBOLIC_PATH,
    regime_path: Path = REGIME_PATH,
    graph_slice_path: Path = GRAPH_SLICE_PATH,
) -> dict[str, Any]:
    symbolic = _read_json(symbolic_path)
    regime_map = _read_json(regime_path)
    symbol_ids = _load_symbol_ids(symbolic)
    window_ids = _load_window_ids(symbolic)
    regime_ids = _load_regime_ids(regime_map)
    include_daniel = _graph_has_daniel_slice(graph_slice_path)
    eras = _build_eras(symbol_ids, include_daniel)
    era_ids = {str(e["era_id"]) for e in eras}
    bridges = _build_bridges(era_ids, window_ids, regime_ids)
    matched = sorted(symbol_ids & set(SYMBOL_ERAS.keys()))
    source_note = (
        f"SSOT build: symbolic_map({len(matched)} symbols), regime_map, graph_slice "
        f"daniel={include_daniel}; builder=build_logos_chronology_from_repo_ssot_v1.py. "
        "Commander table may supersede."
    )[:512]
    return {
        "schema": "logos_chronology_v1",
        "schema_version": "1.0.0",
        "generated_at_utc": _now(),
        "source_note": source_note,
        "policy": POLICY,
        "hypothesis_tier": "[HYPO]",
        "eras": eras,
        "modern_bridges": bridges,
        "merge_targets": {
            "logos_symbolic_event_map_v1": "docs/final/artifacts/logos_symbolic_event_map_v1.json",
            "bible_meaning_graph_nodes_jsonl": "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl",
            "bible_meaning_graph_edges_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl",
        },
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Build logos_chronology_v1_latest.json from repo SSOT.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--symbolic-map", type=Path, default=SYMBOLIC_PATH)
    ap.add_argument("--regime-map", type=Path, default=REGIME_PATH)
    ap.add_argument("--graph-slice", type=Path, default=GRAPH_SLICE_PATH)
    args = ap.parse_args()
    doc = build_chronology(
        symbolic_path=args.symbolic_map,
        regime_path=args.regime_map,
        graph_slice_path=args.graph_slice,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    _write_json(out, doc)
    print(str(out.resolve()))
    print(f"eras={len(doc['eras'])} bridges={len(doc['modern_bridges'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
