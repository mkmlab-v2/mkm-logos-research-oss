#!/usr/bin/env python3
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
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SQLITE = ART / "logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_QUERYSET_A = ART / "logos_semantic_query_set_v2.json"
DEFAULT_QUERYSET_B = ART / "logos_semantic_query_set_v3.json"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_OUT = ART / "logos_semantic_queryset_ab_compare_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_suite(sqlite: Path, query_set: Path, model: str, top_k: int, out_path: Path) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_logos_semantic_query_smoke_suite_v1.py"),
        "--sqlite",
        str(sqlite),
        "--query-set-json",
        str(query_set),
        "--sentence-transformer-model",
        model,
        "--top-k",
        str(top_k),
        "--output-json",
        str(out_path),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        return cp.returncode, (cp.stderr or cp.stdout).strip()[:500]
    return 0, ""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summary(doc: dict[str, Any]) -> dict[str, Any]:
    s = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    return {
        "queries_total": int(s.get("queries_total") or 0),
        "queries_ok": int(s.get("queries_ok") or 0),
        "queries_error": int(s.get("queries_error") or 0),
        "mean_top1_cosine": float(s.get("mean_top1_cosine") or 0.0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare Logos semantic query sets (A/B) using same model/index.")
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-a", type=Path, default=DEFAULT_QUERYSET_A)
    ap.add_argument("--query-set-b", type=Path, default=DEFAULT_QUERYSET_B)
    ap.add_argument("--label-a", type=str, default="v2")
    ap.add_argument("--label-b", type=str, default="v3")
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sqlite = args.sqlite if args.sqlite.is_absolute() else ROOT / args.sqlite
    qa = args.query_set_a if args.query_set_a.is_absolute() else ROOT / args.query_set_a
    qb = args.query_set_b if args.query_set_b.is_absolute() else ROOT / args.query_set_b
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    for p in (sqlite, qa, qb):
        if not p.is_file():
            raise SystemExit(f"Missing required path: {p}")

    with tempfile.TemporaryDirectory(prefix="logos_queryset_ab_") as td:
        td_path = Path(td)
        out_a = td_path / "suite_a.json"
        out_b = td_path / "suite_b.json"
        rc_a, err_a = _run_suite(sqlite, qa, args.sentence_transformer_model, int(args.top_k), out_a)
        rc_b, err_b = _run_suite(sqlite, qb, args.sentence_transformer_model, int(args.top_k), out_b)
        if rc_a != 0 or rc_b != 0:
            raise SystemExit(f"queryset_ab_failed a={rc_a}:{err_a} b={rc_b}:{err_b}")

        sa = _summary(_read_json(out_a))
        sb = _summary(_read_json(out_b))

    delta = {
        "mean_top1_cosine": round(sb["mean_top1_cosine"] - sa["mean_top1_cosine"], 9),
        "queries_error": sb["queries_error"] - sa["queries_error"],
        "queries_ok": sb["queries_ok"] - sa["queries_ok"],
    }
    better = "B" if delta["mean_top1_cosine"] > 0 and delta["queries_error"] <= 0 else "A"
    result = {
        "schema": "logos_semantic_queryset_ab_compare_v1",
        "generated_at_utc": _now(),
        "model_id": args.sentence_transformer_model,
        "top_k": int(args.top_k),
        "query_set_a": {"label": args.label_a, "path": str(qa.resolve()), "summary": sa},
        "query_set_b": {"label": args.label_b, "path": str(qb.resolve()), "summary": sb},
        "delta_b_minus_a": delta,
        "recommended_set": args.label_b if better == "B" else args.label_a,
        "track_wall": {"shadow_only": True, "auto_trade_enable": False},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "recommended_set": result["recommended_set"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

