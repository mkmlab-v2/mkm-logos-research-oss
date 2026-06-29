#!/usr/bin/env python3
"""Morphology frequency report spike — WIVU/MorphHB-aligned sample stats [HYPO].

Reproducible:
  py scripts/build_logos_morphology_frequency_report_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/logos_morphology_registry_v1_latest.json"
DEFAULT_SEED = ROOT / "reports/constitution/btrack_pilot/master_atoms_morphhb_seed_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_morphology_frequency_report_v1_latest.json"

# Demo query anchors (Benei HaElohim spike — morphology layer only, NON_GATING).
QUERY_TERMS = [
    {"term_id": "eloah_H433", "strongs": "H433", "lemma_hint": "אֱלוֹהַ"},
    {"term_id": "elohim_H430", "strongs": "H430", "lemma_hint": "אֱלֹהִים"},
    {"term_id": "ben_H1121", "strongs": "H1121", "lemma_hint": "בֵּן"},
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _scan_term_hits(seed_path: Path, *, strongs: str, max_lines: int = 120000) -> dict[str, Any]:
    morph_counts: dict[str, int] = {}
    lemma_counts: dict[str, int] = {}
    matched = 0
    scanned = 0
    if not seed_path.is_file():
        return {"matched_rows": 0, "scanned_lines": 0, "lemma_counts": {}, "morph_counts": {}}
    needle = strongs.upper().replace("H", "")
    with seed_path.open(encoding="utf-8-sig") as f:
        for line in f:
            scanned += 1
            if scanned > max_lines:
                break
            s = line.strip()
            if not s:
                continue
            try:
                row = json.loads(s)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            blob = json.dumps(row, ensure_ascii=False)
            if needle not in blob and strongs not in blob:
                continue
            matched += 1
            candidates = row.get("morphhb_candidates") if isinstance(row.get("morphhb_candidates"), list) else []
            if candidates and isinstance(candidates[0], dict):
                c0 = candidates[0]
                lemma = str(c0.get("lemma") or "").strip()
                morph = str(c0.get("morph") or "").strip()
                if lemma:
                    lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1
                if morph:
                    morph_counts[morph] = morph_counts.get(morph, 0) + 1
    top_morph = sorted(morph_counts.items(), key=lambda x: (-x[1], x[0]))[:12]
    top_lemma = sorted(lemma_counts.items(), key=lambda x: (-x[1], x[0]))[:8]
    return {
        "matched_rows": matched,
        "scanned_lines": scanned,
        "top_morph_tags": [{"morph": k, "count": v} for k, v in top_morph],
        "top_lemmas": [{"lemma": k, "count": v} for k, v in top_lemma],
    }


def build_report(registry_path: Path, seed_path: Path) -> dict[str, Any]:
    reg = _read_json(registry_path)
    layer = reg.get("morphology_layer") if isinstance(reg.get("morphology_layer"), dict) else {}
    query_reports = []
    for q in QUERY_TERMS:
        hits = _scan_term_hits(seed_path, strongs=str(q["strongs"]))
        query_reports.append(
            {
                "term_id": q["term_id"],
                "strongs": q["strongs"],
                "lemma_hint": q["lemma_hint"],
                "matched_rows_in_seed_scan": hits["matched_rows"],
                "scanned_lines": hits["scanned_lines"],
                "top_morph_tags": hits["top_morph_tags"],
                "top_lemmas": hits["top_lemmas"],
                "governance": "[HYPO][NON_GATING]",
                "note_ko": "형태소 빈도 샘플 — 신학·예언·실매매 트리거 아님.",
            }
        )
    return {
        "schema": "logos_morphology_frequency_report_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "source_refs": {
            "morphology_registry": str(registry_path.relative_to(ROOT)).replace("\\", "/"),
            "morph_seed_jsonl": str(seed_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "coverage_summary": {
            "hebrew_atoms_total": layer.get("hebrew_atoms_total"),
            "matched_hebrew_atoms": layer.get("matched_hebrew_atoms"),
            "coverage_ratio_0_1": layer.get("coverage_ratio_0_1"),
            "registry_top_lemmas": layer.get("top_lemmas") or reg.get("top_lemmas"),
            "registry_top_morphs": layer.get("top_morphs") or reg.get("top_morphs"),
        },
        "query_reports": query_reports,
        "honesty": {
            "tsk_cross_ref": "NOT loaded — Tier C roadmap; this report is morphology-only.",
            "full_wlc_scan": False,
            "sample_policy": "seed_jsonl scan capped; registry aggregate from prior build.",
        },
        "reproduce": "py scripts/build_logos_morphology_frequency_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.registry.is_file():
        print(f"missing registry: {args.registry}", file=sys.stderr)
        return 1
    doc = build_report(args.registry, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
