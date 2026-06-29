#!/usr/bin/env python3
"""Themed vector retrieval eval — anchor recall@k vs hash_stub themed index."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = ROOT / "reports/logos_themed_retrieval_eval_v1_latest.json"
THEMES = ("dan_aramaic", "john_1_logos")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _anchor_ids(theme_id: str) -> set[str]:
    distill_path = ART / f"logos_deep_research_distill_{theme_id}_latest.json"
    if not distill_path.is_file():
        return set()
    doc = json.loads(distill_path.read_text(encoding="utf-8-sig"))
    ids: set[str] = set()
    for ref in doc.get("evidence_refs") or []:
        if isinstance(ref, dict):
            vid = ref.get("verse_id")
            if isinstance(vid, str) and vid.strip() and not vid.startswith("sample-"):
                ids.add(vid.strip())
    return ids


def _query_top_k(theme_id: str, top_k: int) -> list[str]:
    q_path = ART / f"logos_themed_vector_query_{theme_id}_latest.json"
    if not q_path.is_file():
        subprocess.run(
            [PY, "scripts/query_logos_themed_vector_index_v1.py", "--theme", theme_id, "--top-k", str(top_k)],
            cwd=ROOT,
            check=False,
        )
    if not q_path.is_file():
        return []
    doc = json.loads(q_path.read_text(encoding="utf-8-sig"))
    out: list[str] = []
    for row in doc.get("top_k") or []:
        if isinstance(row, dict) and row.get("verse_id"):
            out.append(str(row["verse_id"]))
    return out


def eval_theme(theme_id: str, *, top_k: int) -> dict[str, Any]:
    anchors = _anchor_ids(theme_id)
    hits = _query_top_k(theme_id, top_k)
    hit_set = set(hits[:top_k])
    overlap = sorted(anchors & hit_set)
    recall = (len(overlap) / len(anchors)) if anchors else 0.0
    sidecar = ART / f"logos_themed_vector_{theme_id}_sidecar_latest.json"
    emb = "unknown"
    if sidecar.is_file():
        try:
            emb = json.loads(sidecar.read_text(encoding="utf-8-sig")).get("embedding_backend") or emb
        except json.JSONDecodeError:
            pass
    q_path = ART / f"logos_themed_vector_query_{theme_id}_latest.json"
    if q_path.is_file():
        try:
            qdoc = json.loads(q_path.read_text(encoding="utf-8-sig"))
            mode = qdoc.get("embedding_mode")
            if mode == "sentence_transformers_v1":
                emb = "sentence_transformers"
            elif mode == "hash_stub_v1":
                emb = "hash_stub_v1"
        except json.JSONDecodeError:
            pass
    return {
        "theme_id": theme_id,
        "embedding_backend": emb,
        "anchor_count": len(anchors),
        "top_k": top_k,
        "retrieved": hits[:top_k],
        "overlap_verse_ids": overlap,
        "anchor_recall_at_k": round(recall, 4),
        "notes": "anchor set = distill evidence_refs; hash_stub scores are not semantic — baseline only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    themes = [eval_theme(t, top_k=max(1, args.top_k)) for t in THEMES]
    doc = {
        "schema": "logos_themed_retrieval_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "themes": themes,
        "reproduce": "py scripts/build_logos_themed_retrieval_eval_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
