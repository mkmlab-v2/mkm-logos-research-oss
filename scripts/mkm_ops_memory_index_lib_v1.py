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
        anchor_end="### 📦 핸드오프 · 다른 채팅 융합",
        essence="작전 보드 SSOT — 사업화·압축 격벽·Track A 금지·B2B SEND_GATE HOLD",
        must_keep_tags=("FAIL-COMP-004", "Track A", "SEND_GATE: HOLD"),
        priority=10,
    ),
    NodeSpec(
        node_id="prism_ops_central_checkpoint",
        file_path="docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        anchor_start="<!-- ATHENA_CHECKPOINT_V1_START -->",
        anchor_end="<!-- ATHENA_CHECKPOINT_V1_END -->",
        essence="CENTRAL 최신 운영 체크포인트 블록 — MISSION_LOG·research_only·격벽 스냅샷",
        must_keep_tags=("MISSION_LOG", "research_only"),
        priority=9,
    ),
    NodeSpec(
        node_id="prism_ops_mission_log_next_one",
        file_path="MISSION_LOG.md",
        anchor_start="**다음 1타 (레인 · 새 채팅):**",
        anchor_end="### 🧠 메타인지",
        essence="레인별 다음 1타 SSOT — 재개 복붙·HOLD·Track A·실매매 금지",
        must_keep_tags=("Track A", "HOLD", "금지"),
        priority=8,
    ),
    NodeSpec(
        node_id="prism_ops_lane_oracle",
        file_path="MISSION_LOG.md",
        anchor_start="| **Oracle·예언·align-panel** |",
        anchor_end="| **CROSS_REF·DSS [HYPO]** |",
        essence="Oracle 레인 다음 1타 — 예언·진화·Inception 관측 · Track A·실매매 금지",
        must_keep_tags=("Track A", "실매매", "금지"),
        priority=7,
    ),
    NodeSpec(
        node_id="prism_ops_lane_infra",
        file_path="MISSION_LOG.md",
        anchor_start="| **Infra/GPU** |",
        anchor_end="| **Clinic·SDIT·Insight** |",
        essence="Infra/GPU 레인 — Interpret·DailyOpsPatrol · Track A·live·match% 헤드라인 금지",
        must_keep_tags=("Track A", "금지", "GPU"),
        priority=7,
    ),
    NodeSpec(
        node_id="prism_ops_lane_ms",
        file_path="MISSION_LOG.md",
        anchor_start="| **MS** |",
        anchor_end="| **환자·최소영 (Track B)** |",
        essence="MS 레인 — 지휘관 수동 제출만 · 에이전트 포털·% 헤드라인 금지",
        must_keep_tags=("MS", "금지", "HOLD"),
        priority=7,
    ),
)

LANE_OPS_PACKS: dict[str, tuple[str, ...]] = {
    "oracle": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_oracle",
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
    "web_ops": (
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_web_ops_regime_gate",
        "prism_ops_web_ops_health",
    ),
}


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
        except (FileNotFoundError, ValueError) as exc:
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
) -> list[tuple[str, dict[str, Any]]]:
    """Default: top-N by priority. Lane pack: board + CENTRAL + one lane row (no full next-one table)."""
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


def build_web_ops_overlay_nodes(root: Path) -> dict[str, dict[str, Any]]:
    """Build JSON-slice nodes from web_ops *_latest artifacts (skip missing files)."""
    nodes: dict[str, dict[str, Any]] = {}
    for spec in WEB_OPS_JSON_SPECS:
        try:
            nodes[spec.node_id] = build_json_slice_node_entry(root, spec)
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
    "infra": ("infra", "gpu", "ollama", "vps", "인프라", "pack 0"),
    "oracle": ("oracle", "예언", "prophecy", "inception"),
    "ms": ("ms", "국방", "defense", "제출"),
}


def _query_matches_synonyms(q: str, tag: str) -> bool:
    tag_low = tag.lower()
    if tag_low in q:
        return True
    for synonym in FIELD_TAG_SYNONYMS.get(tag_low, (tag_low,)):
        if synonym.lower() in q:
            return True
    return False


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
) -> list[tuple[str, dict[str, Any]]]:
    """Keyword router for JSON overlay nodes ([HYPO] — synonym map, not embedding RAG)."""
    q = query.lower()
    hits: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for node_id, node in (index.get("nodes") or {}).items():
        field_tags = [str(t) for t in node.get("field_tags") or []]
        if field_tags and any(_query_matches_synonyms(q, tag) for tag in field_tags):
            if node_id not in seen:
                seen.add(node_id)
                hits.append((node_id, node))
            continue
        essence = (node.get("essence") or "").lower()
        tokens = [t for t in re.split(r"[^a-zA-Z0-9_가-힣]+", q) if len(t) >= 3]
        if any(token in essence for token in tokens):
            if node_id not in seen:
                seen.add(node_id)
                hits.append((node_id, node))
    if _query_mentions_regime_action(q):
        for node_id, node in (index.get("nodes") or {}).items():
            if node_id in WEB_OPS_ACTION_NODE_IDS and node_id not in seen:
                seen.add(node_id)
                hits.append((node_id, node))
    ranked = sorted(hits, key=lambda item: (-int(item[1].get("priority", 0)), item[0]))
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
