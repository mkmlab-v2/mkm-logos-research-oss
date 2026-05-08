#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_QUERY_SMOKE = ART / "logos_vector_ann_lite_query_smoke_latest.json"
DEFAULT_OUT = ART / "logos_semantic_drift_monitor_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build semantic drift monitor from ANN-lite query smoke."
    )
    ap.add_argument("--query-smoke-json", type=Path, default=DEFAULT_QUERY_SMOKE)
    ap.add_argument("--min-cosine", type=float, default=0.10)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    query_smoke_path = (
        args.query_smoke_json
        if args.query_smoke_json.is_absolute()
        else ROOT / args.query_smoke_json
    )
    if not query_smoke_path.is_file():
        raise SystemExit(f"Missing query smoke json: {query_smoke_path}")

    doc = _read_json(query_smoke_path)
    top_k = doc.get("top_k")
    if not isinstance(top_k, list):
        top_k = []

    top_score = None
    top_verse = None
    if top_k:
        first = top_k[0] if isinstance(top_k[0], dict) else {}
        score = first.get("score")
        if isinstance(score, (int, float)):
            top_score = float(score)
        verse = first.get("verse_id")
        if isinstance(verse, str) and verse.strip():
            top_verse = verse.strip()

    min_cosine = float(args.min_cosine)
    low_conf = top_score is None or top_score < min_cosine

    out = {
        "schema": "logos_semantic_drift_monitor_v1",
        "generated_at_utc": _now(),
        "source_query_smoke_json": str(query_smoke_path.resolve()),
        "embedding_mode": doc.get("embedding_mode"),
        "query_seed": doc.get("query_seed"),
        "policy": {
            "min_cosine": round(min_cosine, 6),
            "low_confidence_when_below_min": True,
        },
        "snapshot": {
            "top_verse_id": top_verse,
            "top_cosine_similarity": None if top_score is None else round(top_score, 9),
            "top_k_size": len(top_k),
        },
        "guard": {
            "low_confidence": low_conf,
            "decision": "LOW_CONFIDENCE" if low_conf else "OK",
            "reason": "top_cosine_below_threshold_or_missing" if low_conf else "top_cosine_within_threshold",
        },
        "track_wall": {
            "auto_trade_enable": False,
            "shadow_observation_only": True,
        },
    }

    output = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(output), "low_confidence": low_conf}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

