#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit showroom Logos research thin-slice JSON from docs/research/logos_metaphor_db_v1 (NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "docs/research/logos_metaphor_db_v1"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_research_slice_v0.json"
)

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "연구용 상징 연결망 스냅샷입니다. 종교·신학적 진리·투자·임상·실매매(Track A) 근거가 아닙니다. "
        "research_metaphor_* 필드는 운영 게이트와 무관합니다."
    ),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _normalize_node_id(node_id: str) -> str:
    """Map research DB ids to showroom schema pattern ^NODE_[A-Z0-9_]+$."""
    s = str(node_id).upper().replace("-", "_")
    s = re.sub(r"[^A-Z0-9_]", "_", s)
    if not s.startswith("NODE_"):
        s = "NODE_" + s
    return s


def _theme_summary(path: Path, doc: dict[str, Any]) -> dict[str, Any]:
    anchor = doc["golden_anchor"]
    nodes = []
    for n in doc.get("semantic_nodes") or []:
        row = dict(n)
        if "node_id" in row:
            row["node_id"] = _normalize_node_id(row["node_id"])
        nodes.append(row)
    return {
        "theme_id": path.stem,
        "schema": doc["schema"],
        "meta": doc["meta"],
        "golden_anchor": anchor,
        "semantic_nodes": nodes,
        "governance_mapping": doc["governance_mapping"],
        "commander_insight": doc["commander_insight"],
    }


def build_slice(db_dir: Path, schema_path: Path) -> dict[str, Any]:
    themes_paths = sorted(db_dir.glob("theme_*.json"))
    if not themes_paths:
        raise FileNotFoundError(f"no theme_*.json in {db_dir}")
    themes: list[dict[str, Any]] = []
    for path in themes_paths:
        doc = _load(path)
        _validate(doc, schema_path)
        themes.append(_theme_summary(path, doc))
    return {
        "schema_version": "showroom_logos_research_slice_v0",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disclaimer": DISCLAIMER,
        "source_db_dir": str(db_dir.relative_to(ROOT)).replace("\\", "/"),
        "theme_count": len(themes),
        "themes": themes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build showroom Logos research slice JSON")
    ap.add_argument("--db-dir", type=Path, default=DEFAULT_DB)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.schema.is_file():
        print(f"schema missing: {args.schema}", file=sys.stderr)
        return 2
    if not args.db_dir.is_dir():
        print(f"db dir missing: {args.db_dir}", file=sys.stderr)
        return 2

    try:
        doc = build_slice(args.db_dir, args.schema)
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_json} themes={doc['theme_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
