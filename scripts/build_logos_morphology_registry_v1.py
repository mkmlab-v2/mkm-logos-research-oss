#!/usr/bin/env python3
"""Build NON_GATING morphology registry for Logos response layer."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_SUMMARY = PILOT / "master_atoms_morphhb_seed_summary_latest.json"
DEFAULT_SEED = PILOT / "master_atoms_morphhb_seed_latest.jsonl"
DEFAULT_INDEX = PILOT / "morphhb_norm_to_lemma_index_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_morphology_registry_v1_latest.json"
DEFAULT_MAX_SCAN_LINES = 400000
DEFAULT_TARGET_MATCHED_SAMPLES = 5000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _scan_seed_stats(
    path: Path,
    *,
    max_scan_lines: int = DEFAULT_MAX_SCAN_LINES,
    target_matched_samples: int = DEFAULT_TARGET_MATCHED_SAMPLES,
) -> dict[str, Any]:
    lemma_counts: dict[str, int] = {}
    morph_counts: dict[str, int] = {}
    matched_rows = 0
    scanned = 0
    if not path.is_file():
        return {"matched_rows": 0, "scanned_lines": 0, "lemma_counts": lemma_counts, "morph_counts": morph_counts}
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            scanned += 1
            if scanned > max_scan_lines:
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
            if str(row.get("lang") or "") != "hebrew":
                continue
            method = str(row.get("match_method") or "")
            if method not in {"morphhb_wlc", "morphhb_wlc_no_strong", "morphhb_wlc_multi"} and not method.startswith("matched"):
                continue
            matched_rows += 1
            candidates = row.get("morphhb_candidates") if isinstance(row.get("morphhb_candidates"), list) else []
            if candidates:
                cand0 = candidates[0] if isinstance(candidates[0], dict) else {}
                lemma = str(cand0.get("lemma") or "").strip()
                morph = str(cand0.get("morph") or "").strip()
                if lemma:
                    lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1
                if morph:
                    morph_counts[morph] = morph_counts.get(morph, 0) + 1
            if matched_rows >= target_matched_samples:
                break
    return {
        "matched_rows": matched_rows,
        "scanned_lines": scanned,
        "lemma_counts": lemma_counts,
        "morph_counts": morph_counts,
    }


def build_registry(summary: dict[str, Any], seed_stats: dict[str, Any], idx_meta: dict[str, Any]) -> dict[str, Any]:
    hebrew_atoms = int(summary.get("hebrew_atoms") or 0)
    matched = int(summary.get("matched_hebrew") or 0)
    unmatched = int(summary.get("unmatched_hebrew") or 0)
    frac = float(((summary.get("coverage") or {}).get("hebrew") or {}).get("fraction_of_hebrew_atoms") or 0.0)
    multi = int(((summary.get("multi_resolution") or {}).get("rows_resolved_from_wlc_multi")) or 0)
    unique_norm = int(((idx_meta.get("stats") or {}).get("unique_norm_keys")) or 0)

    lemma_counts = seed_stats.get("lemma_counts") if isinstance(seed_stats.get("lemma_counts"), dict) else {}
    morph_counts = seed_stats.get("morph_counts") if isinstance(seed_stats.get("morph_counts"), dict) else {}
    matched_rows = int(seed_stats.get("matched_rows") or 0)
    scanned_lines = int(seed_stats.get("scanned_lines") or 0)

    top_lemmas = sorted(lemma_counts.items(), key=lambda x: (-x[1], x[0]))[:8]
    top_morphs = sorted(morph_counts.items(), key=lambda x: (-x[1], x[0]))[:8]

    return {
        "schema": "logos_morphology_registry_v1",
        "generated_at_utc": _now(),
        "source_refs": {
            "morph_summary_json": "reports/constitution/btrack_pilot/master_atoms_morphhb_seed_summary_latest.json",
            "morph_seed_jsonl": "reports/constitution/btrack_pilot/master_atoms_morphhb_seed_latest.jsonl",
            "morph_index_json": "reports/constitution/btrack_pilot/morphhb_norm_to_lemma_index_latest.json",
        },
        "morphology_layer": {
            "registry_id": "morphhb_hebrew_core_v1",
            "scope": "hebrew_morphology_only",
            "hebrew_atoms_total": hebrew_atoms,
            "matched_hebrew_atoms": matched,
            "unmatched_hebrew_atoms": unmatched,
            "coverage_ratio_0_1": round(frac, 6),
            "resolved_multi_rows": multi,
            "index_unique_norm_keys": unique_norm,
            "sampled_matched_rows": matched_rows,
            "sampled_scanned_lines": scanned_lines,
            "sampling_policy": {
                "max_scan_lines": DEFAULT_MAX_SCAN_LINES,
                "target_matched_samples": DEFAULT_TARGET_MATCHED_SAMPLES,
                "stop_condition": "matched_rows>=target or scanned_lines>=max",
            },
            "top_lemmas": [{"lemma": k, "count": v} for k, v in top_lemmas],
            "top_morph_tags": [{"morph_tag": k, "count": v} for k, v in top_morphs],
            "interpretation_guard": "원어 형태소 레이어는 의미 해설 보조이며 가격/실행 트리거가 아니다.",
            "non_gating_only": True,
            "price_mapping_forbidden": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--seed-jsonl", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    summary_path = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    seed_path = args.seed_jsonl if args.seed_jsonl.is_absolute() else ROOT / args.seed_jsonl
    index_path = args.index_json if args.index_json.is_absolute() else ROOT / args.index_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not summary_path.is_file():
        raise SystemExit(f"Missing --summary-json: {summary_path}")
    summary = _read_json(summary_path)
    seed_stats = _scan_seed_stats(
        seed_path,
        max_scan_lines=DEFAULT_MAX_SCAN_LINES,
        target_matched_samples=DEFAULT_TARGET_MATCHED_SAMPLES,
    )
    idx_meta = _read_json(index_path) if index_path.is_file() else {}
    payload = build_registry(summary, seed_stats, idx_meta)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "registry_id": payload["morphology_layer"]["registry_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

