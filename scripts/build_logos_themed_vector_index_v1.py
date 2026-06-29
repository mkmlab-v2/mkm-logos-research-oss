#!/usr/bin/env python3
"""Build a small themed verse vector index (hash_stub or optional sentence-transformers)."""

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

from scripts.logos_deep_research_graph_evidence_v1 import (
    DEFAULT_VERSE_JSONL,
    load_theme_preset,
    load_verse_ids_by_prefix,
    load_verse_rows,
)

PY = sys.executable
POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"
ART = ROOT / "docs/final/artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_theme_jsonl(theme_id: str, verse_ids: list[str], out_path: Path) -> int:
    rows = load_verse_rows(set(verse_ids), DEFAULT_VERSE_JSONL)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for vid in verse_ids:
            row = rows.get(vid)
            if not row:
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", required=True, help="Theme id from LOGOS_TRACK_B_THEME_PRESETS_V1.json")
    ap.add_argument(
        "--embedding-backend",
        choices=("hash_stub_v1", "sentence_transformers"),
        default="hash_stub_v1",
    )
    ap.add_argument(
        "--try-sentence-transformers",
        action="store_true",
        help="Try ST backend; fall back to hash_stub_v1 on failure.",
    )
    ap.add_argument("--max-verses", type=int, default=0, help="0 = use preset max_verses or 32")
    args = ap.parse_args()

    backend = args.embedding_backend
    if args.try_sentence_transformers:
        probe = subprocess.run(
            [PY, "scripts/probe_logos_sentence_transformers_readiness_v1.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            backend = "sentence_transformers"
        else:
            backend = "hash_stub_v1"

    try:
        preset = load_theme_preset(args.theme)
    except (FileNotFoundError, KeyError) as e:
        print(str(e), file=sys.stderr)
        return 2

    prefix = str(preset.get("verse_prefix") or "")
    cap = args.max_verses or int(preset.get("max_verses") or 32)
    verse_ids = load_verse_ids_by_prefix(prefix, DEFAULT_VERSE_JSONL, max_verses=cap)
    if not verse_ids:
        print(f"No verses for prefix {prefix!r}", file=sys.stderr)
        return 2

    cache_dir = ROOT / "reports/cache/logos_themed_vector"
    cache_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = cache_dir / f"{args.theme}_verses.jsonl"
    row_count = _write_theme_jsonl(args.theme, verse_ids, jsonl_path)
    if row_count < 1:
        print("No verse rows materialized.", file=sys.stderr)
        return 2

    sqlite_out = ART / f"logos_themed_vector_{args.theme}_v1.sqlite"
    report_out = ART / f"logos_themed_vector_{args.theme}_v1_latest.json"

    cmd = [
        PY,
        "scripts/build_logos_vector_index_ann_lite_v1.py",
        "--verse-json",
        str(jsonl_path),
        "--max-verses",
        str(row_count),
        "--sqlite-out",
        str(sqlite_out),
        "--report-json",
        str(report_out),
        "--embedding-backend",
        backend,
    ]
    if backend == "sentence_transformers":
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        model_id = (policy.get("embedding") or {}).get("model_id")
        if isinstance(model_id, str) and model_id.strip():
            cmd += ["--sentence-transformer-model", model_id.strip()]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    sidecar: dict[str, Any] = {
        "schema": "logos_themed_vector_index_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "theme_id": args.theme,
        "verse_prefix": prefix,
        "verse_count": row_count,
        "embedding_backend": backend,
        "embedding_backend_requested": args.embedding_backend,
        "st_try_requested": args.try_sentence_transformers,
        "sqlite": str(sqlite_out.relative_to(ROOT)).replace("\\", "/"),
        "build_report": str(report_out.relative_to(ROOT)).replace("\\", "/"),
        "verse_jsonl_cache": str(jsonl_path.relative_to(ROOT)).replace("\\", "/"),
        "graphrag_query_ko": preset.get("graphrag_query_ko"),
        "notes": "hash_stub scores are not semantic relevance unless sentence_transformers backend.",
    }
    sidecar_path = ART / f"logos_themed_vector_{args.theme}_sidecar_latest.json"
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "theme": args.theme,
                "verse_count": row_count,
                "sqlite": sidecar["sqlite"],
                "sidecar": str(sidecar_path.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
