#!/usr/bin/env python3
"""Build sasang routing sidecar JSONL overlay for full Logos corpus (31k; B-track only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_sasang_routing_sidecar_on_gematria_path_v1 import (
    PRIMITIVE_KERNEL,
    SASANG_LENS,
    _load,
    build as build_sidecar,
)
from scripts.core.gematria_engine import build_gematria_metadata

DEFAULT_CORPUS = ROOT / "data/logos/verse_4pipeline_full_31102.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/logos_verse_4pipeline_minimal_manifest_v1.json"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_manifest_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/sasang_routing_sidecar_corpus_31k_posture_v1_latest.json"
EXPECTED_VERSE_COUNT = 31102
RECIPE_ID = "gematria_to_4d_bridge"
ROW_SCHEMA = "sasang_routing_sidecar_corpus_row_v1"

MUST_NOT_MERGE = [
    "prophecy_vote",
    "track_a_compression_floor",
    "production_gematria_kernel",
    "arm_a_quant_ssot",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_corpus(path: Path) -> Iterator[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, list):
        raise ValueError(f"corpus must be JSON array: {path}")
    for row in doc:
        if isinstance(row, dict):
            yield row


def _book_bucket(verse_id: str) -> str:
    return verse_id.split(".", 1)[0] if verse_id else "unknown"


def _chapter_bucket(verse_id: str) -> int | None:
    parts = verse_id.split(".")
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def _gematria_metadata_from_verse(verse: dict[str, Any]) -> dict[str, int]:
    text = str(verse.get("text_preview") or "").strip()
    if text:
        return build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
    p2 = verse.get("pipeline2_gematria_general") or {}
    if p2.get("total_value") is not None:
        total = int(p2.get("total_value") or 0)
        heb = int(p2.get("hebrew_value") or 0)
        grk = int(p2.get("greek_value") or 0)
        return {
            "raw_combined_sum": total,
            "compressed_combined_sum": heb + grk,
            "reconstructed_combined_sum": total,
        }
    vid = str(verse.get("verse_id") or "unknown")
    seed = sum(ord(c) for c in vid) % 100000
    return {
        "raw_combined_sum": seed,
        "compressed_combined_sum": seed,
        "reconstructed_combined_sum": seed,
    }


def _compact_row(*, verse: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    verse_id = str(verse.get("verse_id") or "")
    hints = sidecar.get("sasang_routing_hints") or {}
    return {
        "schema": ROW_SCHEMA,
        "verse_id": verse_id,
        "book_bucket": _book_bucket(verse_id),
        "chapter": _chapter_bucket(verse_id),
        "path_id": sidecar.get("path_id"),
        "gematria_path_ref": sidecar.get("gematria_path_ref"),
        "sasang_routing_hints": {
            "posture_hint": hints.get("posture_hint"),
            "entropy_leg": hints.get("entropy_leg"),
            "pathology_state": hints.get("pathology_state"),
            "direction_score": hints.get("direction_score"),
            "confidence": hints.get("confidence"),
        },
    }


def build_corpus_overlay(
    *,
    corpus_path: Path,
    limit: int | None = None,
    recipe_id: str = RECIPE_ID,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lens_doc = _load(SASANG_LENS)
    kernel_doc = _load(PRIMITIVE_KERNEL)

    rows: list[dict[str, Any]] = []
    pathology_hist: Counter[str] = Counter()
    posture_hist: Counter[str] = Counter()
    entropy_hist: Counter[str] = Counter()
    book_hist: Counter[str] = Counter()

    for i, verse in enumerate(_iter_corpus(corpus_path)):
        if limit is not None and i >= limit:
            break
        verse_id = str(verse.get("verse_id") or f"row_{i}")
        meta = _gematria_metadata_from_verse(verse)
        sidecar = build_sidecar(
            anchor_ref=verse_id,
            gematria_metadata={k: int(v) for k, v in meta.items()},
            recipe_id=recipe_id,
            lens_doc=lens_doc,
            kernel_doc=kernel_doc,
        )
        row = _compact_row(verse=verse, sidecar=sidecar)
        rows.append(row)

        hints = row["sasang_routing_hints"]
        pathology_hist[str(hints.get("pathology_state") or "unknown")] += 1
        posture_hist[str(hints.get("posture_hint") or "unknown")] += 1
        entropy_hist[str(hints.get("entropy_leg") or "unknown")] += 1
        book_hist[row["book_bucket"]] += 1

    posture_histogram = {
        "pathology_state": dict(sorted(pathology_hist.items())),
        "posture_hint": dict(sorted(posture_hist.items())),
        "entropy_leg": dict(sorted(entropy_hist.items())),
        "by_book_bucket": dict(sorted(book_hist.items())),
    }

    generated_at = _utc()
    manifest = {
        "schema": "sasang_routing_sidecar_corpus_31k_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "track_a_promotion": False,
        "forbidden_synthesis_ack": True,
        "must_not_merge_into": list(MUST_NOT_MERGE),
        "corpus_input": str(corpus_path.relative_to(ROOT)).replace("\\", "/"),
        "recipe_id": recipe_id,
        "row_schema": ROW_SCHEMA,
        "verse_count": len(rows),
        "expected_verse_count": EXPECTED_VERSE_COUNT,
        "posture_histogram": posture_histogram,
        "upstream": {
            "sidecar_builder": "scripts/build_sasang_routing_sidecar_on_gematria_path_v1.py",
            "disclaimer_ko": (
                "31k 절 좌표망 routing hints overlay — not Track A · not prophecy vote · not SEND"
            ),
        },
        "reproduce": (
            "py scripts/build_sasang_routing_sidecar_corpus_31k_v1.py "
            "&& py scripts/check_sasang_routing_sidecar_corpus_31k_v1.py"
        ),
    }
    return rows, manifest


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=None, help="default: full 31k if present else fixture")
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--limit", type=int, default=None, help="smoke: first N verses only")
    args = ap.parse_args()

    corpus = args.corpus
    if corpus is None:
        corpus = DEFAULT_CORPUS if DEFAULT_CORPUS.is_file() else DEFAULT_FIXTURE
    if not corpus.is_file():
        print(json.dumps({"ok": False, "error": f"missing corpus: {corpus}"}))
        return 1

    rows, manifest = build_corpus_overlay(corpus_path=corpus, limit=args.limit)
    _write_jsonl(rows, args.jsonl)
    manifest["jsonl_path"] = _rel_or_abs(args.jsonl)
    manifest["jsonl_bytes"] = args.jsonl.stat().st_size
    manifest["jsonl_sha256"] = _sha256_file(args.jsonl)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "sasang_routing_sidecar_corpus_31k_posture_v1",
        "version": "1.0.0",
        "generated_at_utc": manifest["generated_at_utc"],
        "verse_count": manifest["verse_count"],
        "posture_histogram": manifest["posture_histogram"],
        "manifest": _rel_or_abs(args.manifest),
        "jsonl": manifest["jsonl_path"],
        "send_gate": "HOLD",
        "research_only": True,
        "track_a_blocked": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "verse_count": manifest["verse_count"],
                "jsonl": str(args.jsonl),
                "manifest": str(args.manifest),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
