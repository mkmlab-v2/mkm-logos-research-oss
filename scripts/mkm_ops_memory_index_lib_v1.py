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
        essence="CENTRAL 최신 운영 체크포인트 블록 — hygiene·MCP·격벽 스냅샷",
        must_keep_tags=("hygiene", "MISSION_LOG", "MCP lean"),
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


def extract_node_from_index(root: Path, node: dict[str, Any]) -> str:
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


def truncate_anchor_slice(text: str, *, max_chars: int) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated)."""
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    if len(text) <= max_chars:
        return text, False
    marker = "\n… [HYPO slice truncated]\n"
    budget = max(1, max_chars - len(marker))
    return text[:budget].rstrip() + marker, True
