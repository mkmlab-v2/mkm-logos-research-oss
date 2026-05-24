#!/usr/bin/env python3
"""Read-only bridge: cross-lens RAG fusion + 4RAG/sphere graph pointers for commander Telegram."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

HUB_TOPOLOGY = "https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html"
HUB_MKMLIFE = "https://mkmlife.com/oracle-sphere"
HUB_LOGOS_V6 = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"

CROSS_LENS_PATH = "docs/final/artifacts/cross_lens_rag_fusion_latest.json"
SPHERE_PATH = "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _rag_layer_counts(resolved: Dict[str, Any]) -> str:
    parts: List[str] = []
    for layer in ("lexical", "semantic", "temporal", "constitutional"):
        rows = resolved.get(layer) or []
        if not isinstance(rows, list):
            continue
        present = sum(1 for r in rows if isinstance(r, dict) and r.get("present"))
        parts.append(f"{layer[:4]} {present}/{len(rows)}")
    return " · ".join(parts) if parts else "—"


def build_cross_lens_telegram_lines(workspace: Path = ROOT) -> List[str]:
    doc = _read_json(workspace / CROSS_LENS_PATH)
    if not doc or doc.get("schema") != "cross_lens_rag_fusion_v1":
        return ["  (cross-lens RAG 미갱신 — build_cross_lens_rag_fusion_v1.py)"]

    matrix = doc.get("cross_lens_conflict_matrix") or {}
    signal = doc.get("signal_light") or {}
    lines: List[str] = [
        "  3렌즈+RAG 융합 [HYPO·관측·NON_GATING]",
        f"  합의 {matrix.get('agreement_rate', '—')} · 다수 {matrix.get('majority_sign', '—')} "
        f"· 소수 {', '.join(matrix.get('minority_lenses') or []) or '—'}",
        f"  신호등 {signal.get('status', '—')} · veto_hold={doc.get('final_gate_panel', {}).get('veto_force_hold', False)}",
    ]
    snaps = []
    for row in doc.get("lens_snapshots") or []:
        if not isinstance(row, dict) or not row.get("available"):
            continue
        lid = row.get("lens_id")
        if lid in ("myeongni", "sasang", "logos", "market_myeongni"):
            snaps.append(f"{lid}={row.get('direction_sign')}({row.get('confidence')})")
    if snaps:
        lines.append(f"  렌즈: {' · '.join(snaps[:5])}")
    lines.append("  경계: 실매매·Track A 자동합선 없음")
    return lines


def build_sphere_rag_viz_telegram_lines(workspace: Path = ROOT) -> List[str]:
    doc = _read_json(workspace / SPHERE_PATH)
    if not doc or doc.get("schema") != "three_lens_sphere_envelope_v1":
        return [
            "  (4RAG·그래프 포인터 미갱신 — assemble_three_lens_sphere_envelope_v1.py)",
            f"  토폴로지(고정): {HUB_TOPOLOGY}",
        ]

    hubs = doc.get("hub_links") or {}
    gv = doc.get("graph_viz") or {}
    resolved = doc.get("rag_layers_resolved") or {}
    final_raw = doc.get("final_action")
    if isinstance(final_raw, str):
        final_label = final_raw
    elif isinstance(final_raw, dict):
        final_label = final_raw.get("label_ko", final_raw.get("action", "—"))
    else:
        final_label = "—"
    lines: List[str] = [
        "  4RAG 포인터(교육용·런타임 엔진 아님) [HYPO]",
        f"  레이어 present: {_rag_layer_counts(resolved)}",
        f"  그래프 노드≈{gv.get('node_count_display', '—')} · slice={bool(gv.get('graph_slice_path'))}",
        f"  구슬 final={final_label}",
        f"  시각화: {hubs.get('jemaai_meaning_topology_graph') or HUB_TOPOLOGY}",
        f"  mkmlife: {hubs.get('mkmlife_oracle_sphere') or HUB_MKMLIFE}",
        f"  logos v6: {hubs.get('jemaai_logos_v6_product') or HUB_LOGOS_V6}",
    ]
    return lines


def append_rag_viz_to_body_lines(body_lines: List[str], *, workspace: Path = ROOT) -> None:
    body_lines.extend(["", "  ▸ cross-lens RAG (읽기전용)", *build_cross_lens_telegram_lines(workspace)])
    body_lines.extend(["", "  ▸ 4RAG·그래프 허브", *build_sphere_rag_viz_telegram_lines(workspace)])
