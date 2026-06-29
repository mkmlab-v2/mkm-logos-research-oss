#!/usr/bin/env python3
"""Commander review pack for covenant-convergence ann_lite subset ([HYPO] B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBSET = ROOT / "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/logos_covenant_convergence_review_pack_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_covenant_convergence_review_pack_v1_latest.md"
SCHEMA = "logos_covenant_convergence_review_pack_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _render_md(payload: dict[str, Any]) -> str:
    filt = payload.get("filter") or {}
    stats = payload.get("stats") or {}
    lines = [
        "# Logos covenant convergence — Commander review pack",
        "",
        f"- generated: `{payload.get('generated_at_utc')}`",
        "- lane: **ann_lite primary** · `[HYPO]` · `[NON_GATING]` · research_only",
        "",
        "## Filter",
        "",
        f"- theme_ids: {', '.join(filt.get('theme_ids') or [])}",
        f"- max_items: **{filt.get('max_items')}** · anchor verses: **{filt.get('anchor_verse_count')}**",
        "",
        "## Stats",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| selected | {stats.get('selected_count', 'n/a')} |",
        f"| pending_review | {stats.get('pending_review', 'n/a')} |",
        f"| approved | {stats.get('approved_count', 'n/a')} |",
        "",
        "## Items (review order)",
        "",
        "| rank | pair | similarity | decision |",
        "|-----:|------|----------:|:---------|",
    ]
    for row in payload.get("items") or []:
        decision = row.get("review_decision") or "pending"
        lines.append(
            f"| {row.get('queue_rank')} | `{row.get('pair_key')}` | {row.get('similarity')} | {decision} |"
        )
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "1. Each row: `approve` | `reject` | `defer` in queue JSON",
            "2. Do **not** bulk-merge offline_4d 500 — LoRA strict 소배치만",
            "3. Canonical merge: `--acknowledge-canonical-risk` + gold/subgraph replay",
            "",
            f"Subset JSON: `{payload.get('subset_path')}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subset-json", type=Path, default=DEFAULT_SUBSET)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    subset_path = args.subset_json if args.subset_json.is_absolute() else ROOT / args.subset_json
    subset = _read_json(subset_path)
    if not subset.get("items"):
        print(json.dumps({"ok": False, "error": f"missing items: {subset_path}"}))
        return 1

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "subset_path": str(subset_path.relative_to(ROOT)).replace("\\", "/"),
        "filter": subset.get("filter"),
        "stats": subset.get("stats"),
        "items": subset.get("items"),
        "review_instructions_ko": [
            "covenant-convergence 15건은 ann_lite primary 샘플 검수용",
            "승인은 queue JSON review_decision 필드에 기록",
            "canonical merge는 별도 소배치 체인만",
        ],
    }

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
