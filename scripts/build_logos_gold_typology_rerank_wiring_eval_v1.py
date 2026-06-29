#!/usr/bin/env python3
"""Gold 8-item typology rerank wiring eval — CPU shadow, reports-only."""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_logos_ann_typology_boost_v1 import apply_typology_boost, match_lexicon_entries
from scripts.build_logos_gold_query_eval_report_v1 import (
    _artifact_paths,
    _collect_ann_verses,
    _hit_at_k,
    _match_gold,
    _read_json,
    normalize_verse_ref,
)

DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
DEFAULT_EVAL = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_gold_typology_rerank_wiring_v1_latest.json"
CONTRACT = ROOT / "docs/final/artifacts/logos_gold_typology_rerank_wiring_contract_v1.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"


def _strip_typology_boost(ann: dict[str, Any]) -> dict[str, Any]:
    doc = deepcopy(ann)
    injected = set((doc.get("typology_boost") or {}).get("injected_verse_ids") or [])
    if injected:
        doc["top_k"] = [r for r in (doc.get("top_k") or []) if str(r.get("verse_id")) not in injected]
    doc.pop("typology_boost", None)
    note = str(doc.get("notes") or "")
    doc["notes"] = note.replace("typology_boost applied (CPU lexicon; not semantic re-encode).", "").strip()
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--baseline-eval", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-contract", type=Path, default=CONTRACT)
    args = ap.parse_args()

    gold_doc = _read_json(args.gold_json)
    lexicon = _read_json(args.lexicon_json)
    baseline_eval = _read_json(args.baseline_eval)
    baseline_by_id = {r["id"]: r for r in baseline_eval.get("rows") or [] if r.get("id")}

    rows = []
    wiring_ok = 0
    uplift_count = 0

    for item in gold_doc.get("items") or []:
        qid = str(item.get("id") or "")
        query = str(item.get("query_ko") or "")
        paths = _artifact_paths(qid)
        ann_path = paths["ann"]
        ann = _read_json(ann_path)
        gold_ids = [normalize_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
        prefixes = [str(x) for x in (item.get("gold_verse_prefixes") or [])]

        entries = match_lexicon_entries(query=query, query_id=qid, lexicon=lexicon)
        before_ann = _strip_typology_boost(ann) if ann else {}
        after_ann = ann if (ann.get("typology_boost") or {}).get("applied") else {}
        if ann and not after_ann.get("typology_boost", {}).get("applied"):
            try:
                after_ann, _meta = apply_typology_boost(before_ann, query=query, query_id=qid, lexicon=lexicon)
            except ValueError:
                after_ann = before_ann

        before_hits = _match_gold(_collect_ann_verses(before_ann), gold_ids, prefixes)
        after_hits = _match_gold(_collect_ann_verses(after_ann), gold_ids, prefixes)
        hit8_before = _hit_at_k(_collect_ann_verses(before_ann), gold_ids, prefixes, 8)
        hit8_after = _hit_at_k(_collect_ann_verses(after_ann), gold_ids, prefixes, 8)
        uplift = len(after_hits) > len(before_hits) or (hit8_after and not hit8_before)
        if uplift:
            uplift_count += 1

        baseline_row = baseline_by_id.get(qid) or {}
        router_gate = baseline_row.get("gate_pass")
        wired = ann_path.is_file() and bool(entries)
        if wired:
            wiring_ok += 1

        rows.append(
            {
                "id": qid,
                "query_ko": query,
                "ann_path": str(ann_path.relative_to(ROOT)).replace("\\", "/") if ann_path.is_relative_to(ROOT) else str(ann_path),
                "ann_present": ann_path.is_file(),
                "lexicon_entries_matched": [e.get("theme_id") for e in entries],
                "typology_wiring_ok": wired,
                "gold_hit_before_boost": before_hits[:8],
                "gold_hit_after_boost": after_hits[:8],
                "hit_at_8_before": hit8_before,
                "hit_at_8_after": hit8_after,
                "uplift_vs_stripped_baseline": uplift,
                "baseline_router_gate_pass": router_gate,
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "schema": "logos_gold_typology_rerank_wiring_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "items": len(rows),
            "wiring_ok": f"{wiring_ok}/{len(rows)}",
            "uplift_count": uplift_count,
            "baseline_gold_required_all_pass": (baseline_eval.get("summary") or {}).get("gold_required_all_pass"),
        },
        "interpretation_guard": "Wiring PoC only — does not replace logos_gold_query_eval SSOT.",
        "rows": rows,
    }
    contract = {
        "schema": "logos_gold_typology_rerank_wiring_contract_v1",
        "version": "1.0.0",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "batch_script": "scripts/Run-LogosAnnTypologyBoostBatch_v1.ps1",
        "eval_script": "scripts/build_logos_gold_query_eval_report_v1.py",
        "lexicon": "docs/final/fixtures/logos_ann_typology_lexicon_v1.json",
        "ann_dir": "reports/magic_orb_insight_by_query",
        "query_ids": [r["id"] for r in rows],
        "wiring_rule": "match_lexicon_entries(query, query_id) → apply_typology_boost on ann_query_{id}_latest.json",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_contract.parent.mkdir(parents=True, exist_ok=True)
    args.out_contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wiring_ok": doc["summary"]["wiring_ok"], "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
