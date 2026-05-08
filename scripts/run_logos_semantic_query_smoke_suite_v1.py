#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SQLITE = ART / "logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_OUT = ART / "logos_semantic_query_smoke_suite_latest.json"
DEFAULT_QUERY_SET = ART / "logos_semantic_query_set_v1.json"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_query(sqlite: Path, query: str, top_k: int, model_id: str) -> tuple[int, dict[str, Any], str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "query_logos_vector_index_ann_lite_v1.py"),
        "--sqlite",
        str(sqlite),
        "--query",
        query,
        "--top-k",
        str(int(top_k)),
        "--sentence-transformer-model",
        model_id,
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        return cp.returncode, {}, (cp.stderr or cp.stdout).strip()
    try:
        doc = json.loads(cp.stdout)
    except json.JSONDecodeError:
        return 98, {}, "invalid_json_from_query_tool"
    return 0, doc, ""


def _load_queries(path: Path) -> list[str]:
    if path.is_file():
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(obj, dict) and isinstance(obj.get("queries"), list):
            return [str(x).strip() for x in obj["queries"] if str(x).strip()]
    return [
        "risk regime stress",
        "inflation growth slowdown",
        "liquidity contraction shock",
        "defensive positioning signal",
        "policy uncertainty volatility",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run multi-query semantic smoke suite for Logos ANN-lite.")
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sqlite = args.sqlite if args.sqlite.is_absolute() else ROOT / args.sqlite
    query_set = args.query_set_json if args.query_set_json.is_absolute() else ROOT / args.query_set_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not sqlite.is_file():
        raise SystemExit(f"Missing sqlite index: {sqlite}")

    queries = _load_queries(query_set)
    rows: list[dict[str, Any]] = []
    for q in queries:
        rc, doc, err = _run_query(sqlite=sqlite, query=q, top_k=args.top_k, model_id=args.sentence_transformer_model)
        if rc != 0:
            rows.append({"query": q, "status": "error", "error": err[:300]})
            continue
        top_k = doc.get("top_k") if isinstance(doc.get("top_k"), list) else []
        top1 = top_k[0] if top_k and isinstance(top_k[0], dict) else {}
        score = top1.get("score")
        rows.append(
            {
                "query": q,
                "status": "ok",
                "embedding_mode": doc.get("embedding_mode"),
                "top_match_verse_id": top1.get("verse_id"),
                "top_match_cosine": float(score) if isinstance(score, (int, float)) else None,
            }
        )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    mean_top1 = (
        sum(float(r["top_match_cosine"]) for r in ok_rows if isinstance(r.get("top_match_cosine"), (int, float)))
        / len(ok_rows)
        if ok_rows
        else None
    )

    result = {
        "schema": "logos_semantic_query_smoke_suite_v1",
        "generated_at_utc": _now(),
        "sqlite_path": str(sqlite.resolve()),
        "query_set_path": str(query_set.resolve()) if query_set.is_file() else None,
        "sentence_transformer_model_id": args.sentence_transformer_model,
        "top_k": int(args.top_k),
        "rows": rows,
        "summary": {
            "queries_total": len(rows),
            "queries_ok": len(ok_rows),
            "queries_error": len(rows) - len(ok_rows),
            "mean_top1_cosine": None if mean_top1 is None else round(mean_top1, 9),
        },
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "queries_ok": len(ok_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

