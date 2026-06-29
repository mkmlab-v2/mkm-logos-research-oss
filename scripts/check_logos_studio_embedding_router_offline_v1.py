#!/usr/bin/env python3
"""Offline smoke: embedding router matches paraphrase queries to BigSet presets."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "reports/logos_studio_embedding_router_offline_v1_latest.json"
DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_INDEX = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"

PARAPHRASE_CASES: list[tuple[str, str, set[str]]] = [
    (
        "fallen_angels_marriage_tradition",
        "타락한 천사가 인간 여성과 결혼했다는 고대 전통",
        {"bigset_topic_watchers", "bigset_topic_nephilim", "bigset_topic_benei_haelohim"},
    ),
    (
        "divine_sons_psalm_job",
        "하늘 회의에서 말하는 하나님의 아들들은 누구인가",
        {"bigset_topic_divine_council", "bigset_topic_benei_haelohim"},
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    return dot / (na * nb) if na and nb else 0.0


def _encode_query(query: str) -> list[float]:
    proc = subprocess.run(
        [PY, str(ROOT / "scripts/encode_logos_studio_query_embedding_v1.py"), "--query-stdin"],
        input=query,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[:200] or f"encode_exit_{proc.returncode}")
    doc = json.loads(proc.stdout)
    if not doc.get("ok"):
        raise RuntimeError(str(doc.get("error") or "encode_failed"))
    return list(doc["vector"])


def _resolve_embedding(query: str, index: dict[str, Any]) -> tuple[str | None, float]:
    qvec = _encode_query(query)
    threshold = float(index.get("min_cosine_threshold") or 0.42)
    best_id: str | None = None
    best_score = -1.0
    for row in index.get("vectors") or []:
        score = _cosine(qvec, list(row.get("vector") or []))
        if score > best_score:
            best_score = score
            best_id = str(row.get("preset_id"))
    if best_id and best_score >= threshold:
        return best_id, best_score
    return None, best_score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not DEFAULT_INDEX.is_file():
        print(f"missing index: {DEFAULT_INDEX}", file=sys.stderr)
        return 2
    index = json.loads(DEFAULT_INDEX.read_text(encoding="utf-8-sig"))
    presets = json.loads(DEFAULT_PRESETS.read_text(encoding="utf-8-sig"))
    from scripts.match_logos_studio_preset_query_v1 import load_default_lexical_index, resolve_preset_id

    lexical = load_default_lexical_index()
    failures: list[str] = []
    cases: dict[str, Any] = {}
    for key, query, allowed in PARAPHRASE_CASES:
        tier01 = resolve_preset_id(presets["presets"], query=query, lexical_index=lexical)
        emb_id, emb_score = _resolve_embedding(query, index)
        tier01_id = tier01.get("preset_id")
        if tier01_id and str(tier01_id).startswith("bigset_topic_"):
            picked = tier01_id
            match = tier01["match"]
        elif emb_id and (
            not tier01_id or str(tier01_id).startswith("era_") or str(tier01_id).startswith("topic_")
        ):
            picked = emb_id
            match = "embedding"
        else:
            picked = tier01_id or emb_id
            match = tier01["match"] if tier01_id else ("embedding" if emb_id else "none")
        cases[key] = {
            "query": query,
            "tier01": tier01,
            "embedding_preset_id": emb_id,
            "embedding_score": round(emb_score, 4),
            "picked": picked,
            "match": match,
        }
        if not picked or picked not in allowed:
            failures.append(f"{key}: picked={picked} allowed={sorted(allowed)}")
    ok = not failures
    doc = {
        "schema": "logos_studio_embedding_router_offline_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "gate_pass": ok,
        "gate_failures": failures,
        "cases": cases,
        "reproducible_command": "py scripts/check_logos_studio_embedding_router_offline_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "gate_failures": failures, "out": str(args.output)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
