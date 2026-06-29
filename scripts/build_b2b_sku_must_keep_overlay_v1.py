#!/usr/bin/env python3
"""Build B2B SKU must_keep overlay from b2b shard + corpus (incl. Hangul terms). [HYPO]"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"
HANGUL_RE = re.compile(r"[가-힣]{2,}")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_shard_terms(shard_path: Path) -> tuple[list[str], list[str]]:
    if not shard_path.is_file():
        return [], []
    doc = json.loads(shard_path.read_text(encoding="utf-8-sig"))
    hard = list(doc.get("must_keep_hard_terms") or [])
    soft = list(doc.get("must_keep_soft_terms") or [])
    rk = list(doc.get("routing_keywords") or [])
    for t in rk:
        if t not in hard and t not in soft:
            soft.append(t)
    return hard, soft


def _corpus_hangul_terms(corpus: Path, *, min_freq: int = 2, max_terms: int = 24) -> tuple[list[str], list[str]]:
    from collections import Counter

    counter: Counter[str] = Counter()
    rows = 0
    for line in corpus.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        text = obj.get("text") or obj.get("raw_text") or ""
        if not isinstance(text, str):
            continue
        rows += 1
        for term in HANGUL_RE.findall(text):
            if len(term) >= 2:
                counter[term] += 1
    hard: list[str] = []
    soft: list[str] = []
    for term, freq in counter.most_common():
        if freq < min_freq:
            break
        if len(hard) + len(soft) >= max_terms:
            break
        if freq >= 3 or len(term) >= 4:
            hard.append(term)
        else:
            soft.append(term)
    return hard, soft


def build_overlay(
    external_sku: str,
    corpus_path: Path,
    *,
    spec_path: Path = SPEC,
) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    sku_row = next((s for s in spec.get("skus") or [] if s.get("external_sku") == external_sku), None)
    if not sku_row:
        raise KeyError(f"unknown sku: {external_sku}")
    shard_path = ROOT / str(sku_row["b2b_shard_path"])
    shard_hard, shard_soft = _load_shard_terms(shard_path)
    corp_hard, corp_soft = _corpus_hangul_terms(corpus_path)
    seen: set[str] = set()
    hard: list[str] = []
    soft: list[str] = []
    for t in shard_hard + corp_hard:
        if t not in seen:
            seen.add(t)
            hard.append(t)
    for t in shard_soft + corp_soft:
        if t not in seen:
            seen.add(t)
            soft.append(t)
    slug = external_sku.lower().replace("mkm-", "").replace("-", "_")
    return {
        "schema": "compression_tenant_must_keep_overlay_v1",
        "tenant_id": f"b2b-{slug}",
        "external_sku": external_sku,
        "generated_at_utc": _utc(),
        "source_corpus": corpus_path.relative_to(ROOT).as_posix(),
        "b2b_shard_path": sku_row["b2b_shard_path"],
        "labels": ["DRAFT", "research_only", "b2b_sku_overlay_v1"],
        "must_keep_hard_terms": hard[:32],
        "must_keep_soft_terms": soft[:32],
        "extraction_stats": {
            "shard_hard": len(shard_hard),
            "shard_soft": len(shard_soft),
            "corpus_hangul_hard": len(corp_hard),
            "corpus_hangul_soft": len(corp_soft),
        },
        "boundary_ack": "B1 overlay — evaluate_report hydrate arm only; not Track A auto-router.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--external-sku", required=True)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()
    corpus = args.input_jsonl.resolve()
    if not corpus.is_file():
        print(f"error: missing corpus: {corpus}", file=sys.stderr)
        return 2
    doc = build_overlay(args.external_sku, corpus)
    slug = args.external_sku.lower().replace("mkm-", "")
    out = args.out_json or (ROOT / f"docs/final/artifacts/b2b_sku_{slug}_must_keep_overlay_v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hard": len(doc["must_keep_hard_terms"]), "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
