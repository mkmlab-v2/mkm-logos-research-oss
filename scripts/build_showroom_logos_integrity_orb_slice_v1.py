#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit showroom Logos Integrity Orb thin-slice JSON from ENTRY_13/16 supplements (NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENTRY13 = ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json"
DEFAULT_ENTRY16 = ROOT / "reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.json"
DEFAULT_GATE = ROOT / "docs/final/artifacts/cross_ref_waiting_queue_consolidated_gate_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/showroom_logos_integrity_orb_slice_v1.schema.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_integrity_orb_slice_v1.json"
)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/showroom_logos_integrity_orb_slice_v1_latest.json"

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "Integrity Orb는 사전 계산된 연구 스냅샷입니다. 실시간 LLM·종교적 단정·투자·실매매(Track A) "
        "근거가 아닙니다. verified_anchor가 없으면 Gap을 표시합니다 — 환각 없음을 절대 단정하지 마세요."
    ),
    "note_ko_product": (
        "Precomputed integrity trace · research_only · NON_GATING · gaps shown when anchor missing. "
        "Not investment advice · no live LLM."
    ),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _edge(src: str, dst: str, edge_type: str = "", weight: float = 1.0, on_path: bool = False) -> dict[str, Any]:
    return {"src": src, "dst": dst, "edge_type": edge_type, "weight": weight, "on_path": on_path}


def _node(
    nid: str,
    label: str,
    kind: str,
    *,
    label_ko: str | None = None,
    hub_score: float = 0.5,
    tier: str | None = None,
    ref: str | None = None,
    entry_id: str | None = None,
    status: str | None = None,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"id": nid, "label": label, "kind": kind, "hub_score": hub_score}
    if label_ko:
        row["label_ko"] = label_ko
    if tier:
        row["tier"] = tier
    if ref:
        row["ref"] = ref
    if entry_id:
        row["entry_id"] = entry_id
    if status:
        row["status"] = status
    if artifact_path:
        row["artifact_path"] = artifact_path
    return row


def build_graph(entry13: dict[str, Any], entry16: dict[str, Any], gate: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    nodes.append(_node("gate::fact_lock", "Fact-Lock", "gate", label_ko="Fact-Lock Integrity", hub_score=1.0, status="ACTIVE"))
    nodes.append(_node("gate::send_hold", "SEND HOLD", "gate", label_ko="send_gate HOLD", hub_score=0.9, status="HOLD"))
    nodes.append(
        _node(
            "gate::verified_anchor",
            "verified_anchor: 0",
            "gap",
            label_ko="verified_anchor 미달",
            hub_score=0.95,
            status="missing_anchor",
            tier="documented",
        )
    )
    edges.extend(
        [
            _edge("gate::fact_lock", "gate::send_hold", "rail_policy"),
            _edge("gate::fact_lock", "gate::verified_anchor", "integrity_check", on_path=True),
        ]
    )

    # ENTRY_13 cluster
    nodes.append(
        _node(
            "entry::ENTRY_13",
            "ENTRY_13",
            "entry",
            label_ko="ENTRY_13 · Ps.5.2",
            hub_score=0.92,
            entry_id="ENTRY_13",
            ref="Ps.5.2",
            artifact_path="reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json",
        )
    )
    shadow = entry13.get("commander_shadow") or {}
    nodes.append(
        _node(
            "witness::4Q98b",
            "4Q98b frg.1",
            "shadow",
            label_ko="4Q98b shadow witness",
            hub_score=0.88,
            ref=shadow.get("scroll", "4Q98b"),
            entry_id="ENTRY_13",
            status="commander_verified_shadow_witness",
            tier="shadow",
        )
    )
    nodes.append(
        _node(
            "witness::Ps5_8_9",
            "Ps.5.8-9",
            "witness",
            label_ko="Ps.5.8-9 (shadow verse)",
            hub_score=0.8,
            ref=entry13.get("shadow_verse_anchor", "Ps.5.8-9"),
            entry_id="ENTRY_13",
        )
    )
    nodes.append(
        _node(
            "gap::MT_Ps5_2",
            "MT Ps.5.2 v.2",
            "gap",
            label_ko="MT Ps.5.2 verified_anchor Gap",
            hub_score=0.85,
            ref="Ps.5.2",
            entry_id="ENTRY_13",
            status="missing_anchor",
        )
    )
    nodes.append(
        _node(
            "gap::11Q5",
            "11Q5 no Ps.5",
            "gap",
            label_ko="11Q5 Ps.5 부재",
            hub_score=0.7,
            status="missing_anchor",
            entry_id="ENTRY_13",
        )
    )
    nodes.append(
        _node(
            "hypo::4Q83",
            "4Q83 [HYPO]",
            "hypo",
            label_ko="4Q83 provisional",
            hub_score=0.55,
            tier="[HYPO]",
            entry_id="ENTRY_13",
        )
    )
    edges.extend(
        [
            _edge("entry::ENTRY_13", "witness::Ps5_8_9", "canonical_bench", on_path=True),
            _edge("witness::Ps5_8_9", "witness::4Q98b", "shadow_witness", on_path=True),
            _edge("entry::ENTRY_13", "gap::MT_Ps5_2", "verified_anchor_gap", on_path=True),
            _edge("entry::ENTRY_13", "gap::11Q5", "scroll_structure"),
            _edge("witness::4Q98b", "hypo::4Q83", "provisional_lexical"),
            _edge("entry::ENTRY_13", "gate::verified_anchor", "registry_check"),
        ]
    )

    # ENTRY_16 cluster
    nodes.append(
        _node(
            "entry::ENTRY_16",
            "ENTRY_16",
            "entry",
            label_ko="ENTRY_16 · Ezra.2.54",
            hub_score=0.9,
            entry_id="ENTRY_16",
            ref="Ezra.2.54",
            artifact_path="reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.json",
        )
    )
    nodes.append(
        _node(
            "witness::4Q117",
            "4Q117",
            "witness",
            label_ko="4Q117 (Ezra range)",
            hub_score=0.75,
            ref="4Q117",
            entry_id="ENTRY_16",
            status="extant_range_only",
        )
    )
    nodes.append(
        _node(
            "gap::Ezra_2_54",
            "Ezra.2.54 DSS line",
            "gap",
            label_ko="Ezra.2.54 missing_anchor",
            hub_score=0.9,
            ref="Ezra.2.54",
            entry_id="ENTRY_16",
            status="missing_anchor_until_source_update",
        )
    )
    nodes.append(
        _node(
            "witness::LXX_proxy",
            "LXX proxy",
            "hypo",
            label_ko="LXX/Swete proxy only",
            hub_score=0.45,
            tier="proxy_not_dss_line",
            entry_id="ENTRY_16",
        )
    )
    edges.extend(
        [
            _edge("entry::ENTRY_16", "witness::4Q117", "scroll_range", on_path=True),
            _edge("witness::4Q117", "gap::Ezra_2_54", "documented_gap", on_path=True),
            _edge("entry::ENTRY_16", "witness::LXX_proxy", "proxy_candidate"),
            _edge("entry::ENTRY_16", "gate::verified_anchor", "registry_check"),
            _edge("entry::ENTRY_16", "entry::ENTRY_13", edge_type="isolation_barrier"),
        ]
    )

    # Query anchor nodes (preset entry points)
    nodes.append(
        _node(
            "query::ps5_shadow",
            "Ps.5 shadow 질문",
            "query",
            label_ko="ENTRY_13 shadow 분석",
            hub_score=1.0,
            entry_id="ENTRY_13",
        )
    )
    nodes.append(
        _node(
            "query::ezra_gap",
            "Ezra.2.54 Gap 질문",
            "query",
            label_ko="ENTRY_16 waiting queue",
            hub_score=1.0,
            entry_id="ENTRY_16",
        )
    )
    edges.extend(
        [
            _edge("query::ps5_shadow", "entry::ENTRY_13", "user_query", on_path=True),
            _edge("query::ezra_gap", "entry::ENTRY_16", "user_query", on_path=True),
        ]
    )

    return nodes, edges


def build_presets(entry13: dict[str, Any], entry16: dict[str, Any]) -> list[dict[str, Any]]:
    shadow_preview = (entry13.get("commander_shadow") or {}).get("text_preview", "")[:80]
    return [
        {
            "id": "preset_entry_13_shadow",
            "entry_id": "ENTRY_13",
            "prompt_ko": "ENTRY_13: Ps.5.2 bench와 4Q98b shadow witness(Ps.5.8-9)의 학술적 연결",
            "answer_ko": (
                "[HYPO] **ENTRY_13**은 bench **Ps.5.2**입니다. Commander 승인 **shadow witness**는 "
                f"**4Q98b** frg.1 line 1 → **Ps.5.8-9**입니다.\n\n"
                f"미리보기: {shadow_preview}…\n\n"
                "**verified_anchor**는 **미달**입니다 — MT Ps.5.2 v.2에 대한 DSS line 앵커가 없습니다. "
                "11Q5는 Ps.1–~89를 보존하지 않습니다. 4Q83 등은 **[HYPO] provisional**만 허용됩니다.\n\n"
                "Ps.5 DSS 연구를 ENTRY_16(Ezra)에 합치지 마세요."
            ),
            "answer_ko_product": (
                "ENTRY_13 · bench Ps.5.2 · commander shadow 4Q98b → Ps.5.8-9. "
                "verified_anchor not achieved — gap displayed honestly. research_only · NON_GATING."
            ),
            "highlight_node_ids": [
                "query::ps5_shadow",
                "entry::ENTRY_13",
                "witness::Ps5_8_9",
                "witness::4Q98b",
                "gap::MT_Ps5_2",
                "gate::verified_anchor",
            ],
            "reasoning_path_v1": {
                "node_ids": [
                    "query::ps5_shadow",
                    "entry::ENTRY_13",
                    "witness::Ps5_8_9",
                    "witness::4Q98b",
                    "gap::MT_Ps5_2",
                    "gate::verified_anchor",
                ],
                "path_label_ko": "질문 → ENTRY_13 → shadow → 4Q98b → verified_anchor Gap",
            },
            "keywords": ["ENTRY_13", "Ps.5", "4Q98b", "shadow", "Ps.5.2"],
        },
        {
            "id": "preset_entry_16_gap",
            "entry_id": "ENTRY_16",
            "prompt_ko": "ENTRY_16: Ezra.2.54와 4Q117 범위 — DSS line 앵커가 없을 때 어떻게 보고하나?",
            "answer_ko": (
                "[HYPO] **ENTRY_16**은 **Ezra.2.54** waiting queue입니다. **4Q117**은 Ezra 구간 "
                "일부를 보존하나 **Ezra.2.54 DSS line witness**는 **missing_anchor_until_source_update** "
                "상태입니다.\n\n"
                "LXX/Swete는 **proxy**로만 분류 — DSS line 앵커가 아닙니다. "
                "manual lock은 approved이나 **missing_anchor lock**은 유지됩니다. "
                "CROSS_REF 자동 변경 없음 · commander apply 전까지 **documented_hold**.\n\n"
                "Ps.5.8-9 DSS 증거를 ENTRY_16에 매핑하는 것은 **금지**입니다."
            ),
            "answer_ko_product": (
                "ENTRY_16 · Ezra.2.54 · 4Q117 extant range · DSS line gap documented. "
                "LXX proxy only. send_gate HOLD. research_only · NON_GATING."
            ),
            "highlight_node_ids": [
                "query::ezra_gap",
                "entry::ENTRY_16",
                "witness::4Q117",
                "gap::Ezra_2_54",
                "gate::verified_anchor",
                "gate::send_hold",
            ],
            "reasoning_path_v1": {
                "node_ids": [
                    "query::ezra_gap",
                    "entry::ENTRY_16",
                    "witness::4Q117",
                    "gap::Ezra_2_54",
                    "gate::verified_anchor",
                    "gate::send_hold",
                ],
                "path_label_ko": "질문 → ENTRY_16 → 4Q117 → Documented Gap → HOLD",
            },
            "keywords": ["ENTRY_16", "Ezra", "4Q117", "missing_anchor", "waiting queue"],
        },
    ]


def build_slice(
    entry13_path: Path,
    entry16_path: Path,
    gate_path: Path,
) -> dict[str, Any]:
    entry13 = _load(entry13_path)
    entry16 = _load(entry16_path)
    gate = _load(gate_path) if gate_path.is_file() else {}

    nodes, edges = build_graph(entry13, entry16, gate)
    presets = build_presets(entry13, entry16)

    rail_status = {
        "send_gate": str(gate.get("send_gate") or entry13.get("send_gate") or "HOLD"),
        "verified_anchor_achieved": False,
        "waiting_queue_status": str(gate.get("waiting_queue_status") or "documented_hold"),
        "fact_lock_integrity": "ACTIVE",
        "lane": "track_b_hypo",
    }

    doc: dict[str, Any] = {
        "schema_version": "showroom_logos_integrity_orb_slice_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disclaimer": DISCLAIMER,
        "rail_status": rail_status,
        "nodes": nodes,
        "edges": edges,
        "presets": presets,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "preset_count": len(presets),
        },
        "upstream_artifacts": [
            str(entry13_path.relative_to(ROOT)).replace("\\", "/"),
            str(entry16_path.relative_to(ROOT)).replace("\\", "/"),
            str(gate_path.relative_to(ROOT)).replace("\\", "/") if gate_path.is_file() else "",
        ],
        "reproduce": "py scripts/build_showroom_logos_integrity_orb_slice_v1.py",
    }
    doc["upstream_artifacts"] = [p for p in doc["upstream_artifacts"] if p]
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build showroom Logos Integrity Orb slice JSON")
    ap.add_argument("--entry13", type=Path, default=DEFAULT_ENTRY13)
    ap.add_argument("--entry16", type=Path, default=DEFAULT_ENTRY16)
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--skip-schema-validate", action="store_true")
    args = ap.parse_args()

    for label, path in [("entry13", args.entry13), ("entry16", args.entry16)]:
        if not path.is_file():
            print(f"{label} missing: {path}", file=sys.stderr)
            return 2

    try:
        doc = build_slice(args.entry13, args.entry16, args.gate)
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    if not args.skip_schema_validate:
        if not args.schema.is_file():
            print(f"schema missing: {args.schema}", file=sys.stderr)
            return 2
        try:
            _validate(doc, args.schema)
        except Exception as exc:  # noqa: BLE001
            print(f"schema validate failed: {exc}", file=sys.stderr)
            return 1

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(payload, encoding="utf-8")
    print(
        f"Wrote {args.out_json} nodes={doc['stats']['node_count']} "
        f"presets={doc['stats']['preset_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
