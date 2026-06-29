"""Tier-1 corpus expansion scan (distribution only — no anchor materialize)."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from scripts.core.logos_verse_corpus_lookup_v1 import extract_greek_text, strip_greek_accents

BOOK_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_corpus_rows(path: Path) -> Iterator[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("corpus must be JSON array")
    for row in data:
        if isinstance(row, dict) and row.get("verse_id"):
            yield row


def load_motif_lexicon(registry_path: Path) -> list[dict[str, Any]]:
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    lex: list[dict[str, Any]] = []
    for e in reg.get("entries", []):
        if not e.get("enabled"):
            continue
        lemma = e.get("motif_lemma") or {}
        greek = str(lemma.get("greek") or "")
        hebrew = str(lemma.get("hebrew") or "")
        needle = strip_greek_accents((greek or hebrew).lower())
        if not needle:
            continue
        refs = [str(v) for v in (e.get("verse_refs") or [])]
        lex.append(
            {
                "slot_id": e.get("slot_id"),
                "file_stem": e.get("file_stem"),
                "needle": needle,
                "primitive_bias": e.get("primitive_bias") or e.get("category"),
                "primary_verse_ref": refs[0] if refs else None,
            }
        )
    return lex


def occupied_verse_refs(registry_path: Path) -> set[str]:
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for e in reg.get("entries", []):
        if not e.get("enabled"):
            continue
        for v in e.get("verse_refs") or []:
            out.add(str(v))
    return out


def verse_text_blob(row: dict[str, Any]) -> str:
    parts = [extract_greek_text(row), str(row.get("text_preview") or "")]
    return strip_greek_accents(" ".join(p for p in parts if p).lower())


def scan_tier1_corpus(
    *,
    corpus_path: Path,
    registry_path: Path,
) -> dict[str, Any]:
    if not corpus_path.is_file():
        raise FileNotFoundError(corpus_path)
    lexicon = load_motif_lexicon(registry_path)
    occupied = occupied_verse_refs(registry_path)

    motif_hits: Counter[str] = Counter()
    motif_verse_samples: dict[str, list[str]] = {m["file_stem"]: [] for m in lexicon}
    book_counts: Counter[str] = Counter()
    gematria_totals: list[int] = []
    verses_with_text = 0
    verses_with_motif_hit = 0
    per_verse_hit_count: list[int] = []
    candidate_scores: Counter[str] = Counter()

    needles = [(m["file_stem"], m["needle"]) for m in lexicon]

    for row in iter_corpus_rows(corpus_path):
        vid = str(row["verse_id"])
        m = BOOK_RE.match(vid)
        book_counts[m.group(1) if m else "unknown"] += 1

        blob = verse_text_blob(row)
        if blob.strip():
            verses_with_text += 1

        p2 = row.get("pipeline2_gematria_general") or {}
        tv = p2.get("total_value")
        if isinstance(tv, (int, float)):
            gematria_totals.append(int(tv))

        hit_stems: list[str] = []
        for stem, needle in needles:
            if needle and needle in blob:
                motif_hits[stem] += 1
                hit_stems.append(stem)
                samples = motif_verse_samples[stem]
                if len(samples) < 5:
                    samples.append(vid)
        if hit_stems:
            verses_with_motif_hit += 1
            if vid not in occupied:
                candidate_scores[vid] = len(hit_stems)
        per_verse_hit_count.append(len(hit_stems))

    total_motif_hit_events = sum(motif_hits.values())
    top_stem, top_count = motif_hits.most_common(1)[0] if motif_hits else ("", 0)
    top_share = round(top_count / total_motif_hit_events, 4) if total_motif_hit_events else 0.0

    motif_ranking = [
        {
            "file_stem": stem,
            "hit_count": count,
            "share_of_motif_hits": round(count / total_motif_hit_events, 6) if total_motif_hit_events else 0.0,
            "sample_verse_ids": motif_verse_samples.get(stem, []),
        }
        for stem, count in motif_hits.most_common()
    ]

    expansion_candidates = [
        {"verse_id": vid, "motif_hit_count": score}
        for vid, score in candidate_scores.most_common(500)
    ]

    gt_sorted = sorted(gematria_totals)
    gem_summary: dict[str, Any] = {}
    if gt_sorted:
        mid = len(gt_sorted) // 2
        gem_summary = {
            "count": len(gt_sorted),
            "min": gt_sorted[0],
            "max": gt_sorted[-1],
            "median": gt_sorted[mid],
        }

    return {
        "tier": "tier1_canon",
        "corpus_path": corpus_path.as_posix(),
        "corpus_sha256": sha256_file(corpus_path),
        "verse_count": sum(book_counts.values()),
        "verses_with_text": verses_with_text,
        "verses_with_motif_hit": verses_with_motif_hit,
        "motif_lexicon_size": len(lexicon),
        "registry_occupied_verse_refs": len(occupied),
        "motif_hit_event_total": total_motif_hit_events,
        "skew_warning": {
            "top_motif_stem": top_stem,
            "top_motif_share_of_hits": top_share,
            "bulk_materialize_risk": top_share > 0.25,
            "note_ko": "31k 일괄 anchor materialize 시 harmony 쏠림 위험 — wave+spread-aware 필수",
        },
        "book_distribution_top20": [
            {"book": b, "verse_count": c} for b, c in book_counts.most_common(20)
        ],
        "gematria_total_summary": gem_summary,
        "motif_hit_ranking": motif_ranking[:50],
        "expansion_candidate_preview": expansion_candidates[:200],
        "threshold_gate_recommendation": {
            "harmony_top1_share_max": 0.65,
            "spread_aware_ranking": True,
            "wave_size": 100,
            "human_gate_required": True,
            "production_batch_merge_forbidden_until_gate": True,
        },
    }
