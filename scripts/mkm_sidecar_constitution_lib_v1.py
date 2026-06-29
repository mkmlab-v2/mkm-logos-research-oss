"""CONSTITUTION path/gate sidecar — anchor slices only ([HYPO] / research_only).

Original `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` stays SSOT on disk.
Compressed JSON is for patrol/resume injection only — separate domain from ops memory index.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mkm_ops_memory_index_lib_v1 import (
    extract_anchor_block,
    read_lines,
    resolve_path,
    utc_now_iso,
    verify_must_keep_tags,
)

ROOT = Path(__file__).resolve().parents[1]

CONSTITUTION_REL = "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
DEFAULT_SIDECAR_PATH = ROOT / "storage" / "meta" / "mkm_sidecar_constitution_paths_v1.json"

PATH_IN_BACKTICKS_RE = re.compile(
    r"`((?:scripts|docs|projects|tests|data|storage|memory|tools|\.github)/[^`\s]+?)`"
)


@dataclass(frozen=True)
class SegmentSpec:
    segment_id: str
    anchor_start: str
    anchor_end: str | None
    essence: str
    must_keep_tags: tuple[str, ...]
    priority: int = 5
    max_chars: int | None = None


SEGMENT_SPECS: tuple[SegmentSpec, ...] = (
    SegmentSpec(
        segment_id="fact_lock_p0_pointer",
        anchor_start="> **정합성 메모",
        anchor_end="## 1. 검증 범위",
        essence=(
            "Stale CONSTITUTION prose is not law — "
            "scripts/verify_p0_constitution_gate_paths.ps1 required list wins"
        ),
        must_keep_tags=("verify_p0_constitution_gate_paths.ps1",),
        priority=10,
        max_chars=4000,
    ),
    SegmentSpec(
        segment_id="compression_factlock_table",
        anchor_start="### 1.2 압축·해석 파이프라인 Fact-Lock",
        anchor_end="### 1.2.1 MKM Control-Integrity",
        essence="Track A/B compression SSOT paths (SLA, interpretation fact-lock, bundles)",
        must_keep_tags=(
            "COMPRESSION_SLA_POLICY_V1.md",
            "COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK",
        ),
        priority=8,
        max_chars=12000,
    ),
    SegmentSpec(
        segment_id="phase1_ops_gate_table",
        anchor_start="### 13.1 Phase 1 체인·레지스트리",
        anchor_end="### 13.1.b n8n",
        essence=(
            "Windows Phase1 ops chain, constitution gates, trading go/nogo pointers "
            "(observation — not autonomous strategy engine)"
        ),
        must_keep_tags=(
            "verify_p0_constitution_gate_paths.ps1",
            "ops_phase1_chain_report_latest.json",
        ),
        priority=7,
        max_chars=8000,
    ),
    SegmentSpec(
        segment_id="logos_ops_memory_cursor_inject",
        anchor_start="**보강 (2026-06-19 — Logos/4D ops memory Cursor inject",
        anchor_end="**보강 (2026-06-16 — 4축 독립 승격 가드레일):**",
        essence=(
            "Oracle Logos Cursor inject Tier-1 module SSOT — overlay + readiness gate; "
            "≠ CONSTITUTION full rewrite; B-track HOLD; Logos [NON_GATING]"
        ),
        must_keep_tags=(
            "run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
            "logos_theory_implementation_wiring_v1.json",
        ),
        priority=9,
        max_chars=4000,
    ),
)


def truncate_block(text: str, *, max_chars: int | None) -> tuple[str, bool]:
    if max_chars is None or len(text) <= max_chars:
        return text, False
    marker = "\n… [constitution sidecar truncated]\n"
    budget = max(1, max_chars - len(marker))
    return text[:budget].rstrip() + marker, True


def extract_paths_from_block(block: str, *, limit: int = 64) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in PATH_IN_BACKTICKS_RE.finditer(block):
        path = match.group(1).strip()
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
        if len(out) >= limit:
            break
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_segment_entry(root: Path, spec: SegmentSpec) -> dict[str, Any]:
    path = resolve_path(root, CONSTITUTION_REL)
    if not path.is_file():
        raise FileNotFoundError(f"Missing CONSTITUTION SSOT: {CONSTITUTION_REL}")

    lines = read_lines(path)
    block, line_range = extract_anchor_block(
        lines,
        anchor_start=spec.anchor_start,
        anchor_end=spec.anchor_end,
    )
    verify_must_keep_tags(block, spec.must_keep_tags)

    body, truncated = truncate_block(block, max_chars=spec.max_chars)
    extracted = extract_paths_from_block(block)

    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return {
        "segment_id": spec.segment_id,
        "source_file": CONSTITUTION_REL,
        "anchor_start": spec.anchor_start,
        "anchor_end": spec.anchor_end,
        "line_range": list(line_range),
        "essence": spec.essence,
        "must_keep_tags": list(spec.must_keep_tags),
        "priority": spec.priority,
        "char_count": len(body),
        "truncated": truncated,
        "content_sha256_prefix": digest,
        "extracted_paths": extracted,
        "body_markdown": body,
    }


def build_sidecar_document(root: Path) -> dict[str, Any]:
    from datetime import datetime, timezone

    source_path = resolve_path(root, CONSTITUTION_REL)
    source_mtime_utc = (
        datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    segments: dict[str, Any] = {}
    for spec in SEGMENT_SPECS:
        segments[spec.segment_id] = build_segment_entry(root, spec)

    all_paths: list[str] = []
    seen: set[str] = set()
    for seg in segments.values():
        for p in seg.get("extracted_paths") or []:
            if p not in seen:
                seen.add(p)
                all_paths.append(p)

    return {
        "schema": "mkm_sidecar_constitution_paths_v1",
        "sidecar_version": "1.0",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] constitution path sidecar — slices only; "
            "CONSTITUTION MD remains SSOT; no Track A·live merge"
        ),
        "source_ssot": CONSTITUTION_REL,
        "source_sha256": sha256_file(source_path),
        "source_mtime_utc": source_mtime_utc,
        "last_built_utc": utc_now_iso(),
        "segments": segments,
        "path_pin_union": all_paths[:96],
    }


def top_segments_by_priority(
    sidecar: dict[str, Any],
    *,
    top_n: int = 3,
) -> list[tuple[str, dict[str, Any]]]:
    segments = sidecar.get("segments") or {}
    ranked = sorted(
        segments.items(),
        key=lambda item: (-int(item[1].get("priority", 0)), item[0]),
    )
    return ranked[:top_n]


def constitution_pins_for_resume(
    sidecar: dict[str, Any],
    *,
    top_n: int = 3,
    include_body: bool = False,
    body_max_chars: int = 600,
) -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    for seg_id, seg in top_segments_by_priority(sidecar, top_n=top_n):
        pin: dict[str, Any] = {
            "segment_id": seg_id,
            "essence": seg.get("essence"),
            "must_keep_tags": seg.get("must_keep_tags") or [],
            "line_range": seg.get("line_range"),
            "path_count": len(seg.get("extracted_paths") or []),
            "top_paths": (seg.get("extracted_paths") or [])[:10],
        }
        if include_body:
            body = seg.get("body_markdown") or ""
            if len(body) > body_max_chars:
                body = body[: body_max_chars - 40].rstrip() + "\n… [truncated]\n"
            pin["body_preview"] = body
        pins.append(pin)
    return pins
