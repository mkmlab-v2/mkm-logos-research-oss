#!/usr/bin/env python3
"""Attach empirical 4D vectors to symbol candidates from Logos corpora."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_SYMBOLS = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_latest.jsonl"
IN_VERSES_A = ROOT / "data" / "logos" / "verse_distilled_11_1.jsonl"
IN_VERSES_B = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
IN_ANCHOR = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_anchor_matrix_latest.json"
OUT_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_with_vectors_latest.jsonl"
OUT_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_vectors_from_verse_distilled_summary_latest.json"

TOK_RE = re.compile(r"[A-Za-z]+|[0-9]+|[\u0370-\u03FF]+|[\u0590-\u05FF]+")


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOK_RE.finditer(text or "")]


def _vector_ok(v: Any) -> bool:
    return isinstance(v, dict) and all(isinstance(v.get(k), (int, float)) for k in ("S", "L", "K", "M"))


def _mean_vector(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    n = float(len(rows))
    return {
        "S": sum(r["S"] for r in rows) / n,
        "L": sum(r["L"] for r in rows) / n,
        "K": sum(r["K"] for r in rows) / n,
        "M": sum(r["M"] for r in rows) / n,
    }


def _token_pool_from_verse_jsonl(path: Path) -> tuple[dict[str, list[dict[str, float]]], dict[str, dict[str, float]], int]:
    token_vecs: dict[str, list[dict[str, float]]] = {}
    verse_vecs: dict[str, dict[str, float]] = {}
    used = 0
    for row in _iter_jsonl(path):
        vec = row.get("vector_4d") or row.get("unified_4d_vector")
        if not _vector_ok(vec):
            continue
        v = {k: float(vec[k]) for k in ("S", "L", "K", "M")}
        verse_id = str(row.get("verse_id", "")).strip()
        if verse_id:
            verse_vecs[verse_id] = v
        text = " ".join(
            [
                str(row.get("text", "") or ""),
                str(row.get("original_text", "") or ""),
            ]
        ).strip()
        if not text:
            continue
        toks = set(_tokenize(text))
        if not toks:
            continue
        used += 1
        for tok in toks:
            token_vecs.setdefault(tok, []).append(v)
    return token_vecs, verse_vecs, used


def _add_anchor_projection_token_pool(
    *,
    anchor_path: Path,
    verse_vecs: dict[str, dict[str, float]],
    token_vecs: dict[str, list[dict[str, float]]],
) -> int:
    if not anchor_path.is_file():
        return 0
    payload = json.loads(anchor_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return 0
    projected = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("canonical_ref", "")).strip()
        vec = verse_vecs.get(ref)
        if vec is None:
            continue
        text = " ".join(
            [
                str(row.get("entry_id", "") or ""),
                str(row.get("canonical_ref", "") or ""),
                str(row.get("satellite_ref", "") or ""),
                str(row.get("corpus_type", "") or ""),
            ]
        ).strip()
        toks = set(_tokenize(text))
        if not toks:
            continue
        for tok in toks:
            token_vecs.setdefault(tok, []).append(vec)
        projected += 1
    return projected


def _vector_from_phrase(symbol: str, token_vecs: dict[str, list[dict[str, float]]]) -> tuple[dict[str, float] | None, int]:
    parts = [p for p in _tokenize(symbol) if p]
    if not parts:
        return None, 0
    part_vecs: list[dict[str, float]] = []
    support = 0
    for p in parts:
        vec_rows = token_vecs.get(p)
        if not vec_rows:
            continue
        part_vecs.append(_mean_vector(vec_rows))
        support += len(vec_rows)
    if not part_vecs:
        return None, 0
    return _mean_vector(part_vecs), support


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbol->4D mapping from Logos corpora")
    ap.add_argument("--symbols", default=str(IN_SYMBOLS))
    ap.add_argument("--verses-a", default=str(IN_VERSES_A))
    ap.add_argument("--verses-b", default=str(IN_VERSES_B))
    ap.add_argument("--anchor", default=str(IN_ANCHOR))
    ap.add_argument("--out-jsonl", default=str(OUT_JSONL))
    ap.add_argument("--out-summary", default=str(OUT_SUMMARY))
    args = ap.parse_args()

    symbols_path = _abs(args.symbols)
    verses_a_path = _abs(args.verses_a)
    verses_b_path = _abs(args.verses_b)
    anchor_path = _abs(args.anchor)
    out_jsonl = _abs(args.out_jsonl)
    out_summary = _abs(args.out_summary)
    for p in (symbols_path, verses_a_path, verses_b_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    token_vecs_a, verse_vecs_a, used_a = _token_pool_from_verse_jsonl(verses_a_path)
    token_vecs_b, verse_vecs_b, used_b = _token_pool_from_verse_jsonl(verses_b_path)
    token_vecs: dict[str, list[dict[str, float]]] = {}
    for k, rows in token_vecs_a.items():
        token_vecs.setdefault(k, []).extend(rows)
    for k, rows in token_vecs_b.items():
        token_vecs.setdefault(k, []).extend(rows)
    verse_vecs = dict(verse_vecs_a)
    verse_vecs.update(verse_vecs_b)

    anchor_projected_rows = _add_anchor_projection_token_pool(
        anchor_path=anchor_path,
        verse_vecs=verse_vecs,
        token_vecs=token_vecs,
    )

    written = 0
    matched = 0
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in _iter_jsonl(symbols_path):
            symbol = str(row.get("symbol", "")).strip().lower()
            out = dict(row)
            out["vector_source"] = "none"
            if symbol in token_vecs:
                out["vector_4d"] = _mean_vector(token_vecs[symbol])
                out["vector_source"] = "logos_token_mean_v2"
                out["vector_support_count"] = len(token_vecs[symbol])
                matched += 1
            else:
                phrase_vec, support = _vector_from_phrase(symbol, token_vecs)
                if phrase_vec is not None:
                    out["vector_4d"] = phrase_vec
                    out["vector_source"] = "logos_phrase_mean_v2"
                    out["vector_support_count"] = support
                    matched += 1
            out["vectorized_at_utc"] = ts
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            written += 1

    summary = {
        "schema": "symbol_vectors_from_verse_distilled_summary_v1",
        "generated_at_utc": ts,
        "inputs": {
            "symbols_jsonl": str(symbols_path),
            "verses_a_jsonl": str(verses_a_path),
            "verses_b_jsonl": str(verses_b_path),
            "anchor_matrix_json": str(anchor_path),
        },
        "stats": {
            "verse_rows_used_a": used_a,
            "verse_rows_used_b": used_b,
            "anchor_rows_projected": anchor_projected_rows,
            "token_vocab_size": len(token_vecs),
            "symbol_rows_written": written,
            "symbol_rows_with_vector_4d": matched,
            "vector_coverage_rate": (matched / written) if written else 0.0,
        },
        "outputs": {
            "symbols_with_vectors_jsonl": str(out_jsonl),
        },
    }
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol vectors attached")
    print(f"out={out_jsonl}")
    print(f"summary={out_summary}")
    print(f"coverage={matched}/{written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
