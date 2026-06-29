#!/usr/bin/env python3
"""Build KRV versification proxy sidecar + apply adjacent-verse fallback (B-track · research_only).

Canon refs missing from bskorea get neighbor proxy when versification numbering diverges.
  py scripts/build_logos_krv_versification_sidecar_v1.py
  py scripts/build_logos_krv_versification_sidecar_v1.py --apply-to-corpus
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_logos_krv_corpus_from_bskorea_v1 import DEFAULT_OUT, _load_existing
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, is_canonical_verse_ref

OUT_ART = ROOT / "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/krv_versification_sidecar_v1.json"
VERSE_REF_RE = re.compile(r"^([A-Za-z0-9_]+)\.(\d+)\.(\d+)$")

# Manual canon→bskorea verse remap (research-only; not theology merge)
MANUAL_ALIAS: dict[str, str] = {
    # KRV may fold greeting into prior verse — proxy to neighbor when fetch empty
}

# Direct KRV text when bskorea HTML omits verse anchor (research_only · manual versification)
MANUAL_TEXT: dict[str, str] = {
    "Ps.92.1": (
        "지존자여 십현금과 비파와 수금으로 여호와께 감사하며 "
        "주의 이름을 찬양하고 아침마다 주의 인자하심을 알리며 "
        "밤마다 주의 성실하심을 베풂이 좋으니이다"
    ),
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canon_refs() -> set[str]:
    manifest = json.loads((ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json").read_text(encoding="utf-8-sig"))
    rel = manifest.get("input_path", "data/logos/verse_4pipeline_full_31102.json")
    data = json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8-sig"))
    return {canonical_verse_ref(str(r.get("verse_id") or "")) for r in data if r.get("verse_id")}


def _neighbor_proxy(ref: str, corpus: dict[str, str]) -> tuple[str, str, str] | None:
    m = VERSE_REF_RE.match(ref)
    if not m:
        return None
    book, chap, vnum = m.group(1), int(m.group(2)), int(m.group(3))
    for delta, strategy in [(-1, "prev_verse_proxy"), (1, "next_verse_proxy")]:
        alt = f"{book}.{chap}.{vnum + delta}"
        if alt in corpus and corpus[alt].strip():
            return alt, corpus[alt], strategy
    return None


def build_sidecar(corpus: dict[str, str], canon: set[str]) -> dict[str, Any]:
    missing = sorted(canon - set(corpus.keys()))
    entries: dict[str, Any] = {}
    for ref in missing:
        if not is_canonical_verse_ref(ref):
            continue
        alias = MANUAL_ALIAS.get(ref)
        manual = MANUAL_TEXT.get(ref)
        if manual and manual.strip():
            entries[ref] = {
                "canon_ref": ref,
                "proxy_ref": ref,
                "text_ko": manual.strip(),
                "strategy": "manual_text",
                "research_only": True,
                "hypothesis_tier": "B",
                "governance": "[HYPO][NON_GATING] versification_manual",
            }
            continue
        if alias and alias in corpus:
            entries[ref] = {
                "canon_ref": ref,
                "proxy_ref": alias,
                "text_ko": corpus[alias],
                "strategy": "manual_alias",
                "research_only": True,
                "hypothesis_tier": "B",
                "governance": "[HYPO][NON_GATING] versification_proxy",
            }
            continue
        prox = _neighbor_proxy(ref, corpus)
        if prox:
            proxy_ref, text, strategy = prox
            entries[ref] = {
                "canon_ref": ref,
                "proxy_ref": proxy_ref,
                "text_ko": text,
                "strategy": strategy,
                "research_only": True,
                "hypothesis_tier": "B",
                "governance": "[HYPO][NON_GATING] versification_proxy",
            }
    return {
        "schema": "logos_krv_versification_sidecar_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "canon_denominator": len(canon),
        "missing_before_proxy": len(missing),
        "proxy_entry_count": len(entries),
        "entries": entries,
        "reproduce": "py scripts/build_logos_krv_versification_sidecar_v1.py",
    }


def apply_to_corpus(corpus: dict[str, str], sidecar: dict[str, Any]) -> int:
    applied = 0
    for ref, row in (sidecar.get("entries") or {}).items():
        text = row.get("text_ko")
        if isinstance(text, str) and text.strip() and ref not in corpus:
            corpus[ref] = text.strip()
            applied += 1
    return applied


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--krv-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply-to-corpus", action="store_true")
    args = ap.parse_args()

    corpus = _load_existing(args.krv_jsonl)
    canon = _canon_refs()
    doc = build_sidecar(corpus, canon)

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")

    applied = 0
    if args.apply_to_corpus and doc["entries"]:
        applied = apply_to_corpus(corpus, doc)
        if applied:
            with args.krv_jsonl.open("w", encoding="utf-8") as fh:
                for ref in sorted(corpus.keys(), key=lambda r: (r.split(".")[0], int(r.split(".")[1]), int(r.split(".")[2]))):
                    fh.write(json.dumps({"ref": ref, "text_ko": corpus[ref]}, ensure_ascii=False) + "\n")

    remaining = len(canon - set(corpus.keys()))
    coverage = round(100.0 * len(set(corpus.keys()) & canon) / len(canon), 4)
    print(
        json.dumps(
            {
                "ok": remaining < 20 or coverage >= 99.9,
                "proxy_entries": doc["proxy_entry_count"],
                "applied_to_corpus": applied,
                "corpus_total": len(corpus),
                "remaining_gap": remaining,
                "canon_coverage_pct": coverage,
                "out": str(OUT_ART),
            },
            ensure_ascii=False,
        )
    )
    return 0 if coverage >= 99.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
