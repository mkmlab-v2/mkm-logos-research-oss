#!/usr/bin/env python3
"""Commander review pack for offline_4d strict LoRA micro-batch (5 rows). [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBSET = ROOT / "docs/final/artifacts/logos_review_queue_offline_4d_strict_v1_latest.json"
DEFAULT_BATCH = ROOT / "reports/logos_candidate_edge_offline_4d_lora_strict_batch_v1_latest.json"
DEFAULT_LORA = ROOT / "reports/logos_edge_hypothesis_offline_4d_strict_rank_emphasis_lora_closure_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/logos_offline_4d_strict_review_pack_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_offline_4d_strict_review_pack_v1_latest.md"
SCHEMA = "logos_offline_4d_strict_review_pack_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _render_md(payload: dict[str, Any]) -> str:
    lora = payload.get("lora_summary") or {}
    ranks = [row.get("queue_rank") for row in (payload.get("items") or []) if row.get("queue_rank") is not None]
    rank_span = f"{min(ranks)}–{max(ranks)}" if ranks else "n/a"
    lines = [
        f"# Logos offline_4d strict — Commander review pack (Wave {payload.get('wave', 2)})",
        "",
        f"- generated: `{payload.get('generated_at_utc')}`",
        "- lane: **offline_4d_knn** · `[HYPO]` · `[NON_GATING]` · research_only",
        "- **bulk merge blocked** — row-by-row decision only",
        "",
        "## LoRA rank-emphasis (template smoke, not semantic GO)",
        "",
        f"- rank_match: **{lora.get('rank_match', 'n/a')}** · steps: {lora.get('microtrain_steps', 'n/a')}",
        f"- closure: `{lora.get('closure_ref', 'n/a')}`",
        "",
        f"## Items (ranks {rank_span})",
        "",
        "| rank | pair | sim | cross-book | decision | note |",
        "|-----:|------|----:|:-----------|:---------|:-----|",
    ]
    for row in payload.get("items") or []:
        books = row.get("books") or []
        cross = "yes" if len(set(books)) > 1 else "intra"
        decision = row.get("review_decision") or "pending"
        note = row.get("review_notes_ko") or row.get("commander_hint_ko") or ""
        lines.append(
            f"| {row.get('queue_rank')} | `{row.get('pair_key')}` | {row.get('similarity')} | {cross} | {decision} | {note} |"
        )
    lines.extend(
        [
            "",
            "## Per-row checklist",
            "",
            "1. Each rank: `approve` | `defer` | `reject` via `apply_logos_candidate_edge_human_review_decisions_v1.py --queue-ranks N --decision …`",
            "2. **No** `--auto-approve-offline-4d-only` on 500 bulk",
            "3. Canonical merge: small batch + `--acknowledge-canonical-risk` + gold replay only after explicit approve",
            "",
            f"Subset JSON: `{payload.get('subset_path')}`",
            f"Strict batch: `{payload.get('strict_batch_path')}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _books_from_pair(pair_key: str) -> list[str]:
    books: list[str] = []
    for part in str(pair_key).split("|"):
        if "::" in part:
            ref = part.split("::", 1)[1]
            if "." in ref:
                books.append(ref.split(".", 1)[0])
    return books


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wave", type=int, default=2, help="Wave label for pack metadata")
    ap.add_argument("--subset-json", type=Path, default=DEFAULT_SUBSET)
    ap.add_argument("--batch-json", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--lora-closure-json", type=Path, default=DEFAULT_LORA)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    subset_path = args.subset_json if args.subset_json.is_absolute() else ROOT / args.subset_json
    subset = _read_json(subset_path)
    items = subset.get("items") or []
    if not items:
        print(json.dumps({"ok": False, "error": f"missing items: {subset_path}"}))
        return 1

    lora_doc = _read_json(
        args.lora_closure_json if args.lora_closure_json.is_absolute() else ROOT / args.lora_closure_json
    )
    samp = lora_doc.get("sample_infer_summary") or {}
    enriched: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        pk = str(row.get("pair_key") or "")
        enriched.append(
            {
                **row,
                "books": _books_from_pair(pk),
                "commander_hint_ko": "4D KNN sim≈1.0 — 표면 주제·서술 검증 후 approve; 불확실 시 defer",
            }
        )

    batch_path = args.batch_json if args.batch_json.is_absolute() else ROOT / args.batch_json
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "bulk_merge_blocked": True,
        "wave": int(args.wave),
        "subset_path": _rel(subset_path),
        "strict_batch_path": _rel(batch_path),
        "stats": subset.get("stats"),
        "lora_summary": {
            "rank_match": f"{samp.get('rank_match_pass_count')}/{samp.get('rank_match_total')}",
            "rank_accuracy": samp.get("rank_accuracy"),
            "microtrain_steps": (lora_doc.get("artifacts") or {}).get("microtrain_max_steps"),
            "closure_ref": _rel(
                args.lora_closure_json if args.lora_closure_json.is_absolute() else ROOT / args.lora_closure_json
            ),
            "interpretation_ko": "LoRA rank-emphasis = format template only; not semantic approval",
        },
        "items": enriched,
        "review_instructions_ko": [
            "offline_4d strict 5건 — 건별 approve/defer/reject",
            "500 bulk auto-approve 금지",
            "canonical merge는 승인 건만 소배치 promote",
        ],
    }

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md), "items": len(enriched)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
