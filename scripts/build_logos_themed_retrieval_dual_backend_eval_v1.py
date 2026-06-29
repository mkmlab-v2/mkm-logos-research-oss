#!/usr/bin/env python3
"""Compare hash_stub vs sentence_transformers themed retrieval recall@k."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_themed_retrieval_eval_v1 import THEMES, _anchor_ids, eval_theme

PY = sys.executable
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = ROOT / "reports/logos_themed_retrieval_dual_backend_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recall_from_hits(anchors: set[str], hits: list[str]) -> dict[str, Any]:
    overlap = sorted(anchors & set(hits))
    recall = (len(overlap) / len(anchors)) if anchors else 0.0
    return {
        "retrieved": hits,
        "overlap_verse_ids": overlap,
        "anchor_recall_at_k": round(recall, 4),
    }


def _query_sqlite(theme_id: str, sqlite: Path, query: str, top_k: int, st_model: str | None) -> list[str]:
    out = Path(tempfile.gettempdir()) / f"logos_themed_query_{theme_id}_{sqlite.stem}.json"
    cmd = [
        PY,
        "scripts/query_logos_vector_index_ann_lite_v1.py",
        "--sqlite",
        str(sqlite),
        "--query",
        query,
        "--top-k",
        str(top_k),
        "--output-json",
        str(out),
    ]
    if st_model:
        cmd += ["--sentence-transformer-model", st_model]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or not out.is_file():
        return []
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    return [str(r["verse_id"]) for r in (doc.get("top_k") or []) if r.get("verse_id")]


def _theme_query_ko(theme_id: str) -> str:
    sidecar = ART / f"logos_themed_vector_{theme_id}_sidecar_latest.json"
    if sidecar.is_file():
        try:
            return str(json.loads(sidecar.read_text(encoding="utf-8-sig")).get("graphrag_query_ko") or theme_id)
        except json.JSONDecodeError:
            pass
    return theme_id


def _st_model(theme_id: str) -> str | None:
    br = ART / f"logos_themed_vector_{theme_id}_v1_latest.json"
    if not br.is_file():
        return None
    try:
        doc = json.loads(br.read_text(encoding="utf-8-sig"))
        if doc.get("embedding_mode") == "sentence_transformers_v1":
            return doc.get("sentence_transformer_model_id")
    except json.JSONDecodeError:
        pass
    return None


def compare_theme(theme_id: str, *, top_k: int) -> dict[str, Any]:
    anchors = _anchor_ids(theme_id)
    query = _theme_query_ko(theme_id)

    hash_sqlite = ART / f"logos_themed_vector_{theme_id}_hash_v1.sqlite"
    cache_jsonl = ROOT / "reports/cache/logos_themed_vector" / f"{theme_id}_verses.jsonl"
    if not cache_jsonl.is_file():
        subprocess.run(
            [PY, "scripts/build_logos_themed_vector_index_v1.py", "--theme", theme_id],
            cwd=ROOT,
            check=False,
        )

    hash_build = subprocess.run(
        [
            PY,
            "scripts/build_logos_vector_index_ann_lite_v1.py",
            "--verse-json",
            str(cache_jsonl),
            "--max-verses",
            "64",
            "--sqlite-out",
            str(hash_sqlite),
            "--report-json",
            str(ART / f"logos_themed_vector_{theme_id}_hash_v1_latest.json"),
            "--embedding-backend",
            "hash_stub_v1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    hash_hits: list[str] = []
    if hash_build.returncode == 0 and hash_sqlite.is_file():
        hash_hits = _query_sqlite(theme_id, hash_sqlite, query, top_k, None)

    st_sqlite = ART / f"logos_themed_vector_{theme_id}_v1.sqlite"
    st_model = _st_model(theme_id)
    st_hits: list[str] = []
    if st_sqlite.is_file() and st_model:
        st_hits = _query_sqlite(theme_id, st_sqlite, query, top_k, st_model)

    hash_stats = _recall_from_hits(anchors, hash_hits)
    st_stats = _recall_from_hits(anchors, st_hits)
    delta = round(st_stats["anchor_recall_at_k"] - hash_stats["anchor_recall_at_k"], 4)

    return {
        "theme_id": theme_id,
        "anchor_count": len(anchors),
        "top_k": top_k,
        "query_ko": query,
        "hash_stub_v1": {"backend": "hash_stub_v1", **hash_stats},
        "sentence_transformers": {"backend": "sentence_transformers_v1", **st_stats},
        "delta_recall_st_minus_hash": delta,
        "notes": "thematic anchor recall — not GraphRAG gold organic; research_only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    # Ensure verse jsonl cache exists
    for tid in THEMES:
        cache = ROOT / "reports/cache/logos_themed_vector" / f"{tid}_verses.jsonl"
        if not cache.is_file():
            subprocess.run(
                [PY, "scripts/build_logos_themed_vector_index_v1.py", "--theme", tid],
                cwd=ROOT,
                check=False,
            )

    themes = [compare_theme(t, top_k=max(1, args.top_k)) for t in THEMES]
    doc = {
        "schema": "logos_themed_retrieval_dual_backend_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "themes": themes,
        "reproduce": "py scripts/build_logos_themed_retrieval_dual_backend_eval_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
