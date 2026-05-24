#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Logos Track B metaphor DB theme JSON to Markdown (showroom/B2B draft; NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
DEFAULT_DB_DIR = ROOT / "docs/research/logos_metaphor_db_v1"

DISCLAIMER_KO = """\
> **[TRACK B / HYPO]** 본 문서는 Logos 연구용(`hypo_research_only`) 상징 연결망이며 `[NON_GATING]`입니다. \
종교적·신학적 진리 단정·임상·투자·실매매(Track A) 근거가 **아닙니다**. \
`research_metaphor_*` 필드는 교육용 인지 은유이며 운영 게이트(`NO_GO` 등)와 **연결되지 않습니다**.
"""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_theme(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load_json(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def render_theme_markdown(doc: dict[str, Any]) -> str:
    anchor = doc["golden_anchor"]
    meta = doc["meta"]
    lines: list[str] = [
        f"# Logos 연구 카드: {anchor['theme']}\n\n",
        f"- **schema:** `{doc['schema']}`\n",
        f"- **evidence_tier:** `{meta['evidence_tier']}`\n",
        f"- **gating_status:** `{meta['gating_status']}`\n",
        f"- **weight_source:** `{meta['weight_source']}`\n\n",
        DISCLAIMER_KO,
        "\n",
        "## Golden anchor\n\n",
        f"- **node_id:** `{anchor['node_id']}`\n",
        f"- **ref:** {anchor['ref']}\n",
        f"- **text:** {anchor['text']}\n\n",
        "## Semantic nodes\n\n",
    ]
    for node in doc["semantic_nodes"]:
        lines.append(f"### `{node['node_id']}` — {node['ref']}\n\n")
        lines.append(f"- **text:** {node['text']}\n")
        lines.append(f"- **edge:** `{node['edge_type']}` → `{node['target_node']}`\n")
        lines.append(f"- **impact_weight:** {node['impact_weight']}\n")
        lines.append(f"- **domain:** `{node['research_metaphor_domain']}`\n")
        lines.append(f"- **logic:** {node['research_metaphor_logic_connection']}\n\n")
    lines.append("## Governance mapping (research metaphor only)\n\n")
    for key in sorted(doc["governance_mapping"]):
        lines.append(f"- **{key}:** {doc['governance_mapping'][key]}\n")
    lines.append("\n## Commander insight\n\n")
    lines.append(doc["commander_insight"] + "\n\n")
    lines.append(f"_ops_analogy_note: {meta['ops_analogy_note']}_\n")
    return "".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate and render Logos metaphor DB theme JSON")
    ap.add_argument("--theme-json", type=Path, help="Single theme JSON path")
    ap.add_argument(
        "--db-dir",
        type=Path,
        default=DEFAULT_DB_DIR,
        help="When --theme-json omitted: render all theme_*.json in this directory",
    )
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-md", type=Path, help="Write Markdown (single theme only)")
    ap.add_argument("--out-dir", type=Path, help="Write one .md per theme (batch)")
    ap.add_argument("--validate-only", action="store_true", help="Schema validate only; no render")
    args = ap.parse_args()

    if not args.schema.is_file():
        print(f"schema missing: {args.schema}", file=sys.stderr)
        return 2

    paths: list[Path]
    if args.theme_json:
        paths = [args.theme_json]
    else:
        paths = sorted(args.db_dir.glob("theme_*.json"))
        if not paths:
            print(f"no theme_*.json under {args.db_dir}", file=sys.stderr)
            return 2

    for path in paths:
        if not path.is_file():
            print(f"theme missing: {path}", file=sys.stderr)
            return 2
        doc = _load_json(path)
        try:
            validate_theme(doc, args.schema)
        except Exception as exc:  # noqa: BLE001 — CLI surfaces validation errors
            print(f"VALIDATE FAIL {path}: {exc}", file=sys.stderr)
            return 1
        if args.validate_only:
            print(f"OK {path}")
            continue
        md = render_theme_markdown(doc)
        if args.theme_json and args.out_md:
            args.out_md.parent.mkdir(parents=True, exist_ok=True)
            args.out_md.write_text(md, encoding="utf-8")
            print(f"Wrote {args.out_md}")
        elif args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            out = args.out_dir / f"{path.stem}.md"
            out.write_text(md, encoding="utf-8")
            print(f"Wrote {out}")
        elif args.theme_json:
            print(md, end="")
        else:
            print(f"OK {path} (use --out-dir to write markdown)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
