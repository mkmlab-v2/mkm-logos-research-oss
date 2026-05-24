#!/usr/bin/env python3
"""[HYPO] Build master_codebook_lexicon_v1 slice from 수세보원 canonical / chunk lane (B-track)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_CANON = ROOT / "docs/sasang-origin/정교동의수세보원원문.txt"
DEFAULT_OUT = PILOT / "ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
META_OUT = PILOT / "comp_ijeoma_hanja_codebook_export_hypo_v1.json"

_CJK_RUN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom_id(form: str) -> str:
    h = hashlib.sha256(form.encode("utf-8")).hexdigest()[:12]
    return f"ijeoma_hanja_{h}"


def extract_phrases(text: str, *, min_len: int = 2, max_len: int = 4) -> set[str]:
    out: set[str] = set()
    for run in _CJK_RUN.findall(text):
        if len(run) < min_len:
            continue
        cap = min(max_len, len(run))
        for length in range(min_len, cap + 1):
            for i in range(len(run) - length + 1):
                out.add(run[i : i + length])
    return out


def _read_canonical(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_chunk_lane(path: Path) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    parts = [str(c.get("raw_text") or "") for c in doc.get("compression_cases") or []]
    return "\n".join(parts)


def main() -> int:
    from scripts.core.master_codebook_lexicon_v1_bridge import clear_codebook_cache

    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=("canonical", "chunk_lane", "both"), default="both")
    ap.add_argument("--canonical", type=Path, default=DEFAULT_CANON)
    ap.add_argument(
        "--chunk-lane",
        type=Path,
        default=ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json",
    )
    ap.add_argument("--min-phrase-len", type=int, default=2)
    ap.add_argument("--max-phrase-len", type=int, default=4)
    ap.add_argument("--max-entries", type=int, default=12000)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    blobs: list[str] = []
    sources: list[str] = []
    if args.source in ("canonical", "both"):
        canon = (ROOT / args.canonical).resolve() if not args.canonical.is_absolute() else args.canonical
        if canon.is_file():
            blobs.append(_read_canonical(canon))
            sources.append(str(canon.relative_to(ROOT)).replace("\\", "/"))
    if args.source in ("chunk_lane", "both"):
        lane = (ROOT / args.chunk_lane).resolve() if not args.chunk_lane.is_absolute() else args.chunk_lane
        if lane.is_file():
            blobs.append(_read_chunk_lane(lane))
            sources.append(str(lane.relative_to(ROOT)).replace("\\", "/"))

    if not blobs:
        print(json.dumps({"error": "no_sources"}, ensure_ascii=False))
        return 2

    phrases: set[str] = set()
    for blob in blobs:
        phrases |= extract_phrases(
            blob,
            min_len=max(1, args.min_phrase_len),
            max_len=max(2, args.max_phrase_len),
        )

    short = sorted(p for p in phrases if 2 <= len(p) <= 3)
    long = sorted(p for p in phrases if len(p) >= 4)
    sorted_phrases = short + long
    if args.max_entries > 0 and len(sorted_phrases) > args.max_entries:
        sorted_phrases = sorted_phrases[: args.max_entries]

    entries: list[dict] = []
    for form in sorted_phrases:
        entries.append(
            {
                "atom_id": _atom_id(form),
                "lang": "zh-Hani",
                "normalized_form": form,
                "occurrences": 1,
                "lexicon_strongs_candidates": [],
                "lexicon_match_method": "ijeoma_canon_phrase_mining_hypo_v1",
                "morphhb_match_method": "",
                "morphhb_strongs_hints": [],
                "morphhb_chosen": None,
                "morphhb_disambiguation": None,
                "research_only": True,
                "hypothesis_tier": "B",
            }
        )

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    payload = {
        "schema": "master_codebook_lexicon_v1",
        "generated_at_utc": _utc(),
        "row_count": len(entries),
        "bench_label": "ijeoma_hanja_hypo_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "sources": sources,
        "phrase_mining": {
            "min_len": args.min_phrase_len,
            "max_len": args.max_phrase_len,
            "unique_phrases_before_cap": len(phrases),
        },
        "rail_coverage_note": (
            "HYPO slice mined from 수세보원 CJK runs; not merged into global 41775-row export. "
            "Use via master_codebook_lexicon_path on chunk-lane eval only."
        ),
        "entries": entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clear_codebook_cache()

    meta = {
        "schema": "comp_ijeoma_hanja_codebook_export_hypo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "entry_count": len(entries),
        "sources": sources,
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
