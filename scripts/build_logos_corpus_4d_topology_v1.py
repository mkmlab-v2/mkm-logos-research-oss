#!/usr/bin/env python3
"""[HYPO] Precompute gematria 4D topology for full Logos canon corpus (NON_GATING).

Internal closed-corpus geometry only — no external headline mapping, Track A, or live trading.
Outputs summary JSON + per-verse JSONL shard for Hub / Topology Radar ingest.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logos_chronology_gematria_core_v1 import (  # noqa: E402
    build_era_profiles,
    gematria_bundle,
    l2_distance,
    load_json,
    load_verse_index,
    mean_vec,
    rel_repo,
    utc_now,
    vec4_from_text,
)
from logos_chronology_map_core_v1 import POLICY  # noqa: E402
from tools.core.logos_corpus_loader import default_hebrew_greek_jsonl, iter_hebrew_greek_jsonl  # noqa: E402

DEFAULT_CORPUS = default_hebrew_greek_jsonl(ROOT)
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_corpus_4d_topology_v1_latest.json"
DEFAULT_VERSES_JSONL = ROOT / "reports/logos_corpus_4d_topology_verses_v1_latest.jsonl"
DEFAULT_HUB_PUBLIC = ROOT / "projects/no1kmedi/public/data/logos_corpus_4d_topology_hub_v1.json"
AXES = ("S", "L", "K", "M")


def _book_id_from_verse(verse_id: str) -> str:
    vid = str(verse_id or "").strip()
    if not vid:
        return "unknown"
    if "::" in vid:
        vid = vid.split("::", 1)[1]
    return vid.split(".", 1)[0] if "." in vid else vid


def _phase_angle_sl(vec: dict[str, float], centroid: dict[str, float]) -> float:
    ds = float(vec["S"]) - float(centroid["S"])
    dl = float(vec["L"]) - float(centroid["L"])
    return round(math.atan2(dl, ds), 6)


def _hub_score(l2: float) -> float:
    return round(1.0 / (1.0 + float(l2)), 6)


def _scan_corpus(
    corpus: Path,
    *,
    limit: int | None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, float]]]]:
    rows: list[dict[str, Any]] = []
    by_book: dict[str, list[dict[str, float]]] = {}
    for rec in iter_hebrew_greek_jsonl(corpus, limit=limit):
        vid = str(rec.get("verse_id") or "").strip()
        if not vid:
            continue
        he = str(rec.get("text_hebrew") or "").strip()
        gr = str(rec.get("text_greek") or "").strip()
        logos = " ".join(x for x in (he, gr) if x).strip()
        if not logos:
            continue
        bundle = gematria_bundle(logos)
        vec = bundle["vector_4d"]
        book = _book_id_from_verse(vid)
        by_book.setdefault(book, []).append(vec)
        rows.append(
            {
                "verse_id": vid,
                "book_id": book,
                "vector_4d": vec,
                "combined_sum": int(bundle.get("combined_sum") or 0),
                "state16": bundle.get("state16"),
            }
        )
    return rows, by_book


def _write_verse_shard(
    fh: TextIO,
    *,
    rows: list[dict[str, Any]],
    global_centroid: dict[str, float],
) -> None:
    for row in rows:
        vec = row["vector_4d"]
        l2 = round(l2_distance(vec, global_centroid), 6)
        out = {
            "verse_id": row["verse_id"],
            "book_id": row["book_id"],
            "vector_4d": vec,
            "l2_to_global_centroid": l2,
            "phase_angle_sl_rad": _phase_angle_sl(vec, global_centroid),
            "hub_score_inverse_l2": _hub_score(l2),
            "combined_sum": row.get("combined_sum"),
            "state16": row.get("state16"),
        }
        fh.write(json.dumps(out, ensure_ascii=False) + "\n")


def _top_hubs(rows: list[dict[str, Any]], global_centroid: dict[str, float], top_n: int) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in rows:
        vec = row["vector_4d"]
        l2 = round(l2_distance(vec, global_centroid), 6)
        scored.append(
            {
                "verse_id": row["verse_id"],
                "book_id": row["book_id"],
                "hub_score_inverse_l2": _hub_score(l2),
                "l2_to_global_centroid": l2,
                "phase_angle_sl_rad": _phase_angle_sl(vec, global_centroid),
                "vector_4d": vec,
                "interpretation_class": "[HYPO]",
            }
        )
    scored.sort(key=lambda r: (-float(r["hub_score_inverse_l2"]), str(r["verse_id"])))
    return scored[:top_n]


def _era_trajectories(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev: dict[str, float] | None = None
    for p in profiles:
        c = p["centroid_4d"]
        step_l2 = round(l2_distance(c, prev), 6) if prev else 0.0
        out.append(
            {
                "era_id": p["era_id"],
                "label_ko": p["label_ko"],
                "centroid_4d": c,
                "phase_shift_l2_from_previous": step_l2,
                "n_verse_refs": p.get("n_verse_refs"),
                "interpretation_class": "[HYPO]",
            }
        )
        prev = c
    return out


def _book_summaries(by_book: dict[str, list[dict[str, float]]], top_books: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for book_id, vecs in by_book.items():
        centroid = mean_vec(vecs)
        items.append(
            {
                "book_id": book_id,
                "n_verses": len(vecs),
                "centroid_4d": centroid,
            }
        )
    items.sort(key=lambda x: (-int(x["n_verses"]), str(x["book_id"])))
    return items[:top_books]


def _hub_public_doc(summary: dict[str, Any], *, hub_top_n: int) -> dict[str, Any]:
    hubs = list(summary.get("global_centrality_hubs") or [])[:hub_top_n]
    return {
        "schema": "logos_corpus_4d_topology_hub_v1",
        "generated_at_utc": summary.get("generated_at_utc"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": summary.get("policy"),
        "source_summary_json": summary.get("inputs", {}).get("summary_json"),
        "n_verses": summary.get("n_verses"),
        "global_centroid_4d": summary.get("global_centroid_4d"),
        "global_centrality_hubs": hubs,
        "era_centroid_trajectories": summary.get("era_centroid_trajectories"),
        "book_centroid_top": (summary.get("book_centroid_summaries") or [])[:12],
        "reproduce_command": summary.get("reproduce_command"),
        "disclaimer_ko": (
            "내부 코퍼스 기하학 관측 [HYPO]·research_only. 예언·실매매·Track A 근거 아님. "
            "게마트리아 4D bridge는 mod-101 PoC이며 신학적 중심축 단정이 아닙니다."
        ),
    }


def build_topology(
    *,
    corpus: Path,
    chrono_path: Path,
    top_hubs: int,
    top_books: int,
    limit: int | None,
) -> dict[str, Any]:
    if not corpus.is_file():
        raise FileNotFoundError(corpus)
    if not chrono_path.is_file():
        raise FileNotFoundError(chrono_path)

    rows, by_book = _scan_corpus(corpus, limit=limit)
    if not rows:
        raise RuntimeError("empty corpus scan")

    vectors = [r["vector_4d"] for r in rows]
    global_centroid = mean_vec(vectors)

    verse_index = load_verse_index(corpus)
    chrono = load_json(chrono_path)
    era_profiles = build_era_profiles(chrono, verse_index)
    era_trajectories = _era_trajectories(era_profiles)

    return {
        "schema": "logos_corpus_4d_topology_v1",
        "generated_at_utc": utc_now(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "hypothesis_lane": "B",
        "policy": POLICY,
        "method_ko": (
            "31k절 히브리/그리스 원어 → gematria_engine + gematria_to_4d_bridge → "
            "전역 무게중심 대비 L2·SL평면 위상각 → hub Top-N · 11-era centroid phase shift"
        ),
        "inputs": {
            "corpus_jsonl": rel_repo(ROOT, corpus),
            "chronology_json": rel_repo(ROOT, chrono_path),
            "corpus_limit": limit,
            "centrality_metric": "inverse_l2_to_global_centroid",
            "verses_shard_jsonl": rel_repo(ROOT, DEFAULT_VERSES_JSONL),
        },
        "n_verses": len(rows),
        "global_centroid_4d": global_centroid,
        "global_centrality_hubs": _top_hubs(rows, global_centroid, top_hubs),
        "era_centroid_trajectories": era_trajectories,
        "book_centroid_summaries": _book_summaries(by_book, top_books),
        "known_limitations": [
            "Closed-corpus internal geometry only; no external history injection.",
            "Gematria 4D bridge is deterministic mod-101 PoC — not traditional gematria exegesis.",
            "Hub labels are structural candidates [HYPO], not theological center claims.",
            "Does not promote Track A, prophecy gates, or live trading.",
        ],
        "reproduce_command": (
            "py scripts/build_logos_corpus_4d_topology_v1.py "
            "--corpus-jsonl data/logos/bible_original_hebrew_greek.jsonl"
        ),
        "_verse_rows": rows,
        "_global_centroid": global_centroid,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--verses-jsonl", type=Path, default=DEFAULT_VERSES_JSONL)
    ap.add_argument("--hub-public-json", type=Path, default=DEFAULT_HUB_PUBLIC)
    ap.add_argument("--top-hubs", type=int, default=50)
    ap.add_argument("--hub-public-top-hubs", type=int, default=20)
    ap.add_argument("--top-books", type=int, default=40)
    ap.add_argument("--corpus-limit", type=int, default=None, help="Dev/test cap on verses")
    ap.add_argument("--skip-hub-public", action="store_true")
    args = ap.parse_args()

    corpus = args.corpus_jsonl if args.corpus_jsonl.is_absolute() else ROOT / args.corpus_jsonl
    chrono = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    verses_out = args.verses_jsonl if args.verses_jsonl.is_absolute() else ROOT / args.verses_jsonl
    hub_out = args.hub_public_json if args.hub_public_json.is_absolute() else ROOT / args.hub_public_json

    try:
        built = build_topology(
            corpus=corpus,
            chrono_path=chrono,
            top_hubs=max(1, int(args.top_hubs)),
            top_books=max(1, int(args.top_books)),
            limit=args.corpus_limit,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    rows = built.pop("_verse_rows")
    global_centroid = built.pop("_global_centroid")
    built["inputs"]["summary_json"] = rel_repo(ROOT, out)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(built, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    verses_out.parent.mkdir(parents=True, exist_ok=True)
    with verses_out.open("w", encoding="utf-8") as fh:
        _write_verse_shard(fh, rows=rows, global_centroid=global_centroid)

    if not args.skip_hub_public:
        hub_doc = _hub_public_doc(built, hub_top_n=max(1, int(args.hub_public_top_hubs)))
        hub_out.parent.mkdir(parents=True, exist_ok=True)
        hub_out.write_text(json.dumps(hub_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output": rel_repo(ROOT, out),
                "verses_jsonl": rel_repo(ROOT, verses_out),
                "hub_public": rel_repo(ROOT, hub_out) if not args.skip_hub_public else None,
                "n_verses": built["n_verses"],
                "top_hub_verse": (built["global_centrality_hubs"][0]["verse_id"] if built["global_centrality_hubs"] else None),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
