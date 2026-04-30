#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

STOPWORDS = {
    "the",
    "and",
    "that",
    "with",
    "from",
    "unto",
    "upon",
    "this",
    "there",
    "them",
    "they",
    "have",
    "were",
    "shall",
    "your",
    "their",
    "would",
    "could",
    "should",
    "into",
    "then",
    "than",
    "when",
    "what",
    "which",
    "whom",
    "thou",
    "thee",
    "said",
    "lord",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _tokenize(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-z]{3,}", text.lower())
    return [t for t in toks if t not in STOPWORDS]


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build readable digest from universal precursor clusters.")
    ap.add_argument(
        "--ruleset-json",
        default="docs/final/artifacts/universal_precursor_ruleset_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_cluster_digest_v1_latest.json",
    )
    ap.add_argument("--top-keywords", type=int, default=8)
    args = ap.parse_args()

    src = _resolve(args.ruleset_json)
    out = _resolve(args.output_json)
    data = _read_json(src)
    clusters = data.get("universal_precursor_clusters")
    if not isinstance(clusters, list):
        raise SystemExit("invalid ruleset: universal_precursor_clusters missing")

    digest_rows: list[dict[str, Any]] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        rep = str(c.get("representative_text_preview") or "")
        sample_ids = c.get("sample_verse_ids") if isinstance(c.get("sample_verse_ids"), list) else []
        toks = _tokenize(rep)
        top_kw = [k for k, _ in Counter(toks).most_common(max(1, int(args.top_keywords)))]
        digest_rows.append(
            {
                "cluster_id": c.get("cluster_id"),
                "size": int(c.get("size") or 0),
                "coherence_score_0_1": float(c.get("coherence_score_0_1") or 0.0),
                "representative_verse_id": c.get("representative_verse_id"),
                "keywords_top": top_kw,
                "representative_text_preview": rep,
                "sample_verse_ids_head": sample_ids[:10],
            }
        )

    digest_rows.sort(key=lambda r: (r["size"], r["coherence_score_0_1"]), reverse=True)
    out_doc = {
        "schema": "universal_precursor_cluster_digest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "source_ruleset_json": str(src),
        "gate_decision": (data.get("gate") or {}).get("decision"),
        "cluster_count": len(digest_rows),
        "clusters": digest_rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
