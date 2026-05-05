#!/usr/bin/env python3
"""Run preset searches on workspace post-it index."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence


DEFAULT_INDEX_PATH = "docs/final/artifacts/workspace_postit_index_latest.json"
DEFAULT_PRESETS_PATH = "docs/final/artifacts/workspace_postit_search_presets_v1.json"
DEFAULT_JSON_OUT = "docs/final/artifacts/workspace_postit_search_results_latest.json"
DEFAULT_MD_OUT = "docs/final/artifacts/workspace_postit_search_results_latest.md"


def load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def match_value(item_val: object, cond_val: object) -> bool:
    if isinstance(cond_val, list):
        return item_val in cond_val
    return item_val == cond_val


def match_tags(item_tags: Sequence[str], required: Sequence[str]) -> bool:
    tag_set = set(item_tags)
    return all(tag in tag_set for tag in required)


def match_path_keywords(path: str, keywords: Sequence[str]) -> bool:
    lowered = path.lower()
    return all(k.lower() in lowered for k in keywords)


def apply_filter(items: List[Dict[str, object]], rule: Dict[str, object]) -> List[Dict[str, object]]:
    matched: List[Dict[str, object]] = []
    for it in items:
        ok = True
        for key in ("type", "track", "lane", "status", "evidence_level"):
            if key in rule and not match_value(it.get(key), rule[key]):
                ok = False
                break
        if not ok:
            continue
        if "topic_tags_all" in rule:
            if not match_tags(it.get("topic_tags", []), rule["topic_tags_all"]):
                continue
        if "path_keywords_all" in rule:
            if not match_path_keywords(str(it.get("path", "")), rule["path_keywords_all"]):
                continue
        matched.append(it)
    return matched


def summarize(
    preset_id: str,
    preset_name: str,
    rule: Dict[str, object],
    results: List[Dict[str, object]],
    limit: int,
) -> Dict[str, object]:
    return {
        "preset_id": preset_id,
        "preset_name": preset_name,
        "rule": rule,
        "match_count": len(results),
        "top_paths": [r["path"] for r in results[:limit]],
    }


def write_outputs(results_payload: Dict[str, object], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(results_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Workspace Post-it Search Results (latest)",
        "",
        f"- generated_at_utc: {results_payload['generated_at_utc']}",
        f"- selected_preset: {results_payload['selected_preset']}",
        "",
    ]
    for block in results_payload["results"]:
        lines.append(f"## {block['preset_name']} (`{block['preset_id']}`)")
        lines.append(f"- match_count: {block['match_count']}")
        lines.append("")
        for p in block["top_paths"]:
            lines.append(f"- `{p}`")
        lines.append("")
    md_out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-it preset searches.")
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH)
    parser.add_argument("--presets", default=DEFAULT_PRESETS_PATH)
    parser.add_argument(
        "--preset-id",
        default="all",
        help="Preset id to run. Use 'all' to run every preset.",
    )
    parser.add_argument("--limit", type=int, default=20, help="Top paths per preset")
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    index = load_json(Path(args.index))
    presets = load_json(Path(args.presets))
    items = index.get("items", [])
    preset_list = presets.get("presets", [])

    selected = []
    if args.preset_id == "all":
        selected = preset_list
    else:
        selected = [p for p in preset_list if p.get("id") == args.preset_id]
        if not selected:
            raise SystemExit(f"[error] preset not found: {args.preset_id}")

    blocks = []
    for preset in selected:
        rule = preset.get("rule", {})
        result_rows = apply_filter(items, rule)
        blocks.append(
            summarize(
                preset_id=preset.get("id", "unknown"),
                preset_name=preset.get("name", "unknown"),
                rule=rule,
                results=result_rows,
                limit=args.limit,
            )
        )

    payload = {
        "schema": "workspace_postit_search_results_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_path": args.index,
        "presets_path": args.presets,
        "selected_preset": args.preset_id,
        "results": blocks,
    }
    write_outputs(payload, Path(args.json_out), Path(args.md_out))
    print(f"[ok] search results json: {args.json_out}")
    print(f"[ok] search results md: {args.md_out}")
    print(f"[ok] preset_count: {len(blocks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
