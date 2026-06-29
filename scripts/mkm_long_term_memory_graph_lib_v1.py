"""MKM long-term memory graph — concept ↔ coordinate ↔ prism ↔ NL wiring ([HYPO]).

Dense doctrine graph for B-track resume/routing. Track A·live trading auto-merge forbidden.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mkm_ops_memory_index_lib_v1 import (
    dedupe_routed_by_file_path,
    extract_anchor_block,
    json_slice_text,
    missing_must_keep_tags,
    nodes_for_resume,
    read_lines,
    resolve_path,
    route_nodes_by_field_tags,
    top_nodes_by_priority,
    utc_now_iso,
    verify_must_keep_tags,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GRAPH_PATH = ROOT / "storage" / "meta" / "mkm_long_term_memory_graph_v1.json"
DEFAULT_PRISM_REGISTRY = ROOT / "docs" / "final" / "MKM12_PRISM_INDEX_REGISTRY_V1.json"

GRAPH_SCHEMA = "mkm_long_term_memory_graph_v1"


@dataclass(frozen=True)
class CoordinateSpec:
    kind: str  # markdown_anchor | json_pointer | file_excerpt
    file_path: str
    anchor_start: str | None = None
    anchor_end: str | None = None
    json_pointers: tuple[str, ...] = ()
    prism_id: str | None = None
    rebuild_cmd: str | None = None


@dataclass(frozen=True)
class ConceptSpec:
    concept_id: str
    label_ko: str
    essence: str
    must_keep_tags: tuple[str, ...]
    query_aliases: tuple[str, ...]
    field_tags: tuple[str, ...]
    priority: int
    coordinates: tuple[CoordinateSpec, ...]
    related_concepts: tuple[str, ...] = ()
    notebooklm_uuid: str | None = None
    notebooklm_pack: str | None = None
    lane_hint: str | None = None


CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="sasang_taeyang_containment",
        label_ko="태양인 희귀성 · 火剋金·金器 containment",
        essence=(
            "사상 [HYPO] — 火剋金 → 金器 containment(로켓/엔진 연소실) → 구조적 희귀성; "
            "임상·oper %·live 트리거 금지"
        ),
        must_keep_tags=("火剋金", "金器", "[HYPO]"),
        query_aliases=(
            "태양인",
            "희귀",
            "화극금",
            "火剋金",
            "금器",
            "containment",
            "taeyang",
            "로켓",
            "엔진",
            "연소실",
        ),
        field_tags=("sasang", "lens", "philosophy", "hypos", "taeyang"),
        priority=10,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/artifacts/notebooklm_lens_sasang_rag_excerpt_v1.md",
                anchor_start="## Core framing · 태양인 희귀성",
                anchor_end="## ",
                prism_id="prism_notebooklm_lens_sasang_rag_excerpt",
                rebuild_cmd="py scripts/build_notebooklm_lens_sasang_rag_excerpt_v1.py",
            ),
        ),
        related_concepts=("sasang_forbidden_synthesis", "lens_sasang_notebooklm_pack"),
        notebooklm_uuid="90132f48-febd-471a-82a1-b6ec80d98618",
        notebooklm_pack="LENS_SASANG",
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="sasang_forbidden_synthesis",
        label_ko="사상 해석 격벽 · forbidden_synthesis",
        essence=(
            "금화교역·0.58·LOCKED_MODE·oper score와 사상 철학 자동 합선 금지 — "
            "forbidden_synthesis_ko SSOT"
        ),
        must_keep_tags=("forbidden_synthesis_ko", "HYPO", "금지"),
        query_aliases=(
            "forbidden",
            "합선",
            "geumhwa",
            "금화교역",
            "0.58",
            "locked_mode",
            "코드북",
        ),
        field_tags=("sasang", "philosophy", "fact_lock", "hypos"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
                json_pointers=(
                    "/synthesis_v1/forbidden_synthesis_ko",
                    "/human_commander_gate_v1/banner_ko",
                ),
                rebuild_cmd="py scripts/build_sasang_interpretive_insight_bundle_v1.py",
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
                anchor_start="### 1.2 시스템 매핑",
                anchor_end="## 2. 만물",
            ),
        ),
        related_concepts=("sasang_taeyang_containment", "fact_lock_implementation"),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="lens_sasang_notebooklm_pack",
        label_ko="NotebookLM LENS_SASANG 팩 · NL UUID",
        essence="NL 사상 렌즈 8-source pack — excerpt+worldview+contracts; MCP≠UI auth",
        must_keep_tags=("LENS_SASANG", "HYPO"),
        query_aliases=("notebooklm", "lens_sasang", "nl", "90132f48", "사상 렌즈"),
        field_tags=("sasang", "notebooklm", "nl", "lens"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/NotebookLM_sources_manifest.md",
                anchor_start="| **사상 Sasang (B)** |",
                anchor_end="| **성경 Logos",
            ),
        ),
        notebooklm_uuid="90132f48-febd-471a-82a1-b6ec80d98618",
        notebooklm_pack="LENS_SASANG",
        related_concepts=("sasang_taeyang_containment",),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="sasang_routing_sidecar_gematria_path",
        label_ko="사상 routing sidecar · gematria path lab",
        essence=(
            "gematria_to_4d_bridge 경로에 sasang_routing_sidecar_v1 메타만 부착 — "
            "posture_hint·entropy_leg·forbidden_flags; score blend·prophecy vote 합류 금지"
        ),
        must_keep_tags=("HYPO", "sidecar", "forbidden"),
        query_aliases=(
            "sasang_routing_sidecar",
            "routing sidecar",
            "gematria path",
            "gematria_to_4d_bridge",
            "posture_hint",
            "entropy_leg",
            "must_not_merge",
            "forbidden_flags",
            "sasang_routing_sidecar_on_gematria_path",
        ),
        field_tags=("sasang", "gematria", "logos", "sidecar", "routing", "hypos"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json",
                json_pointers=(
                    "/schema",
                    "/hypothesis_class",
                    "/sasang_routing_hints",
                    "/must_not_merge_into",
                    "/forbidden_synthesis_ack",
                ),
                rebuild_cmd="py scripts/build_sasang_routing_sidecar_on_gematria_path_v1.py",
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_spec_v1_latest.md",
                anchor_start="## Forbidden edges",
                anchor_end="## KPI",
            ),
        ),
        related_concepts=("sasang_forbidden_synthesis", "lens_sasang_notebooklm_pack"),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="btrack_oper_score_freeze",
        label_ko="B-track oper score freeze · pooled 52.8%",
        essence=(
            "oper SSOT read-only — dual per-date+regime; pooled 52.8% n=360; "
            "KOSPI raw 57.2%; overwrite·Track A 승격 금지"
        ),
        must_keep_tags=("research_only", "0.527778", "send_gate"),
        query_aliases=(
            "oper",
            "score",
            "freeze",
            "52.8",
            "57.2",
            "pooled",
            "kospi",
            "recommended_eval",
        ),
        field_tags=("btrack", "prophecy", "oper", "oracle", "kospi"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/btrack_prophecy_research_freeze_v1_latest.json",
                json_pointers=(
                    "/research_only",
                    "/production_posture/send_gate",
                    "/metrics/price_hit_rates/pooled/hit_rate",
                    "/metrics/price_hit_rates/kospi/hit_rate",
                ),
            ),
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json",
                json_pointers=("/generated_at_utc", "/schema"),
            ),
        ),
        related_concepts=("send_gate_hold_doctrine", "prophecy_research_only_boundary"),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="btrack_envelope_benchmark_closed",
        label_ko="Envelope bench CLOSED · H2 governance",
        essence=(
            "envelope vs MKM bench research_only CLOSED — H2 posture; "
            "oper score 대체·headline superiority 금지"
        ),
        must_keep_tags=("CLOSED", "research_only", "HOLD"),
        query_aliases=("envelope", "ma", "smct", "tier2", "benchmark", "closure"),
        field_tags=("btrack", "envelope", "prophecy", "oracle"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/btrack_envelope_benchmark_closure_v1_latest.json",
                json_pointers=(
                    "/decision_tree_outcome/branch_id",
                    "/hypothesis_outcomes/H2_mkm_better_governance",
                    "/oper_score_ssot_read_only/kospi_directional_hit_rate_raw",
                    "/verdict_ko",
                ),
                rebuild_cmd="py scripts/build_btrack_envelope_benchmark_closure_v1.py",
            ),
        ),
        related_concepts=("btrack_oper_score_freeze",),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="send_gate_hold_doctrine",
        label_ko="SEND_GATE HOLD · Track A·live 금지",
        essence="SEND_GATE: HOLD — MS·oper·live·Track A auto-promote forbidden",
        must_keep_tags=("SEND_GATE", "HOLD", "금지"),
        query_aliases=("send_gate", "hold", "live", "track a", "승격", "실매매"),
        field_tags=("governance", "send_gate", "track_a", "ms"),
        priority=10,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="MISSION_LOG.md",
                anchor_start="## 🚀 전술 작전 보드",
                anchor_end="### 📦 핸드오프",
            ),
        ),
        related_concepts=("fact_lock_implementation", "prophecy_research_only_boundary"),
        lane_hint="ms",
    ),
    ConceptSpec(
        concept_id="fact_lock_implementation",
        label_ko="Fact-Lock · CONSTITUTION + scripts",
        essence="구현·통과 = CONSTITUTION + callable scripts + exit code; NL·채팅 단독 금지",
        must_keep_tags=("CONSTITUTION", "검증 범위", "pytest"),
        query_aliases=("fact-lock", "fact lock", "constitution", "implementation", "ssot"),
        field_tags=("fact_lock", "constitution", "governance"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                anchor_start="## 1. 검증 범위",
                anchor_end="## 2. Dual-regime",
            ),
        ),
        related_concepts=("central_resume_protocol",),
    ),
    ConceptSpec(
        concept_id="central_resume_protocol",
        label_ko="CENTRAL checkpoint · 장기기억 재개",
        essence="CENTRAL checkpoint block + athena_checkpoint — MISSION_LOG 표 금지",
        must_keep_tags=("ATHENA_CHECKPOINT",),
        query_aliases=(
            "central",
            "장기기억",
            "checkpoint",
            "이어서",
            "맥락",
            "athena_checkpoint",
        ),
        field_tags=("central", "memory", "resume", "governance"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CENTRAL_AGENT_MEMORY_V1.md",
                anchor_start="<!-- ATHENA_CHECKPOINT_V1_START -->",
                anchor_end="<!-- ATHENA_CHECKPOINT_V1_END -->",
            ),
        ),
        related_concepts=("fact_lock_implementation",),
    ),
    ConceptSpec(
        concept_id="prophecy_research_only_boundary",
        label_ko="예언 B-track · research_only 격벽",
        essence="예언·가격 B-track [HYPO] — Track A·live auto-merge·combined_all_passed 휴먼",
        must_keep_tags=("outcome_class", "combined_all_passed", "reject"),
        query_aliases=("prophecy", "예언", "b-track", "hypos", "combined_all"),
        field_tags=("prophecy", "btrack", "oracle", "research_only"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
                json_pointers=("/outcome_class", "/combined_all_passed", "/gate_taxonomy"),
            ),
        ),
        related_concepts=("btrack_oper_score_freeze", "send_gate_hold_doctrine"),
        lane_hint="oracle",
    ),
)

from mkm_long_term_memory_graph_concepts_dev_os_v1 import DEV_OS_CONCEPT_SPECS  # noqa: E402
from mkm_long_term_memory_graph_concepts_extended_v1 import EXTENDED_CONCEPT_SPECS  # noqa: E402
from mkm_long_term_memory_graph_concepts_meta_routing_v1 import (  # noqa: E402
    META_ROUTING_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_research_v1 import (  # noqa: E402
    RESEARCH_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_trading_guard_v1 import (  # noqa: E402
    TRADING_GUARD_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_a2a_bridge_v1 import (  # noqa: E402
    A2A_BRIDGE_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_infra_gpu_v1 import (  # noqa: E402
    INFRA_GPU_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_logos_oracle_v1 import (  # noqa: E402
    LOGOS_ORACLE_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_concepts_design_adapters_v1 import (  # noqa: E402
    DESIGN_ADAPTER_CONCEPT_SPECS,
)
from mkm_long_term_memory_graph_topology_v1 import (  # noqa: E402
    TOPOLOGY_BY_ID,
    topology_to_dict,
    verify_topology_blast_radius,
    verify_topology_coverage,
)

CONCEPT_SPECS = (
    *CONCEPT_SPECS,
    *EXTENDED_CONCEPT_SPECS,
    *DEV_OS_CONCEPT_SPECS,
    *META_ROUTING_CONCEPT_SPECS,
    *RESEARCH_CONCEPT_SPECS,
    *TRADING_GUARD_CONCEPT_SPECS,
    *A2A_BRIDGE_CONCEPT_SPECS,
    *INFRA_GPU_CONCEPT_SPECS,
    *LOGOS_ORACLE_CONCEPT_SPECS,
    *DESIGN_ADAPTER_CONCEPT_SPECS,
)

CONCEPT_BY_ID: dict[str, ConceptSpec] = {c.concept_id: c for c in CONCEPT_SPECS}


def load_prism_registry(path: Path = DEFAULT_PRISM_REGISTRY) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    out: dict[str, dict[str, Any]] = {}
    for entry in doc.get("entries") or []:
        eid = entry.get("id")
        if eid:
            out[str(eid)] = entry
    return out


def _coordinate_to_dict(coord: CoordinateSpec) -> dict[str, Any]:
    d: dict[str, Any] = {
        "kind": coord.kind,
        "file_path": coord.file_path,
    }
    if coord.anchor_start:
        d["anchor_start"] = coord.anchor_start
    if coord.anchor_end:
        d["anchor_end"] = coord.anchor_end
    if coord.json_pointers:
        d["json_pointers"] = list(coord.json_pointers)
    if coord.prism_id:
        d["prism_id"] = coord.prism_id
    if coord.rebuild_cmd:
        d["rebuild_cmd"] = coord.rebuild_cmd
    return d


def _concept_to_dict(spec: ConceptSpec, *, primary_coord: dict[str, Any] | None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "label_ko": spec.label_ko,
        "essence": spec.essence,
        "must_keep_tags": list(spec.must_keep_tags),
        "query_aliases": list(spec.query_aliases),
        "field_tags": list(spec.field_tags),
        "priority": spec.priority,
        "coordinates": [_coordinate_to_dict(c) for c in spec.coordinates],
        "related_concepts": list(spec.related_concepts),
    }
    if spec.notebooklm_uuid:
        d["notebooklm"] = {
            "notebook_uuid": spec.notebooklm_uuid,
            "pack_label": spec.notebooklm_pack,
        }
    if spec.lane_hint:
        d["lane_hint"] = spec.lane_hint
    if primary_coord:
        d["primary_coordinate"] = primary_coord
    return d


def extract_coordinate_block(root: Path, coord: CoordinateSpec) -> tuple[str, dict[str, Any]]:
    path = resolve_path(root, coord.file_path)
    if not path.is_file():
        raise FileNotFoundError(coord.file_path)

    meta: dict[str, Any] = {"file_path": coord.file_path, "kind": coord.kind}

    if coord.kind == "json_pointer":
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        block = json_slice_text(doc, coord.json_pointers)
        meta["json_pointers"] = list(coord.json_pointers)
        return block, meta

    if coord.kind == "markdown_anchor":
        lines = read_lines(path)
        block, line_range = extract_anchor_block(
            lines,
            anchor_start=coord.anchor_start or "",
            anchor_end=coord.anchor_end,
        )
        meta["anchor_start"] = coord.anchor_start
        meta["anchor_end"] = coord.anchor_end
        meta["line_range"] = list(line_range)
        return block, meta

    if coord.kind == "file_excerpt":
        lines = read_lines(path)
        if coord.anchor_start:
            block, line_range = extract_anchor_block(
                lines,
                anchor_start=coord.anchor_start,
                anchor_end=coord.anchor_end,
            )
            meta["line_range"] = list(line_range)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            block = text[:4000]
            meta["line_range"] = [1, min(len(lines), 200)]
        return block, meta

    raise ValueError(f"unknown coordinate kind: {coord.kind!r}")


def pick_primary_coordinate(root: Path, spec: ConceptSpec) -> tuple[CoordinateSpec, str, dict[str, Any]]:
    last_err: Exception | None = None
    for coord in spec.coordinates:
        try:
            block, meta = extract_coordinate_block(root, coord)
            if block.strip():
                return coord, block, meta
        except (FileNotFoundError, ValueError, KeyError) as exc:
            last_err = exc
            continue
    raise FileNotFoundError(
        f"no valid coordinate for {spec.concept_id}: {last_err}"
    )


def build_graph_document(root: Path) -> dict[str, Any]:
    prism = load_prism_registry(root / DEFAULT_PRISM_REGISTRY.relative_to(ROOT))
    concepts: dict[str, Any] = {}
    edges: list[dict[str, str]] = []
    missing_files: list[str] = []

    for spec in CONCEPT_SPECS:
        try:
            coord, block, meta = pick_primary_coordinate(root, spec)
            verify_must_keep_tags(block, spec.must_keep_tags)
            primary = _coordinate_to_dict(coord)
            primary.update(meta)
            if coord.prism_id and coord.prism_id in prism:
                primary["prism_path"] = prism[coord.prism_id].get("path")
                primary["prism_axis"] = prism[coord.prism_id].get("prism_axis")
        except (FileNotFoundError, ValueError) as exc:
            missing_files.append(f"{spec.concept_id}: {exc}")
            primary = None

        concept_dict = _concept_to_dict(spec, primary_coord=primary)
        topo = TOPOLOGY_BY_ID.get(spec.concept_id)
        if topo:
            concept_dict["topology"] = topology_to_dict(topo)
        concepts[spec.concept_id] = concept_dict

        for related in spec.related_concepts:
            edges.append(
                {
                    "from": spec.concept_id,
                    "to": related,
                    "relation": "related_doctrine",
                }
            )

    return {
        "schema": GRAPH_SCHEMA,
        "graph_version": "1.0",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] long-term memory graph — dense concept wiring; "
            "Track A·live trading auto-merge forbidden"
        ),
        "last_updated_utc": utc_now_iso(),
        "prism_registry_path": str(DEFAULT_PRISM_REGISTRY.relative_to(ROOT)).replace("\\", "/"),
        "concepts": concepts,
        "edges": edges,
        "concept_count": len(concepts),
        "edge_count": len(edges),
        "build_missing_coordinates": missing_files,
    }


def load_graph(path: Path = DEFAULT_GRAPH_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Graph not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify_graph_topology(graph: dict[str, Any]) -> list[str]:
    """Topology coverage + blast-radius contract ([HYPO] routing guard)."""
    concept_ids = list((graph.get("concepts") or {}).keys())
    errors = verify_topology_coverage(concept_ids)
    errors.extend(verify_topology_blast_radius(graph))
    return errors


def verify_graph_sources(root: Path, graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for concept_id, concept in (graph.get("concepts") or {}).items():
        spec = CONCEPT_BY_ID.get(concept_id)
        if not spec:
            errors.append(f"{concept_id}: unknown concept in graph")
            continue
        tags = concept.get("must_keep_tags") or spec.must_keep_tags
        try:
            _coord, block, _meta = pick_primary_coordinate(root, spec)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            errors.append(f"{concept_id}: coordinate extract failed: {exc}")
            continue
        missing = missing_must_keep_tags(block, tags)
        if missing:
            errors.append(f"{concept_id}: must_keep_tags missing in source: {missing}")
    return errors


def score_concept_query(concept: dict[str, Any], query: str) -> int:
    q = query.lower().strip()
    if not q:
        return 0
    score = 0
    essence = (concept.get("essence") or "").lower()
    label = (concept.get("label_ko") or "").lower()
    for alias in concept.get("query_aliases") or []:
        al = str(alias).lower()
        if len(al) >= 2 and al in q:
            score += 3 + min(len(al) // 6, 2)
    for tag in concept.get("field_tags") or []:
        t = str(tag).lower()
        if len(t) >= 3 and t in q:
            score += 2
    tokens = [t for t in re.split(r"[^a-zA-Z0-9_가-힣$]+", q) if len(t) >= 2]
    score += sum(1 for t in tokens if t in essence or t in label)
    return score


def route_concepts_by_query(
    graph: dict[str, Any],
    query: str,
    *,
    min_score: int = 2,
    max_concepts: int = 8,
    include_related: bool = True,
) -> list[tuple[str, dict[str, Any]]]:
    concepts = graph.get("concepts") or {}
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for concept_id, concept in concepts.items():
        s = score_concept_query(concept, query)
        if s >= min_score:
            scored.append((s, concept_id, concept))
    scored.sort(
        key=lambda item: (-item[0], -int(item[2].get("priority", 0)), item[1])
    )
    ranked = [(cid, c) for _s, cid, c in scored[:max_concepts]]

    if include_related and ranked:
        seen = {cid for cid, _ in ranked}
        edge_map: dict[str, set[str]] = {}
        for edge in graph.get("edges") or []:
            fr = edge.get("from")
            to = edge.get("to")
            if fr and to:
                edge_map.setdefault(str(fr), set()).add(str(to))
        extras: list[tuple[str, dict[str, Any]]] = []
        for cid, _ in list(ranked):
            for rel in edge_map.get(cid, ()):
                if rel in seen or rel not in concepts:
                    continue
                seen.add(rel)
                extras.append((rel, concepts[rel]))
        ranked.extend(extras[: max(0, max_concepts - len(ranked))])
    return ranked


def resolve_lane_from_graph(graph: dict[str, Any], query: str) -> str | None:
    routed = route_concepts_by_query(
        graph, query, min_score=3, max_concepts=5, include_related=False
    )
    if not routed:
        return None
    top_cid, top_concept = routed[0]
    top_hint = top_concept.get("lane_hint")
    if top_hint:
        return str(top_hint)
    scores: dict[str, int] = {}
    for _cid, concept in routed[:3]:
        hint = concept.get("lane_hint")
        if hint:
            scores[str(hint)] = scores.get(str(hint), 0) + int(concept.get("priority", 0))
    if not scores:
        return None
    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def concept_to_ops_node_entry(
    root: Path,
    spec: ConceptSpec,
    *,
    coord: CoordinateSpec | None = None,
) -> dict[str, Any]:
    use_coord = coord
    block = ""
    if use_coord is None:
        use_coord, block, _meta = pick_primary_coordinate(root, spec)
    else:
        block, _meta = extract_coordinate_block(root, use_coord)

    verify_must_keep_tags(block, spec.must_keep_tags)
    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]

    node: dict[str, Any] = {
        "essence": spec.essence,
        "must_keep_tags": list(spec.must_keep_tags),
        "priority": spec.priority,
        "field_tags": list(spec.field_tags) + [f"ltm_{spec.concept_id}"],
        "char_count": len(block),
        "content_sha256_prefix": digest,
        "ltm_concept_id": spec.concept_id,
        "label_ko": spec.label_ko,
    }

    if use_coord.kind == "json_pointer":
        node["slice_kind"] = "json_pointer"
        node["file_path"] = use_coord.file_path
        node["json_pointers"] = list(use_coord.json_pointers)
    elif use_coord.kind in ("markdown_anchor", "file_excerpt"):
        node["file_path"] = use_coord.file_path
        node["anchor_start"] = use_coord.anchor_start
        node["anchor_end"] = use_coord.anchor_end
    else:
        node["slice_kind"] = "registry_chunk"
        node["file_path"] = use_coord.file_path

    if use_coord.rebuild_cmd:
        node["rebuild_cmd"] = use_coord.rebuild_cmd
    if spec.notebooklm_uuid:
        node["notebooklm_uuid"] = spec.notebooklm_uuid
    return node


def build_doctrine_overlay_nodes(
    root: Path,
    graph: dict[str, Any] | None = None,
    *,
    query: str = "",
    max_nodes: int = 12,
) -> dict[str, dict[str, Any]]:
    """Build ops-index overlay nodes from LTM graph concepts."""
    nodes: dict[str, dict[str, Any]] = {}
    if query.strip() and graph:
        routed = route_concepts_by_query(graph, query, min_score=2, max_concepts=max_nodes)
        specs = [CONCEPT_BY_ID[cid] for cid, _ in routed if cid in CONCEPT_BY_ID]
    else:
        specs = list(CONCEPT_SPECS)

    for spec in specs[:max_nodes]:
        node_id = f"ltm_{spec.concept_id}"
        try:
            nodes[node_id] = concept_to_ops_node_entry(root, spec)
        except (FileNotFoundError, ValueError):
            continue
    return nodes


def nodes_for_topic_resume(
    index: dict[str, Any],
    graph: dict[str, Any],
    topic: str,
    *,
    lane: str | None = None,
    top_n: int = 3,
    max_ltm: int = 5,
    max_field_tag: int = 4,
    root: Path | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Merge lane pack (or top-N) + LTM concepts + field-tag overlay nodes."""
    nodes = index.get("nodes") or {}
    if lane:
        ranked = list(nodes_for_resume(index, lane=lane, root=root))
    else:
        ranked = top_nodes_by_priority(index, top_n=top_n)

    if topic.strip():
        for concept_id, _concept in route_concepts_by_query(
            graph, topic, max_concepts=max_ltm
        ):
            node_id = f"ltm_{concept_id}"
            if node_id in nodes:
                ranked.append((node_id, nodes[node_id]))
        for node_id, node in route_nodes_by_field_tags(
            index, topic, max_nodes=max_field_tag
        ):
            if node_id not in {nid for nid, _ in ranked}:
                ranked.append((node_id, node))

    return dedupe_routed_by_file_path(ranked)


def merge_graph_routing_summary(
    graph: dict[str, Any],
    query: str,
    *,
    resolved_lane: str | None = None,
) -> dict[str, Any]:
    routed = route_concepts_by_query(graph, query)
    lane = resolved_lane or resolve_lane_from_graph(graph, query)
    return {
        "schema": "mkm_long_term_memory_route_v1",
        "research_only": True,
        "topic": query,
        "resolved_lane": lane,
        "concept_ids": [cid for cid, _ in routed],
        "concept_labels": [c.get("label_ko") for _cid, c in routed],
        "overlay_node_ids": [f"ltm_{cid}" for cid, _ in routed],
    }
