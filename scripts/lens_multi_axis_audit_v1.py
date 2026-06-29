#!/usr/bin/env python3
"""Multi-axis audit envelopes for myeongni/sasang — shell-only (no GraphRAG merge).

Borrow Logos subgraph *audit frame* (evidence_refs, axis separation, lint) without
invoking graph routers or creating semantic edges between lenses.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_SUBSTRINGS = (
    "단일 만물이론",
    "통일장 완성",
    "toe complete",
    "theory of everything",
    "graphrag merge",
    "semantic edge",
    "당신의 내일 운명",
    "반드시 오른다",
    "반드시 내린다",
    "100% 확정",
    "track a에 자동 합선",
    "실매매 트리거 활성",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"graph\s*rag.*명리", re.I),
    re.compile(r"graph\s*rag.*사상", re.I),
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _axis(axis_id: str, kind: str, payload: dict[str, Any], *, note: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {
        "axis_id": axis_id,
        "kind": kind,
        "payload": payload,
    }
    if note:
        row["note"] = note
    return row


def extract_myeongni_axes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    stream = doc.get("myeongri_stream_outputs") if isinstance(doc.get("myeongri_stream_outputs"), dict) else {}
    quant = doc.get("myeongni_b_track_quant_block_v0")
    adv = doc.get("advanced") if isinstance(doc.get("advanced"), dict) else {}
    coord = adv.get("coordinator") if isinstance(adv.get("coordinator"), dict) else {}
    math = coord.get("mkm_myeongni_math") if isinstance(coord.get("mkm_myeongni_math"), dict) else {}

    axes: list[dict[str, Any]] = [
        _axis(
            "fusion_direction_scores",
            "numeric_deterministic",
            {
                "direction_score": scores.get("direction_score"),
                "confidence": scores.get("confidence"),
            },
            note="Cross-lens matrix input only; not graph-derived.",
        ),
    ]
    if stream:
        axes.append(
            _axis(
                "myeongri_stream_outputs",
                "deterministic_stub",
                {
                    "state_id": stream.get("state_id"),
                    "mapping_target": stream.get("mapping_target"),
                    "run_id": stream.get("run_id"),
                },
                note="16-state / calendar stub lane; no semantic graph.",
            )
        )
    if isinstance(quant, dict):
        axes.append(
            _axis(
                "myeongni_b_track_quant_block_v0",
                "numeric_matrix",
                {
                    "status": quant.get("status"),
                    "five_element_imbalance_entropy_0_1": (
                        (quant.get("five_element_imbalance_entropy_0_1"))
                        if quant.get("five_element_imbalance_entropy_0_1") is not None
                        else None
                    ),
                },
                note="Ohaeng mass vector; arithmetic only.",
            )
        )
    if math:
        axes.append(
            _axis(
                "mkm_myeongni_math_coordinator",
                "numeric_arbitration",
                {
                    "status": math.get("status"),
                    "school_disagreement_index": math.get("school_disagreement_index"),
                    "arbitrated_direction_score": math.get("arbitrated_direction_score"),
                    "arbitrated_confidence": math.get("arbitrated_confidence"),
                },
                note="School disagreement; interpret LoRA is separate layer.",
            )
        )
    return axes


def extract_sasang_axes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    stream = doc.get("sasang_stream_outputs") if isinstance(doc.get("sasang_stream_outputs"), dict) else {}
    raw_ax = doc.get("b_track_axis_scores_v1")

    axes: list[dict[str, Any]] = [
        _axis(
            "fusion_direction_scores",
            "numeric_deterministic",
            {
                "direction_score": scores.get("direction_score"),
                "confidence": scores.get("confidence"),
            },
        ),
    ]
    if stream:
        axes.append(
            _axis(
                "sasang_stream_outputs",
                "regime_proxy",
                {
                    "regime_hypothesis": stream.get("regime_hypothesis"),
                    "mapping_target": stream.get("mapping_target"),
                    "machine_readables": stream.get("machine_readables"),
                },
                note="Dynamics JSONL proxies; not medical diagnosis.",
            )
        )
    if isinstance(raw_ax, dict) and str(raw_ax.get("schema")) == "sasang_b_track_axis_scores_v1":
        axes.append(
            _axis(
                "b_track_axis_scores_v1",
                "numeric_proxy",
                {
                    "heat_proxy": raw_ax.get("heat_proxy"),
                    "cold_proxy": raw_ax.get("cold_proxy"),
                    "volatility_rarefaction_proxy": raw_ax.get("volatility_rarefaction_proxy"),
                    "thermal_imbalance_proxy": raw_ax.get("thermal_imbalance_proxy"),
                },
                note="Observation slot for cross-lens MD; no graph edges.",
            )
        )
    return axes


def lint_text_blob(text: str) -> list[str]:
    hits: list[str] = []
    low = text.lower()
    for sub in FORBIDDEN_SUBSTRINGS:
        if sub.lower() in low:
            hits.append(sub)
    for pat in FORBIDDEN_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    return sorted(set(hits))


def _collect_lintable_strings(doc: dict[str, Any], *, prefix: str = "") -> list[str]:
    """Scan only narrative fields — skip disclaimer/note keys that negate forbidden phrases."""
    skip_keys = {
        "note",
        "disclaimer_ko",
        "a_track_autobind_forbidden",
        "track_a_auto_merge_forbidden",
        "live_trading_trigger_forbidden",
        "boundary_ack",
        "provenance",
        "prohibition_ack",
    }
    out: list[str] = []
    for key, val in doc.items():
        if key in skip_keys:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(val, str) and key in {"rationale", "draft_text", "interpretation", "insight"}:
            out.append(val)
        elif isinstance(val, dict):
            out.extend(_collect_lintable_strings(val, prefix=path))
    return out


def lint_lens_doc(doc: dict[str, Any]) -> list[str]:
    parts = _collect_lintable_strings(doc)
    if not parts:
        return []
    return lint_text_blob(" ".join(parts))


def build_envelope_from_lens_paths(
    myeongni_path: Path,
    sasang_path: Path,
    *,
    interpret_path: Path | None = None,
) -> dict[str, Any]:
    my_doc = _read_json(myeongni_path)
    sa_doc = _read_json(sasang_path)
    lint_hits: list[str] = []
    lenses: dict[str, Any] = {}

    if my_doc:
        lint_hits.extend(lint_lens_doc(my_doc))
        lenses["myeongni"] = {
            "lens_id": "myeongni",
            "available": True,
            "source_schema": my_doc.get("schema"),
            "source_artifact": _rel(myeongni_path),
            "axes": extract_myeongni_axes(my_doc),
            "evidence_refs": [
                {"ref_type": "artifact", "path": _rel(myeongni_path), "role": "independent_lens"},
            ],
        }
    else:
        lenses["myeongni"] = {
            "lens_id": "myeongni",
            "available": False,
            "source_artifact": _rel(myeongni_path),
            "axes": [],
        }

    if sa_doc:
        lint_hits.extend(lint_lens_doc(sa_doc))
        lenses["sasang"] = {
            "lens_id": "sasang",
            "available": True,
            "source_schema": sa_doc.get("schema"),
            "source_artifact": _rel(sasang_path),
            "axes": extract_sasang_axes(sa_doc),
            "evidence_refs": [
                {"ref_type": "artifact", "path": _rel(sasang_path), "role": "independent_lens"},
            ],
        }
    else:
        lenses["sasang"] = {
            "lens_id": "sasang",
            "available": False,
            "source_artifact": _rel(sasang_path),
            "axes": [],
        }

    interpret_block: dict[str, Any] | None = None
    if interpret_path is not None:
        ip = _read_json(interpret_path)
        if ip:
            lint_hits.extend(lint_lens_doc(ip))
            interpret_block = {
                "available": True,
                "role": "assist_interpret_only",
                "non_gating": True,
                "source_artifact": _rel(interpret_path),
                "note": "LoRA interpret layer; not merged into graph; not fate oracle.",
            }
        else:
            interpret_block = {
                "available": False,
                "source_artifact": _rel(interpret_path),
            }

    return {
        "schema": "lens_multi_axis_audit_envelope_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_a_auto_merge_forbidden": True,
        "live_trading_trigger_forbidden": True,
        "graph_merge_forbidden": True,
        "graph_router_invoked": False,
        "audit_frame": "logos_subgraph_contract_shell_only",
        "lenses": lenses,
        "interpret_layer": interpret_block,
        "prohibition_ack": [
            "no_graph_nodes_edges_on_myeongni_sasang",
            "no_logos_subgraph_router_call",
            "no_track_a_auto_merge",
            "no_live_trading_trigger",
            "no_toe_unification_narrative",
        ],
        "lint": {
            "forbidden_substring_hits": sorted(set(lint_hits)),
            "pass": len(set(lint_hits)) == 0,
        },
    }
