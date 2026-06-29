#!/usr/bin/env python3
"""Resolve B2B off-the-shelf SKU spec → shard paths. [HYPO] / research_only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SPEC = Path("docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json")


def load_sku_spec(spec_path: Path) -> dict[str, Any]:
    p = spec_path.resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing sku spec: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("sku spec must be a JSON object")
    return doc


def list_external_skus(spec: dict[str, Any]) -> list[str]:
    skus = spec.get("skus")
    if not isinstance(skus, list):
        return []
    out: list[str] = []
    for row in skus:
        if isinstance(row, dict) and row.get("external_sku"):
            out.append(str(row["external_sku"]))
    return out


def resolve_external_sku(
    spec: dict[str, Any],
    external_sku: str,
) -> dict[str, Any]:
    want = str(external_sku).strip()
    skus = spec.get("skus")
    if not isinstance(skus, list):
        raise KeyError(f"unknown sku {want!r}")
    for row in skus:
        if isinstance(row, dict) and str(row.get("external_sku", "")) == want:
            return row
    known = list_external_skus(spec)
    raise KeyError(f"unknown sku {want!r}; known: {known}")


def load_shard_json(workspace_root: Path, rel_or_abs: str | Path) -> dict[str, Any]:
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = (workspace_root / p).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing shard json: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"shard json must be object: {p}")
    return doc


def build_sku_context(
    *,
    workspace_root: Path,
    spec_path: Path,
    external_sku: str | None,
    shard_json_override: Path | None,
) -> dict[str, Any]:
    if external_sku is None and shard_json_override is None:
        return {}

    ctx: dict[str, Any] = {
        "routing_wiring": "metadata_only_v1",
        "routing_note_ko": "PoC compress는 텍스트 키워드 자동 라우팅 유지 — SKU/b2b 샤드는 카탈로그·향후 강제 라우팅용.",
        "research_only": True,
        "spec_path": str(spec_path.resolve()).replace("\\", "/"),
    }

    if external_sku:
        spec = load_sku_spec(spec_path)
        row = resolve_external_sku(spec, external_sku)
        ctx["external_sku"] = external_sku
        ctx["gtm_industry_ko"] = row.get("gtm_industry_ko")
        ctx["industry_fit_status"] = row.get("industry_fit_status")
        ctx["legacy_shard_path"] = row.get("legacy_shard_path")
        ctx["b2b_shard_path"] = row.get("b2b_shard_path")
        if row.get("legacy_shard_path"):
            leg = load_shard_json(workspace_root, str(row["legacy_shard_path"]))
            ctx["legacy_shard_id"] = leg.get("shard_id")
        if row.get("b2b_shard_path"):
            b2b = load_shard_json(workspace_root, str(row["b2b_shard_path"]))
            ctx["b2b_shard_id"] = b2b.get("shard_id")
            ctx["forced_shard_id"] = b2b.get("shard_id")
            ctx["b2b_routing_keywords_top"] = list(b2b.get("routing_keywords", []))[:8]

    if shard_json_override is not None:
        override = load_shard_json(workspace_root, shard_json_override)
        ctx["shard_json_override"] = str(shard_json_override.resolve()).replace("\\", "/")
        ctx["override_shard_id"] = override.get("shard_id")

    return ctx
