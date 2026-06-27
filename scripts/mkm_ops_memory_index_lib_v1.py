"""MKM ops memory index — anchor extraction and must_keep gate ([HYPO] / research_only).

Deterministic paragraph/block indexing for MISSION_LOG + CENTRAL checkpoints.
Track A·live trading auto-merge forbidden — B-track research lane only.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INDEX_PATH = ROOT / "storage" / "meta" / "mkm_ops_memory_index_v1.json"

H2_RE = re.compile(r"^##\s+")


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    file_path: str
    anchor_start: str
    anchor_end: str | None
    essence: str
    must_keep_tags: tuple[str, ...]
    priority: int = 5


NODE_SPECS: tuple[NodeSpec, ...] = (
    NodeSpec(
        node_id="prism_ops_mission_log_board",
        file_path="MISSION_LOG.md",
        anchor_start="## 🚀 전술 작전 보드",
        anchor_end="<!-- MISSION_LOG_BOARD_END -->",
        essence="작전 보드 SSOT — active lanes only · Track A 금지 · SEND_GATE HOLD",
        must_keep_tags=("FAIL-COMP-004", "Track A", "SEND_GATE: HOLD"),
        priority=10,
    ),
    NodeSpec(
        node_id="prism_ops_central_checkpoint",
        file_path="docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        anchor_start="<!-- ATHENA_CHECKPOINT_V1_START -->",
        anchor_end="<!-- ATHENA_CHECKPOINT_V1_END -->",
        essence="CENTRAL 최신 운영 체크포인트 블록 — athena_checkpoint·격벽 스냅샷",
        must_keep_tags=("ATHENA_CHECKPOINT", "CENTRAL"),
        priority=9,
    ),
    NodeSpec(
        node_id="prism_ops_mission_log_next_one",
        file_path="MISSION_LOG.md",
        anchor_start="**다음 1타 (레인 · 재개용 핀):**",
        anchor_end="## 🚀 전술 작전 보드",
        essence="레인별 다음 1타 SSOT — 재개 핀 · HOLD · Track A·실매매 금지",
        must_keep_tags=("Track A", "HOLD", "금지"),
        priority=8,
    ),
    NodeSpec(
        node_id="prism_ops_lane_oracle",
        file_path="MISSION_LOG.md",
        anchor_start="### 🔮 Oracle",
        anchor_end="### 🖥️ Infra",
        essence="Oracle 레인 — Logos·align-panel · narrative_lane_open · Track A·live 금지",
        must_keep_tags=("Track A", "금지", "B-track"),
        priority=7,
    ),
    NodeSpec(
        node_id="prism_ops_lane_infra",
        file_path="MISSION_LOG.md",
        anchor_start="### 🖥️ Infra",
        anchor_end="<!-- MISSION_LOG_BOARD_END -->",
        essence="Infra 레인 — solo stack·scheduler band · Track A·live 금지",
        must_keep_tags=("Track A", "금지", "solo"),
        priority=7,
    ),
    NodeSpec(
        node_id="prism_ops_lane_ms",
        file_path="MISSION_LOG.md",
        anchor_start="### 💼 MS",
        anchor_end="### 🧭 Cursor IDE",
        essence="MS 레인 — 지원사업 CLOSED·B2B HOLD · 에이전트 제출 금지",
        must_keep_tags=("MS", "SEND_GATE", "금지"),
        priority=7,
    ),
    NodeSpec(
        node_id="prism_ops_lane_design",
        file_path="MISSION_LOG.md",
        anchor_start="**Design/Showroom (아카이브",
        anchor_end="## 🚀 전술 작전 보드",
        essence="Design/Showroom 레인 — 아카이브·패시브 · SEND_GATE HOLD",
        must_keep_tags=("Track A", "금지", "SEND_GATE: HOLD"),
        priority=7,
    ),
)

LANE_OPS_PACKS: dict[str, tuple[str, ...]] = {
    "oracle": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_oracle",
        "prism_ops_theory_mathematization_gate",
        "prism_ops_theory_formula_ssot",
        "prism_ops_logos_cosmic_anchor_bridge",
        "prism_ops_logos_narrative_router_eval",
        "prism_ops_logos_router_regression_bundle",
        "prism_ops_logos_four_force_report",
        "prism_ops_logos_gematria_dual_gate",
        "prism_ops_logos_oracle_module_tier2_prep",
        "prism_ops_logos_narrative_closure_observability",
    ),
    "ms": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_ms",
    ),
    "infra": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_infra",
    ),
    "design": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_design",
        "prism_ops_pixel_battalion_gate",
        "prism_ops_lens_audio_gate",
        "prism_ops_clinic_landing_gate",
    ),
    "web_ops": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_web_ops_regime_gate",
        "prism_ops_web_ops_health",
    ),
}

# Default Cursor resume when commander says 「장기기억 맥락이어」 (no --lane).
COMMANDER_DEFAULT_RESUME_NODES: tuple[str, ...] = (
    "prism_ops_mission_log_board",
    "prism_ops_central_checkpoint",
    "prism_ops_mission_log_next_one",
)
COMMANDER_SLICE_NODE_IDS: frozenset[str] = frozenset(
    {
        "prism_ops_central_checkpoint",
        "prism_ops_mission_log_next_one",
    }
)


@dataclass(frozen=True)
class JsonSliceSpec:
    node_id: str
    file_path: str
    json_pointers: tuple[str, ...]
    essence: str
    must_keep_tags: tuple[str, ...]
    priority: int = 6
    field_tags: tuple[str, ...] = ()


WEB_OPS_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="prism_ops_web_ops_regime_gate",
        file_path="reports/web_ops_regime_gate_v1_latest.json",
        json_pointers=(
            "/gate_pass",
            "/research_only",
            "/track_wall",
            "/conflict_resolver/worst_final_action",
            "/cost_policy/no_gpu_spinup",
            "/cost_policy/no_new_billing_charges",
            "/cost_policy/nebius_prepaid_only",
            "/operator_hint_ko",
        ),
        essence="web_ops 레짐 게이트 — ALLOW_READ·HOLD_PAYMENT·Nebius/Azure 비용·Tier3 Human · research_only",
        must_keep_tags=("no_gpu_spinup", "research_only", "gate_pass"),
        priority=6,
        field_tags=("infra", "web_ops", "nebius", "cost_audit", "regime_action"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_web_ops_health",
        file_path="reports/web_ops_regime_health_summary_v1_latest.json",
        json_pointers=(
            "/health_ok",
            "/gate_pass",
            "/research_only",
            "/nebius_balance_usd",
            "/pointer_drift_detected",
            "/observation_source",
            "/worst_final_action",
        ),
        essence="web_ops 헬스 요약 — worst_final_action·balance·drift·observation_source · B-track",
        must_keep_tags=("research_only", "health_ok"),
        priority=5,
        field_tags=("infra", "web_ops", "health", "regime_action"),
    ),
)

DOMAIN_ADAPTER_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="prism_ops_pixel_battalion_gate",
        file_path="reports/mkmlife_pixel_sprite_urls_gate_v1_latest.json",
        json_pointers=(
            "/overall_ok",
            "/ok_count",
            "/fail_count",
            "/track_wall",
            "/hypothesis_tag",
            "/lane",
        ),
        essence="Pixel Battalion gate — sprite URL hard gate · B-track UI · not Track A",
        must_keep_tags=("[HYPO]", "overall_ok", "track_wall"),
        priority=6,
        field_tags=("design", "pixel", "showroom", "mkmlife", "btrack"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_lens_audio_gate",
        file_path="reports/audio_gate_latest.json",
        json_pointers=(
            "/decision",
            "/track",
            "/metrics/lens_alignment_pass",
            "/provenance/commercial_terms_tag",
        ),
        essence="Lens Audio gate — lens_safe_tempo_clamp BGM PoC · research_only B-track",
        must_keep_tags=("lens_alignment_pass", "decision", "track"),
        priority=6,
        field_tags=("design", "audio", "bgm", "music", "lens", "btrack"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_clinic_landing_gate",
        file_path="reports/clinic_km_mmp_landing_gate_v1_latest.json",
        json_pointers=(
            "/ok",
            "/decision",
            "/lane_status",
            "/send_gate",
            "/ready_for_external_send",
        ),
        essence="Clinic LOI landing gate — DTCG v2 · forbidden copy · contrast · HOLD wedge",
        must_keep_tags=("ok", "decision", "send_gate"),
        priority=6,
        field_tags=("design", "clinic", "landing", "trust_composition", "btrack"),
    ),
)

FILLS_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="prism_ops_fills_multi_res_summary",
        file_path="reports/multi_res_fills_index_v1_latest.json",
        json_pointers=(
            "/meta/n_fill_rows",
            "/meta/n_daily_buckets",
            "/meta/trades_source",
            "/research_only",
            "/low_res/daily_by_utc_date",
        ),
        essence="fills multi-res low-res inject — daily buckets + row count · B-track",
        must_keep_tags=("research_only", "n_fill_rows"),
        priority=4,
        field_tags=("btrack", "fills", "multi_res", "execution"),
    ),
)

THEORY_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="prism_ops_theory_mathematization_gate",
        file_path="docs/final/artifacts/mkm_theory_formula_promotion_gate_dryrun_v1_latest.json",
        json_pointers=(
            "/promotion_to_a_track_allowed",
            "/track_b_only",
            "/ok",
            "/checks/5/entries",
            "/checks/5/promotion_to_a_track_allowed",
        ),
        essence="이론 75식 승격 게이트 dryrun — B-track only · promotion_to_a_track_allowed=false",
        must_keep_tags=("promotion_to_a_track_allowed", "track_b_only"),
        priority=5,
        field_tags=("theory", "btrack", "formula", "promotion_gate"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_theory_formula_ssot",
        file_path="docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json",
        json_pointers=(
            "/unrecovered_slots",
            "/documented_with_expr",
            "/repo_implemented_facts",
        ),
        essence="75식 SSOT 스냅샷 — catalog expr vs 4 repo FACT · HYPO index",
        must_keep_tags=("unrecovered_slots", "documented_with_expr"),
        priority=5,
        field_tags=("theory", "formula", "hypo"),
    ),
)

LOGOS_MATH_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="prism_ops_logos_cosmic_anchor_bridge",
        file_path="docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json",
        json_pointers=(
            "/kernel_recipe_id",
            "/summary/lemma_hit_anchors",
            "/summary/narrative_sample_count",
            "/summary/resonance_edge_count",
            "/research_only",
            "/track_a_blocked",
        ),
        essence="Logos cosmic anchor bridge — 339 anchors · 200 narratives · gematria_bridge_v1 · B-track",
        must_keep_tags=("gematria_bridge_v1", "research_only", "narrative_sample_count"),
        priority=7,
        field_tags=("logos", "anchor", "graph", "gematria", "btrack"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_four_force_report",
        file_path="docs/final/artifacts/logos_fundamental_force_primitive_report_v1_latest.json",
        json_pointers=(
            "/kernel_recipe_id",
            "/pedagogical_isomorphism_only",
            "/summary/force_top1_counts",
            "/summary/harmony_top1_share",
            "/disclaimer_ko",
        ),
        essence="4힘 교육용 동형 리포트 [HYPO] — gematria_bridge_v1 커널 · Track A 금지",
        must_keep_tags=("gematria_bridge_v1", "pedagogical_isomorphism_only", "[HYPO]"),
        priority=6,
        field_tags=("logos", "four_force", "hypo", "gematria"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_4d_state",
        file_path="docs/final/artifacts/logos_4d_state_v1_latest.json",
        json_pointers=(
            "/quadrant_info/regime_tag",
            "/narrative_oracle/policy_tag",
            "/narrative_oracle/action",
            "/coordinates",
        ),
        essence="Logos 4D daily state — WATCH quadrant · [NON_GATING] narrative assist",
        must_keep_tags=("[NON_GATING]", "regime_tag"),
        priority=6,
        field_tags=("logos", "4d", "regime", "non_gating"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_narrative_router_eval",
        file_path="docs/final/artifacts/logos_narrative_path_eval_v1_latest.json",
        json_pointers=(
            "/summary/router_hit_rate",
            "/summary/sample_pass_rate",
            "/narrative_sample_count",
            "/research_only",
            "/send_gate",
        ),
        essence="Narrative router eval 200/200 — structural overlap · NOT alignment_pass_rate",
        must_keep_tags=("router_hit_rate", "research_only", "send_gate"),
        priority=7,
        field_tags=("logos", "router", "graphrag", "btrack"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_router_regression_bundle",
        file_path="reports/logos_router_regression_bundle_v1_latest.json",
        json_pointers=(
            "/chain_pass",
            "/send_gate",
            "/bloom_cap",
            "/narrative_eval/router_hit_rate",
            "/gold_eval/gold_required_all_pass",
        ),
        essence="P21 router regression bundle — bloom guard + gold 12/12 · HOLD",
        must_keep_tags=("chain_pass", "send_gate", "gold_required_all_pass"),
        priority=8,
        field_tags=("logos", "router", "gold", "regression"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_gold_eval",
        file_path="reports/logos_gold_query_eval_v1_latest.json",
        json_pointers=(
            "/summary/gold_required_all_pass",
            "/summary/gold_required_count",
            "/research_only",
            "/non_gating",
        ),
        essence="Gold query eval 12 required — router/ANN Hit@k · non-gating",
        must_keep_tags=("gold_required_all_pass", "research_only", "non_gating"),
        priority=6,
        field_tags=("logos", "gold", "retrieval", "btrack"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_gematria_dual_gate",
        file_path="docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json",
        json_pointers=(
            "/gates/gate_b_geometry_production/recipe_id",
            "/gates/gate_b_geometry_production/pass",
            "/gates/gate_b_prime_geometry_sandbox/recipe_id",
            "/research_only",
        ),
        essence="Gematria 4D dual gate — production vs sandbox spread · research_only",
        must_keep_tags=("gematria_bridge_v1", "research_only"),
        priority=6,
        field_tags=("logos", "gematria", "4d", "gate"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_oracle_module_tier2_prep",
        file_path="docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json",
        json_pointers=(
            "/tier1_module_ssot_ready",
            "/tier2_prep_ready",
            "/tier2_pin_schema_snapshot/resonance_cap",
            "/tier2_pin_schema_snapshot/hd_mission_version",
            "/hypothesis_class",
            "/send_gate",
            "/repro_one_shot",
        ),
        essence="Oracle module Tier-2 prep — Cursor inject SSOT · cap cross-SSOT read-only · HOLD",
        must_keep_tags=("tier1_module_ssot_ready", "send_gate", "HYPO"),
        priority=9,
        field_tags=("logos", "oracle", "cursor", "module", "tier2"),
    ),
    JsonSliceSpec(
        node_id="prism_ops_logos_narrative_closure_observability",
        file_path="docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json",
        json_pointers=(
            "/observation_pass",
            "/observations_pass_count",
            "/snapshot/resonance_cap",
            "/snapshot/narrative_samples",
            "/snapshot/read_only",
            "/send_gate",
            "/repro_one_shot",
        ),
        essence="Narrative+closure observability aggregate — read-only · NOT cap bump",
        must_keep_tags=("observation_pass", "send_gate", "read_only"),
        priority=8,
        field_tags=("logos", "oracle", "observability", "closure"),
    ),
)

LTM_A2A_NODE_CONCEPT_IDS: dict[str, str] = {
    "ltm_ops_inject_to_a2a_wire": "ltm_ops_inject_to_a2a_wire",
    "ltm_a2a_two_layer_architecture_ssot": "a2a_two_layer_architecture_ssot",
    "ltm_inter_agent_encoding_smoke_chain": "inter_agent_encoding_smoke_chain",
    "ltm_a2a_ltm_track_wall": "a2a_ltm_track_wall",
}

LTM_A2A_JSON_SPECS: tuple[JsonSliceSpec, ...] = (
    JsonSliceSpec(
        node_id="ltm_ops_inject_to_a2a_wire",
        file_path="docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json",
        json_pointers=(
            "/compress_result/decision",
            "/compress_result/compression_metrics/savings_ratio",
            "/boundary_ack",
        ),
        essence="LTM tp01 resume → A2A v2 compress pilot — wire handoff only",
        must_keep_tags=("[HYPO]", "boundary_ack"),
        priority=8,
        field_tags=("a2a", "ltm", "ops_memory", "tp01"),
    ),
    JsonSliceSpec(
        node_id="ltm_a2a_two_layer_architecture_ssot",
        file_path="docs/final/artifacts/mkm_a2a_two_layer_architecture_v1_latest.json",
        json_pointers=("/schema", "/research_only", "/layers"),
        essence="A2A 2-layer architecture — ops memory vs inter-agent wire",
        must_keep_tags=("research_only", "layers"),
        priority=8,
        field_tags=("a2a", "meta_routing", "research"),
    ),
    JsonSliceSpec(
        node_id="ltm_inter_agent_encoding_smoke_chain",
        file_path="docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
        json_pointers=(
            "/rq_019",
            "/rq_019_milestones_wire_layer_ready",
            "/boundary_ack",
        ),
        essence="Inter-Agent encoding smoke status — RQ-019 milestones",
        must_keep_tags=("boundary_ack",),
        priority=7,
        field_tags=("a2a", "compression", "fuel"),
    ),
    JsonSliceSpec(
        node_id="ltm_a2a_ltm_track_wall",
        file_path="docs/final/artifacts/ltm_a2a_bridge_wall_v1.json",
        json_pointers=("/forbidden_auto_merge", "/allowed_uses", "/boundary_ack"),
        essence="A2A·LTM track wall — no Track A·live·MS headline merge",
        must_keep_tags=("forbidden_auto_merge", "live_trading_enable"),
        priority=9,
        field_tags=("a2a", "governance", "fact_lock"),
    ),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_path(root: Path, rel: str) -> Path:
    return (root / rel).resolve()


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return text.splitlines()


def extract_anchor_block(
    lines: list[str],
    *,
    anchor_start: str,
    anchor_end: str | None = None,
) -> tuple[str, tuple[int, int]]:
    """Return (block_text, (start_line_1based, end_line_1based inclusive))."""
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if anchor_start in line:
            start_idx = i
            break
    if start_idx is None:
        raise ValueError(f"anchor_start not found: {anchor_start!r}")

    end_idx = len(lines) - 1
    if anchor_end:
        for j in range(start_idx + 1, len(lines)):
            if anchor_end in lines[j]:
                end_idx = j - 1
                break
        if end_idx < start_idx:
            raise ValueError(
                f"anchor_end {anchor_end!r} before start for {anchor_start!r}"
            )

    block_lines = lines[start_idx : end_idx + 1]
    block = "\n".join(block_lines)
    return block, (start_idx + 1, end_idx + 1)


def missing_must_keep_tags(text: str, tags: tuple[str, ...] | list[str]) -> list[str]:
    missing: list[str] = []
    for tag in tags:
        if tag not in text:
            missing.append(tag)
    return missing


def verify_must_keep_tags(text: str, tags: tuple[str, ...] | list[str]) -> None:
    missing = missing_must_keep_tags(text, tags)
    if missing:
        raise ValueError(f"must_keep_tags missing: {missing}")


def build_node_entry(
    root: Path,
    spec: NodeSpec,
) -> dict[str, Any]:
    path = resolve_path(root, spec.file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {spec.file_path}")

    lines = read_lines(path)
    block, line_range = extract_anchor_block(
        lines,
        anchor_start=spec.anchor_start,
        anchor_end=spec.anchor_end,
    )
    verify_must_keep_tags(block, spec.must_keep_tags)

    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]
    return {
        "file_path": spec.file_path,
        "anchor_start": spec.anchor_start,
        "anchor_end": spec.anchor_end,
        "line_range": list(line_range),
        "essence": spec.essence,
        "must_keep_tags": list(spec.must_keep_tags),
        "priority": spec.priority,
        "char_count": len(block),
        "content_sha256_prefix": digest,
    }


def build_index_document(root: Path) -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    for spec in NODE_SPECS:
        nodes[spec.node_id] = build_node_entry(root, spec)

    return {
        "schema": "mkm_ops_memory_index_v1",
        "index_version": "1.0",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] ops memory index — Track A·live trading auto-merge forbidden"
        ),
        "last_updated_utc": utc_now_iso(),
        "nodes": nodes,
    }


def load_index(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Index not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _decode_json_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_json_pointer(doc: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"json_pointer must start with /: {pointer!r}")
    if pointer == "/":
        return doc
    cur: Any = doc
    for raw in pointer.strip("/").split("/"):
        key = _decode_json_pointer_token(raw)
        if isinstance(cur, list):
            cur = cur[int(key)]
        elif isinstance(cur, dict):
            cur = cur[key]
        else:
            raise KeyError(f"cannot traverse {pointer!r} at segment {key!r}")
    return cur


def json_slice_text(doc: dict[str, Any], pointers: list[str] | tuple[str, ...]) -> str:
    lines: list[str] = []
    for pointer in pointers:
        value = resolve_json_pointer(doc, pointer)
        lines.append(f"{pointer}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines)


def build_json_slice_node_entry(root: Path, spec: JsonSliceSpec) -> dict[str, Any]:
    path = resolve_path(root, spec.file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {spec.file_path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    block = json_slice_text(doc, spec.json_pointers)
    verify_must_keep_tags(block, spec.must_keep_tags)
    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]
    return {
        "slice_kind": "json_pointer",
        "file_path": spec.file_path,
        "json_pointers": list(spec.json_pointers),
        "essence": spec.essence,
        "must_keep_tags": list(spec.must_keep_tags),
        "priority": spec.priority,
        "field_tags": list(spec.field_tags),
        "char_count": len(block),
        "content_sha256_prefix": digest,
    }


def extract_json_slice_from_node(
    root: Path,
    node: dict[str, Any],
    *,
    pointers: list[str] | tuple[str, ...] | None = None,
) -> str:
    path = resolve_path(root, node["file_path"])
    if not path.is_file():
        raise FileNotFoundError(f"Missing indexed file: {node['file_path']}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    use_pointers = list(pointers if pointers is not None else (node.get("json_pointers") or []))
    return json_slice_text(doc, use_pointers)


# Query → JSON pointer coordinates ([HYPO] DSS chunk-cap pattern; not embedding RAG).
POINTER_QUERY_HINTS: dict[str, tuple[str, ...]] = {
    "balance": ("/nebius_balance_usd", "/gate_pass"),
    "잔액": ("/nebius_balance_usd",),
    "prepaid": ("/cost_policy/nebius_prepaid_only", "/nebius_balance_usd"),
    "선불": ("/cost_policy/nebius_prepaid_only",),
    "$25": ("/nebius_balance_usd",),
    "no_gpu": ("/cost_policy/no_gpu_spinup",),
    "spinup": ("/cost_policy/no_gpu_spinup",),
    "gpu": ("/cost_policy/no_gpu_spinup",),
    "gate_pass": ("/gate_pass",),
    "gate": ("/gate_pass", "/conflict_resolver/worst_final_action", "/worst_final_action"),
    "drift": ("/pointer_drift_detected",),
    "baseline": ("/pointer_drift_detected",),
    "health": ("/health_ok",),
    "health_ok": ("/health_ok",),
    "observation": ("/observation_source",),
    "cdp": ("/observation_source",),
    "live": ("/observation_source",),
    "tier3": ("/operator_hint_ko",),
    "auth": ("/operator_hint_ko",),
    "allow_read": ("/conflict_resolver/worst_final_action", "/worst_final_action"),
    "allow_prefill": ("/conflict_resolver/worst_final_action",),
    "hold_payment": ("/operator_hint_ko", "/cost_policy/no_new_billing_charges"),
    "read_only": ("/conflict_resolver/worst_final_action", "/worst_final_action"),
    "dashboard": ("/worst_final_action", "/conflict_resolver/worst_final_action"),
    "worst_final_action": ("/conflict_resolver/worst_final_action", "/worst_final_action"),
    "final_action": ("/conflict_resolver/worst_final_action", "/worst_final_action"),
    "payment_risk": ("/operator_hint_ko", "/cost_policy/no_new_billing_charges"),
    "allow": ("/worst_final_action", "/conflict_resolver/worst_final_action"),
    "hold": ("/worst_final_action", "/conflict_resolver/worst_final_action"),
    "payment": ("/cost_policy/no_new_billing_charges", "/operator_hint_ko"),
    "cost": ("/cost_policy/no_gpu_spinup", "/cost_policy/nebius_prepaid_only"),
    "비용": ("/cost_policy/no_gpu_spinup", "/nebius_balance_usd"),
    "감사": ("/cost_policy/no_gpu_spinup", "/gate_pass"),
}

JSON_POINTER_ANCHORS: tuple[str, ...] = ("/research_only", "/gate_pass", "/health_ok")


def filter_json_pointers_for_query(
    pointers: list[str] | tuple[str, ...],
    query: str,
    *,
    min_selected: int = 2,
) -> list[str]:
    """Pick coordinate subset for query; fallback to full pointer list if too sparse."""
    q = query.lower()
    selected: list[str] = []
    seen: set[str] = set()
    for hint, hint_ptrs in POINTER_QUERY_HINTS.items():
        if hint.lower() in q:
            for ptr in hint_ptrs:
                if ptr in pointers and ptr not in seen:
                    seen.add(ptr)
                    selected.append(ptr)
    for anchor in JSON_POINTER_ANCHORS:
        if anchor in pointers and anchor not in seen:
            seen.add(anchor)
            selected.append(anchor)
    if len(selected) < min_selected:
        return list(pointers)
    return selected


def extract_node_slice_for_query(
    root: Path,
    node: dict[str, Any],
    query: str,
    *,
    max_chars: int,
    use_coordinate_filter: bool = True,
) -> tuple[str, bool, list[str]]:
    """JSON pointer coordinate slice + anchor truncation ([HYPO])."""
    if node.get("slice_kind") == "json_pointer" and use_coordinate_filter:
        pointers = node.get("json_pointers") or []
        filtered = filter_json_pointers_for_query(pointers, query)
        block = extract_json_slice_from_node(root, node, pointers=filtered)
        preview, truncated = truncate_anchor_slice(block, max_chars=max_chars)
        return preview, truncated, filtered
    block = extract_node_from_index(root, node)
    preview, truncated = truncate_anchor_slice(block, max_chars=max_chars)
    return preview, truncated, list(node.get("json_pointers") or [])


def extract_node_from_index(root: Path, node: dict[str, Any]) -> str:
    if node.get("slice_kind") == "json_pointer":
        return extract_json_slice_from_node(root, node)
    if node.get("slice_kind") == "registry_chunk":
        path = resolve_path(root, node["file_path"])
        if not path.is_file():
            raise FileNotFoundError(f"Missing indexed file: {node['file_path']}")
        return path.read_text(encoding="utf-8", errors="replace")
    path = resolve_path(root, node["file_path"])
    if not path.is_file():
        raise FileNotFoundError(f"Missing indexed file: {node['file_path']}")
    lines = read_lines(path)
    block, _ = extract_anchor_block(
        lines,
        anchor_start=node["anchor_start"],
        anchor_end=node.get("anchor_end"),
    )
    return block


def verify_index_sources(root: Path, index: dict[str, Any]) -> list[str]:
    """Return list of error messages; empty if all nodes pass."""
    errors: list[str] = []
    nodes = index.get("nodes") or {}
    for node_id, node in nodes.items():
        tags = node.get("must_keep_tags") or []
        try:
            block = extract_node_from_index(root, node)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            errors.append(f"{node_id}: extract failed: {exc}")
            continue
        missing = missing_must_keep_tags(block, tags)
        if missing:
            errors.append(f"{node_id}: must_keep_tags missing in source: {missing}")
    return errors


def top_nodes_by_priority(
    index: dict[str, Any],
    *,
    top_n: int = 2,
) -> list[tuple[str, dict[str, Any]]]:
    nodes = index.get("nodes") or {}
    ranked = sorted(
        nodes.items(),
        key=lambda item: (-int(item[1].get("priority", 0)), item[0]),
    )
    return ranked[:top_n]


def nodes_for_resume(
    index: dict[str, Any],
    *,
    top_n: int = 3,
    lane: str | None = None,
    root: Path | None = None,
    commander_default: bool = False,
) -> list[tuple[str, dict[str, Any]]]:
    """Default: commander pack (board+CENTRAL+next-one table) or top-N by priority.

    Lane pack: board + CENTRAL + one lane row (no full next-one table).
    """
    if lane and root is not None:
        index = ensure_lane_pack_index(root, index, lane)
    nodes = index.get("nodes") or {}
    if lane:
        lane_key = lane.strip().lower()
        if lane_key not in LANE_OPS_PACKS:
            raise ValueError(
                f"unknown lane {lane!r}; expected one of {sorted(LANE_OPS_PACKS)}"
            )
        selected: list[tuple[str, dict[str, Any]]] = []
        for node_id in LANE_OPS_PACKS[lane_key]:
            if node_id not in nodes:
                raise KeyError(f"lane pack missing node: {node_id}")
            selected.append((node_id, nodes[node_id]))
        return selected
    if commander_default:
        selected = []
        for node_id in COMMANDER_DEFAULT_RESUME_NODES:
            if node_id not in nodes:
                raise KeyError(f"commander resume missing node: {node_id}")
            selected.append((node_id, nodes[node_id]))
        return selected
    return top_nodes_by_priority(index, top_n=top_n)


def truncate_anchor_slice(text: str, *, max_chars: int) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated)."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    if len(text) <= max_chars:
        return text, False
    marker = "\n… [HYPO slice truncated]\n"
    budget = max(1, max_chars - len(marker))
    return text[:budget].rstrip() + marker, True


MIN_FIELD_TAG_MATCH_LEN = 3
PRISM_AXIS_LETTERS = frozenset("slkm")
DEFAULT_ROUTE_MAX_NODES = 8
DEFAULT_REPAIR_SLICE_MAX_CHARS = 800
DEFAULT_REPAIR_MAX_TOTAL_CHARS = 4800
REPAIR_MIN_PARAGRAPH_HITS = 2
REPAIR_MIN_PARAGRAPH_HITS_LARGE_DOC = 2
REPAIR_LARGE_DOC_CHARS = 12_000


def prism_axis_field_tag(axis: str) -> str:
    """Stable prism axis tag — bare single-letter tags are not used for routing."""
    letter = str(axis or "S").strip().lower()[:1]
    if letter not in PRISM_AXIS_LETTERS:
        letter = "s"
    return f"prism_axis_{letter}"


def query_match_tokens(query: str, *, min_len: int = 2) -> list[str]:
    """Tokenize query for relevance scoring (deduped, order preserved)."""
    seen: set[str] = set()
    tokens: list[str] = []
    for token in re.split(r"[^a-zA-Z0-9_가-힣$]+", query.lower()):
        if len(token) < min_len or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def score_text_query_relevance(text: str, query: str) -> int:
    """Count distinct query tokens present in text."""
    if not text.strip():
        return 0
    low = text.lower()
    return sum(1 for token in query_match_tokens(query) if token in low)


def jaccard_similarity(a: str, b: str) -> float:
    """Token-set Jaccard for repair slice gating ([HYPO] proxy)."""
    sa = set(re.findall(r"[a-zA-Z0-9_가-힣$]+", a.lower()))
    sb = set(re.findall(r"[a-zA-Z0-9_가-힣$]+", b.lower()))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def slice_improves_query_jaccard(query: str, header: str, slice_text: str) -> bool:
    """Inject slice only when query Jaccard vs header strictly improves."""
    if not slice_text.strip():
        return False
    j_before = jaccard_similarity(query, header)
    j_after = jaccard_similarity(query, f"{header}\n{slice_text}")
    return j_after > j_before


REPAIR_V2_NOISE_GUARD_MIN_EXTRA_CHARS = 192
REPAIR_V2_NOISE_GUARD_MIN_JACCARD_GAIN = 0.02
REPAIR_V2_NOISE_GUARD_MAX_BULK_RATIO = 1.35
DRIFT_REPAIR_MUTATIONS = frozenset({"stale_sha", "wrong_json_pointer", "header_drop"})


def apply_repair_v2_noise_guard(
    query: str,
    *,
    baseline_text: str,
    repair_text: str,
    min_extra_chars: int = REPAIR_V2_NOISE_GUARD_MIN_EXTRA_CHARS,
    min_jaccard_gain: float = REPAIR_V2_NOISE_GUARD_MIN_JACCARD_GAIN,
    max_bulk_ratio: float = REPAIR_V2_NOISE_GUARD_MAX_BULK_RATIO,
    mutation: str = "baseline",
) -> str:
    """Drop repair slices when they add bulk without improving query Jaccard ([HYPO] B-track)."""
    if not query.strip() or not repair_text.strip():
        return repair_text
    if not baseline_text.strip():
        return repair_text
    extra_chars = len(repair_text) - len(baseline_text)
    if extra_chars <= min_extra_chars:
        return repair_text
    j_base = jaccard_similarity(query, baseline_text)
    j_repair = jaccard_similarity(query, repair_text)
    if j_repair <= j_base:
        return baseline_text
    gain = j_repair - j_base
    bulk_ratio = len(repair_text) / max(len(baseline_text), 1)
    gain_floor = min_jaccard_gain
    ratio_cap = max_bulk_ratio
    if mutation in DRIFT_REPAIR_MUTATIONS:
        gain_floor = max(gain_floor, 0.025)
        ratio_cap = min(ratio_cap, 1.25)
    if bulk_ratio > ratio_cap and gain < gain_floor:
        return baseline_text
    return repair_text


def assemble_ops_memory_repair_v2_text(
    root: Path,
    routed: list[tuple[str, dict[str, Any]]],
    *,
    slice_max_chars: int = DEFAULT_REPAIR_SLICE_MAX_CHARS,
    query: str = "",
    coordinate_filter: bool = False,
    max_total_chars: int | None = DEFAULT_REPAIR_MAX_TOTAL_CHARS,
    mutation: str = "baseline",
    noise_guard: bool = True,
) -> str:
    """Header-only baseline vs repair slices; optional noise guard for pinset stability."""
    baseline = assemble_ops_memory_pins_text(
        root,
        routed,
        include_slice=False,
        max_total_chars=max_total_chars,
        mutation=mutation,
    )
    repaired = assemble_ops_memory_pins_text(
        root,
        routed,
        include_slice=True,
        slice_max_chars=slice_max_chars,
        query=query,
        coordinate_filter=coordinate_filter,
        max_total_chars=max_total_chars,
        mutation=mutation,
    )
    if not noise_guard:
        return repaired
    return apply_repair_v2_noise_guard(
        query,
        baseline_text=baseline,
        repair_text=repaired,
        mutation=mutation,
    )


def _window_around_best_token_hit(text: str, tokens: list[str], max_chars: int) -> str:
    if not tokens or not text:
        return ""
    low = text.lower()
    best_start = 0
    best_score = -1
    step = max(1, max_chars // 4)
    for start in range(0, max(1, len(text)), step):
        end = min(len(text), start + max_chars)
        window = low[start:end]
        score = sum(1 for token in tokens if token in window)
        if score > best_score:
            best_score = score
            best_start = start
    if best_score <= 0:
        return ""
    excerpt = text[best_start : best_start + max_chars]
    preview, _ = truncate_anchor_slice(excerpt, max_chars=max_chars)
    return preview


def extract_query_relevant_excerpt(
    text: str,
    query: str,
    *,
    max_chars: int,
    min_paragraph_hits: int | None = None,
) -> str:
    """Pick paragraphs/lines that overlap query tokens; skip pure noise headers."""
    tokens = query_match_tokens(query)
    if not text.strip():
        return ""
    if not tokens:
        preview, _ = truncate_anchor_slice(text, max_chars=max_chars)
        return preview

    if min_paragraph_hits is None:
        min_paragraph_hits = (
            REPAIR_MIN_PARAGRAPH_HITS_LARGE_DOC
            if len(text) >= REPAIR_LARGE_DOC_CHARS
            else REPAIR_MIN_PARAGRAPH_HITS
        )

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) < 2:
        paragraphs = [ln.strip() for ln in text.splitlines() if ln.strip()]

    scored: list[tuple[int, str]] = []
    for chunk in paragraphs:
        low = chunk.lower()
        score = sum(1 for token in tokens if token in low)
        if score >= min_paragraph_hits:
            scored.append((score, chunk))

    if scored:
        scored.sort(key=lambda item: (-item[0], -len(item[1])))
        parts: list[str] = []
        used = 0
        for _score, chunk in scored:
            if used >= max_chars:
                break
            budget = max_chars - used
            piece, _ = truncate_anchor_slice(chunk, max_chars=budget)
            if piece.strip():
                parts.append(piece)
                used += len(piece) + 2
        if parts:
            joined = "\n\n".join(parts)
            preview, _ = truncate_anchor_slice(joined, max_chars=max_chars)
            return preview

    window = _window_around_best_token_hit(text, tokens, max_chars)
    if window.strip():
        return window
    return ""


def extract_node_repair_slice(
    root: Path,
    node: dict[str, Any],
    query: str,
    *,
    max_chars: int,
    coordinate_filter: bool = False,
    use_relevance_filter: bool = True,
    pin_header: str = "",
    mutation: str = "baseline",
) -> str:
    """Repair_v2 slice extractor — registry chunks + json_pointer + relevance window."""
    essence = str(node.get("essence") or "")
    header_for_gate = pin_header.strip() or essence
    if node.get("slice_kind") == "registry_chunk":
        path = resolve_path(root, node["file_path"])
        if not path.is_file():
            raise FileNotFoundError(f"Missing indexed file: {node['file_path']}")
        block = path.read_text(encoding="utf-8", errors="replace")
        if mutation == "header_drop" and block:
            lines = block.splitlines()
            block = "\n".join(lines[1:]) if len(lines) > 1 else block
    elif node.get("slice_kind") == "json_pointer":
        if coordinate_filter:
            pointers = node.get("json_pointers") or []
            filtered = filter_json_pointers_for_query(pointers, query)
            block = extract_json_slice_from_node(root, node, pointers=filtered)
        else:
            block = extract_node_from_index(root, node)
    else:
        block = extract_node_from_index(root, node)

    if use_relevance_filter and query.strip():
        scoring_query = f"{query} {essence}".strip()
        excerpt = extract_query_relevant_excerpt(
            block, scoring_query, max_chars=max_chars
        )
        if excerpt.strip() and slice_improves_query_jaccard(
            query, header_for_gate, excerpt
        ):
            return excerpt
        if score_text_query_relevance(block, scoring_query) <= 0:
            return ""
        preview, _ = truncate_anchor_slice(block, max_chars=max_chars)
        if slice_improves_query_jaccard(query, header_for_gate, preview):
            return preview
        return ""

    preview, _ = truncate_anchor_slice(block, max_chars=max_chars)
    if use_relevance_filter and query.strip():
        if slice_improves_query_jaccard(query, header_for_gate, preview):
            return preview
        return ""
    return preview


def assemble_ops_memory_pins_text(
    root: Path,
    routed: list[tuple[str, dict[str, Any]]],
    *,
    include_slice: bool = False,
    slice_max_chars: int = DEFAULT_REPAIR_SLICE_MAX_CHARS,
    query: str = "",
    coordinate_filter: bool = False,
    max_total_chars: int | None = DEFAULT_REPAIR_MAX_TOTAL_CHARS,
    mutation: str = "baseline",
) -> str:
    """Assemble routed pins with optional repair slices and a total char budget."""
    lines: list[str] = []
    used = 0
    for _node_id, node in routed:
        header_parts = [node.get("essence") or ""]
        header_parts.extend(str(t) for t in (node.get("must_keep_tags") or []))
        header = "\n".join(p for p in header_parts if p)
        if max_total_chars is not None and used >= max_total_chars:
            break
        if max_total_chars is not None and header and used + len(header) > max_total_chars:
            remaining = max_total_chars - used
            lines.append(header[:remaining])
            break
        if header:
            lines.append(header)
            used += len(header) + 1
        if not include_slice:
            continue
        remaining = None
        if max_total_chars is not None:
            remaining = max(0, max_total_chars - used)
            if remaining < 1:
                break
        cap = slice_max_chars if remaining is None else min(slice_max_chars, remaining)
        preview = extract_node_repair_slice(
            root,
            node,
            query,
            max_chars=cap,
            coordinate_filter=coordinate_filter,
            use_relevance_filter=True,
            pin_header=header,
            mutation=mutation,
        )
        if not preview.strip():
            continue
        accumulated = "\n".join(lines)
        if query.strip() and not slice_improves_query_jaccard(
            query, accumulated, preview
        ):
            continue
        lines.append(preview)
        used += len(preview) + 1
    return "\n".join(lines)


def dedupe_routed_by_file_path(
    ranked: list[tuple[str, dict[str, Any]]],
) -> list[tuple[str, dict[str, Any]]]:
    seen: set[str] = set()
    out: list[tuple[str, dict[str, Any]]] = []
    for node_id, node in ranked:
        fp = str(node.get("file_path") or node_id)
        if fp in seen:
            continue
        seen.add(fp)
        out.append((node_id, node))
    return out


def build_web_ops_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes from web_ops *_latest artifacts (skip missing files)."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in WEB_OPS_JSON_SPECS:
        try:
            nodes[spec.node_id] = build_json_slice_node_entry(root, spec)
        except FileNotFoundError:
            continue
    return nodes


def build_domain_adapter_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes for Pixel Battalion + Lens Audio adapters ([HYPO])."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in DOMAIN_ADAPTER_JSON_SPECS:
        try:
            entry = build_json_slice_node_entry(root, spec)
            entry["overlay_role"] = "domain_adapters_v1"
            nodes[spec.node_id] = entry
        except FileNotFoundError:
            continue
    return nodes


def build_fills_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes from multi-res fills index (skip missing files)."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in FILLS_JSON_SPECS:
        try:
            nodes[spec.node_id] = build_json_slice_node_entry(root, spec)
        except FileNotFoundError:
            continue
    return nodes


def build_theory_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes from theory mathematization gate + 75-formula SSOT."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in THEORY_JSON_SPECS:
        try:
            nodes[spec.node_id] = build_json_slice_node_entry(root, spec)
        except FileNotFoundError:
            continue
    return nodes


def build_logos_math_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes from Logos 4D/gematria/anchor/router artifacts ([HYPO])."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in LOGOS_MATH_JSON_SPECS:
        try:
            entry = build_json_slice_node_entry(root, spec)
            entry["overlay_role"] = "logos_math"
            nodes[spec.node_id] = entry
        except (FileNotFoundError, ValueError, KeyError):
            continue
    return nodes


def build_ltm_a2a_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build ltm_* JSON-slice nodes for LTM ↔ A2A bridge map ([HYPO] / B-track)."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in LTM_A2A_JSON_SPECS:
        try:
            entry = build_json_slice_node_entry(root, spec)
            entry["overlay_role"] = "ltm_a2a"
            concept_id = LTM_A2A_NODE_CONCEPT_IDS.get(spec.node_id, spec.node_id)
            entry["ltm_concept_id"] = concept_id
            nodes[spec.node_id] = entry
        except FileNotFoundError:
            continue
    return nodes


def merge_overlay_nodes(
    index: dict[str, Any],
    overlay_nodes: dict[str, dict[str, Any]],
    *,
    overlay_label: str = "web_ops_v1",
) -> dict[str, Any]:
    merged = dict(index)
    nodes = dict(index.get("nodes") or {})
    nodes.update(overlay_nodes)
    merged["nodes"] = nodes
    merged["index_version"] = "1.1"
    overlays = list(merged.get("overlays") or [])
    if overlay_label not in overlays:
        overlays.append(overlay_label)
    merged["overlays"] = overlays
    merged["last_updated_utc"] = utc_now_iso()
    return merged


def ensure_lane_pack_index(
    root: Path,
    index: dict[str, Any],
    lane: str,
) -> dict[str, Any]:
    """Merge in-memory overlays when lane pack nodes are missing (web_ops JSON slices)."""
    lane_key = lane.strip().lower()
    if lane_key not in LANE_OPS_PACKS:
        raise ValueError(
            f"unknown lane {lane!r}; expected one of {sorted(LANE_OPS_PACKS)}"
        )
    nodes = index.get("nodes") or {}
    missing = [nid for nid in LANE_OPS_PACKS[lane_key] if nid not in nodes]
    if not missing:
        return index
    merged = index
    # web_ops lane requires JSON slice overlays from *_latest artifacts.
    if lane_key == "web_ops":
        overlay = build_web_ops_overlay_nodes(root)
        if overlay:
            merged = merge_overlay_nodes(merged, overlay, overlay_label="web_ops_v1")
    # oracle lane can include theory gate/ssot JSON slices.
    if lane_key == "oracle":
        theory_overlay = build_theory_overlay_nodes(root)
        if theory_overlay:
            merged = merge_overlay_nodes(
                merged, theory_overlay, overlay_label="theory_v1"
            )
        logos_overlay = build_logos_math_overlay_nodes(root)
        if logos_overlay:
            merged = merge_overlay_nodes(
                merged, logos_overlay, overlay_label="logos_math_v1"
            )
    if lane_key == "design":
        adapter_overlay = build_domain_adapter_overlay_nodes(root)
        if adapter_overlay:
            merged = merge_overlay_nodes(
                merged, adapter_overlay, overlay_label="domain_adapters_v1"
            )
    still = [nid for nid in LANE_OPS_PACKS[lane_key] if nid not in (merged.get("nodes") or {})]
    if not still:
        return merged
    missing = still
    raise KeyError(f"lane pack missing node: {missing[0]}")


def compute_node_sha_prefix(root: Path, node: dict[str, Any]) -> str:
    block = extract_node_from_index(root, node)
    return hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]


def verify_index_sha_drift(root: Path, index: dict[str, Any]) -> list[str]:
    """Return drift errors when live content sha differs from indexed prefix."""
    errors: list[str] = []
    for node_id, node in (index.get("nodes") or {}).items():
        stored = node.get("content_sha256_prefix")
        if not stored:
            continue
        try:
            current = compute_node_sha_prefix(root, node)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            errors.append(f"{node_id}: sha check failed: {exc}")
            continue
        if current != stored:
            errors.append(
                f"{node_id}: HOLD_POINTER_DRIFT sha {stored!r} -> {current!r}"
            )
    return errors


FIELD_TAG_SYNONYMS: dict[str, tuple[str, ...]] = {
    "nebius": ("nebius", "네비우스", "balance", "잔액", "prepaid", "선불", "$25", "billing"),
    "web_ops": (
        "web_ops",
        "web ops",
        "regime",
        "레짐",
        "게이트",
        "gate_pass",
        "portal",
        "cdp",
        "nebius",
        "네비우스",
        "잔액",
        "prepaid",
        "선불",
        "비용",
        "감사",
        "cost",
        "audit",
        "billing",
    ),
    "cost_audit": ("cost", "audit", "gpu", "spinup", "비용", "감사", "no_gpu", "결제"),
    "health": ("health", "헬스", "drift", "pointer", "observation"),
    "infra": ("infra", "gpu", "ollama", "vps", "인프라"),
    "azure": ("azure", "portal", "feasibility", "quota"),
    "regime_action": (
        "allow_read",
        "allow_prefill",
        "hold_payment",
        "hold_auth",
        "hold_human",
        "hold_unknown",
        "read_only",
        "read_only_dashboard",
        "payment_risk",
        "worst_final_action",
        "final_action",
        "regime",
        "dashboard",
    ),
}

REGIME_ACTION_QUERY_TOKENS: tuple[str, ...] = (
    "allow_read",
    "allow_prefill",
    "hold_payment",
    "hold_auth",
    "read_only_dashboard",
    "read_only",
    "payment_risk",
    "worst_final_action",
    "final_action",
)

WEB_OPS_ACTION_NODE_IDS: frozenset[str] = frozenset(
    {"prism_ops_web_ops_regime_gate", "prism_ops_web_ops_health"}
)

LANE_TOPIC_HINTS: dict[str, tuple[str, ...]] = {
    "web_ops": (
        "nebius",
        "네비우스",
        "web_ops",
        "web ops",
        "regime",
        "레짐",
        "gate",
        "게이트",
        "cost_audit",
        "비용",
        "감사",
        "azure",
        "portal",
        "gpu spinup",
        "no_gpu",
        "잔액",
        "prepaid",
        "$25",
        "cdp",
        "auth wall",
        "tier3",
    ),
    "infra": (
        "infra",
        "gpu",
        "ollama",
        "vps",
        "인프라",
        "pack 0",
        "scheduler",
        "solo stack",
        "parallel passive",
        "news neutralizer",
        "schtasks",
    ),
    "design": (
        "design",
        "showroom",
        "jemaai",
        "hub",
        "디자인",
        "쇼룸",
        "portfolio",
        "domain",
        "pixel",
        "pixel battalion",
        "sprite",
        "mkmlife",
        "audio",
        "bgm",
        "music",
        "musicgen",
        "lens audio",
        "tempo",
        "lens_safe_tempo",
    ),
    "oracle": (
        "oracle",
        "예언",
        "prophecy",
        "inception",
        "사상",
        "sasang",
        "태양인",
        "태양",
        "火剋金",
        "금器",
        "envelope",
        "oper score",
        "freeze",
    ),
    "ms": (
        "ms",
        "국방",
        "defense",
        "제출",
        "compression",
        "47.5",
        "0.890",
        "jaccard",
        "압축",
        "track a",
        "moat",
        "fail-comp",
    ),
}


def _field_tag_match_score(q: str, tag: str) -> int:
    """Score field-tag relevance; 0 = no match. Blocks bare axis letter substring leaks."""
    tag_low = tag.lower().strip()
    if not tag_low:
        return 0
    if tag_low.startswith("prism_axis_"):
        axis = tag_low.removeprefix("prism_axis_")
        if len(axis) == 1 and axis in PRISM_AXIS_LETTERS:
            needles = (
                f"prism_axis_{axis}",
                f"axis {axis}",
                f"axis:{axis}",
                f"prism {axis}",
            )
            return 3 if any(n in q for n in needles) else 0
        return 0
    if len(tag_low) < MIN_FIELD_TAG_MATCH_LEN:
        return 0
    if tag_low in q:
        return 2 + min(len(tag_low) // 12, 3)
    for synonym in FIELD_TAG_SYNONYMS.get(tag_low, (tag_low,)):
        syn = synonym.lower()
        if len(syn) < MIN_FIELD_TAG_MATCH_LEN:
            continue
        if syn in q:
            return 2
    return 0


def _query_matches_synonyms(q: str, tag: str) -> bool:
    return _field_tag_match_score(q, tag) > 0


def _query_mentions_regime_action(q: str) -> bool:
    if any(token in q for token in REGIME_ACTION_QUERY_TOKENS):
        return True
    compact = re.sub(r"[^a-z0-9_]+", "_", q)
    return any(token in compact for token in REGIME_ACTION_QUERY_TOKENS)


def route_nodes_by_field_tags(
    index: dict[str, Any],
    query: str,
    *,
    min_hits: int = 1,
    max_nodes: int | None = DEFAULT_ROUTE_MAX_NODES,
    dedupe_file_paths: bool = True,
) -> list[tuple[str, dict[str, Any]]]:
    """Keyword router for JSON overlay nodes ([HYPO] — synonym map, not embedding RAG)."""
    q = query.lower()
    scored: list[tuple[int, str, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    for node_id, node in (index.get("nodes") or {}).items():
        field_tags = [str(t) for t in node.get("field_tags") or []]
        score = sum(_field_tag_match_score(q, tag) for tag in field_tags)
        essence = (node.get("essence") or "").lower()
        tokens = [t for t in re.split(r"[^a-zA-Z0-9_가-힣]+", q) if len(t) >= 3]
        score += sum(1 for token in tokens if token in essence)
        if score > 0 and node_id not in seen_ids:
            seen_ids.add(node_id)
            scored.append((score, node_id, node))
    if _query_mentions_regime_action(q):
        for node_id, node in (index.get("nodes") or {}).items():
            if node_id in WEB_OPS_ACTION_NODE_IDS and node_id not in seen_ids:
                seen_ids.add(node_id)
                scored.append((6, node_id, node))
    scored.sort(
        key=lambda item: (-item[0], -int(item[2].get("priority", 0)), item[1])
    )
    ranked: list[tuple[str, dict[str, Any]]] = [
        (node_id, node) for _score, node_id, node in scored
    ]
    if dedupe_file_paths:
        ranked = dedupe_routed_by_file_path(ranked)
    if max_nodes is not None and len(ranked) > max_nodes:
        ranked = ranked[:max_nodes]
    if len(ranked) < min_hits:
        return ranked
    return ranked


def resolve_lane_from_topic(topic: str) -> str | None:
    """Pick LANE_OPS_PACKS key from free-text topic ([HYPO] keyword only)."""
    q = topic.lower().strip()
    if not q:
        return None
    scores: dict[str, int] = {}
    for lane, hints in LANE_TOPIC_HINTS.items():
        score = sum(1 for hint in hints if hint.lower() in q)
        if score:
            scores[lane] = score
    if not scores:
        return None
    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]
