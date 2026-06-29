#!/usr/bin/env python3
"""Forensics for subgraph gold Hit@k misses — q05/q10/q11/q12 focus [HYPO, B-track].

Reproducible:
  py scripts/run_logos_subgraph_gold_miss_forensics_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_subgraph_gold_miss_forensics_v1_latest.json"
DEFAULT_MISS_IDS = ("q05", "q10", "q11", "q12")


def _auto_miss_ids(eval_doc: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for row in eval_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        raw = (row.get("metrics") or {}).get("raw") or {}
        hit = raw.get("hit_at_k") or {}
        if hit.get("1") is False:
            out.append(str(row.get("id") or ""))
    return [x for x in out if x]
GOLD_EVAL = ROOT / "scripts/run_logos_subgraph_gold_eval_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _miss_tags(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    raw = (row.get("metrics") or {}).get("raw") or {}
    hit = raw.get("hit_at_k") or {}
    side = (row.get("router") or {}).get("sidecars") or {}
    if hit.get("1") is False:
        tags.append("hit_at_1_miss")
    if hit.get("3") is False:
        tags.append("hit_at_3_miss")
    if hit.get("8") is False:
        tags.append("hit_at_8_miss")
    if int(side.get("lemma_edge_hits") or 0) == 0:
        tags.append("lemma_sidecar_zero")
    if int(side.get("osi_xref_hits") or 0) == 0:
        tags.append("osi_sidecar_zero")
    if int(side.get("theographic_entity_hits") or 0) == 0:
        tags.append("theographic_sidecar_zero")
    if int(side.get("gematria_lexicon_hits") or 0) == 0:
        tags.append("gematria_sidecar_zero")
    top = raw.get("router_top_verses") or []
    gold_hits = raw.get("router_gold_hits") or []
    if gold_hits and top and gold_hits[0] != top[0]:
        tags.append("gold_not_rank1")
    lanes = row.get("router", {}).get("theme_lanes_active") or []
    if not lanes:
        tags.append("no_theme_lane")
    return tags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--miss-ids", default="", help="Comma-separated ids; empty = auto from eval Hit@1 misses")
    ap.add_argument("--skip-gold-eval", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.skip_gold_eval:
        proc = subprocess.run([PY, str(GOLD_EVAL)], cwd=str(ROOT), capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    eval_path = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
    if not eval_path.is_file():
        print(f"[ERROR] missing eval: {eval_path}", file=sys.stderr)
        return 2

    eval_doc = json.loads(eval_path.read_text(encoding="utf-8-sig"))
    miss_ids = [x.strip() for x in args.miss_ids.split(",") if x.strip()]
    if not miss_ids:
        miss_ids = _auto_miss_ids(eval_doc)

    rows_in = [r for r in (eval_doc.get("rows") or []) if isinstance(r, dict)]
    focused = [r for r in rows_in if r.get("id") in miss_ids]

    forensics_rows: list[dict[str, Any]] = []
    for row in focused:
        raw = (row.get("metrics") or {}).get("raw") or {}
        forensics_rows.append(
            {
                "id": row.get("id"),
                "query_ko": row.get("query_ko"),
                "hit_at_k": raw.get("hit_at_k"),
                "router_top_verses": (raw.get("router_top_verses") or [])[:8],
                "router_gold_hits": raw.get("router_gold_hits"),
                "path_gold_hits": raw.get("path_gold_hits"),
                "theme_lanes_active": row.get("router", {}).get("theme_lanes_active"),
                "bridges_matched": row.get("router", {}).get("bridges_matched"),
                "sidecars": row.get("router", {}).get("sidecars"),
                "miss_tags": _miss_tags(row),
            }
        )

    summary = eval_doc.get("summary") if isinstance(eval_doc.get("summary"), dict) else {}
    report = {
        "schema": "logos_subgraph_gold_miss_forensics_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "miss_query_ids": miss_ids,
        "router_version": eval_doc.get("router_version"),
        "hit_at_k_rates": summary.get("hit_at_k_rates"),
        "gold_required_all_pass": summary.get("gold_required_all_pass"),
        "rows": forensics_rows,
        "reproduce": "py scripts/run_logos_subgraph_gold_miss_forensics_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "hit_at_k_rates": summary.get("hit_at_k_rates"),
                "miss_rows": len(forensics_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
