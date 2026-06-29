#!/usr/bin/env python3
"""Ingest KRV (개역개정) verse corpus for Logos citation shard — P1 bible_full.

Expected input (not committed): data/logos/krv_verses_v1.jsonl
  {"ref": "Gen.1.1", "text_ko": "..."}

Merges with insight/reading sidecars and writes studio shard (same outputs as hand-curated builder).

  py scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py
  py scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py --krv-jsonl path/to/krv.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, is_canonical_verse_ref
INSIGHT = ROOT / "docs/final/artifacts/showroom_qa_node_insight_cards_v1_latest.json"
READING = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/verse_citation_shard_v1.json"
READINESS = ROOT / "reports/logos_krv_corpus_ingest_readiness_v1_latest.json"

DEFAULT_KRV = ROOT / "data/logos/krv_verses_v1.jsonl"
VERSIFICATION_SIDECAR = ROOT / "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clean_excerpt(raw: str, cap: int = 220) -> str:
    s = re.sub(r"\*\*", "", raw or "")
    s = re.sub(r"`[^`]+`", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > cap:
        s = s[: cap - 1].rstrip() + "…"
    return s


def _stage_by_ref(reading: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for stage in reading.get("narrative_route_public") or []:
        for ref in stage.get("verse_refs") or []:
            out[ref] = {
                "stage_id": stage.get("stage_id"),
                "stage_label_ko": stage.get("label_ko"),
                "bottleneck_ko": stage.get("bottleneck_ko"),
            }
    return out


def _load_krv_jsonl(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        ref = row.get("ref") or row.get("verse_id")
        text = row.get("text_ko") or row.get("text")
        if not isinstance(ref, str) or not isinstance(text, str):
            continue
        ref = canonical_verse_ref(ref.strip())
        if not is_canonical_verse_ref(ref):
            continue
        out[ref] = text.strip()
    return out


def _write_readiness(krv_path: Path, *, ok: bool, reason: str, verse_count: int = 0) -> None:
    doc = {
        "schema": "logos_krv_corpus_ingest_readiness_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "reason": reason,
        "expected_path": str(krv_path),
        "verse_count": verse_count,
        "reproduce": "py scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py",
    }
    READINESS.parent.mkdir(parents=True, exist_ok=True)
    READINESS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--krv-jsonl", type=Path, default=DEFAULT_KRV)
    ap.add_argument("--min-verses", type=int, default=1000, help="Minimum KRV lines to accept full corpus ingest")
    args = ap.parse_args()

    krv = _load_krv_jsonl(args.krv_jsonl)
    vers_side = _load_json(VERSIFICATION_SIDECAR) if VERSIFICATION_SIDECAR.is_file() else {}
    vers_entries = vers_side.get("entries") or {}
    for ref, row in vers_entries.items():
        if ref not in krv and isinstance(row.get("text_ko"), str) and row["text_ko"].strip():
            krv[ref] = row["text_ko"].strip()
    if len(krv) < args.min_verses:
        _write_readiness(
            args.krv_jsonl,
            ok=False,
            reason=f"krv_corpus_missing_or_too_small_{len(krv)}_lt_{args.min_verses}",
            verse_count=len(krv),
        )
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "krv_jsonl_missing_or_small",
                    "path": str(args.krv_jsonl),
                    "verse_count": len(krv),
                    "readiness": str(READINESS),
                },
                ensure_ascii=False,
            )
        )
        return 2

    insight = _load_json(INSIGHT)
    reading = _load_json(READING) if READING.is_file() else {}
    stage_map = _stage_by_ref(reading)
    cards = insight.get("cards") or {}

    verses: dict[str, dict] = {}
    for ref, text_ko in krv.items():
        stage = stage_map.get(ref, {})
        card = None
        for key, c in cards.items():
            if c.get("ref") == ref or key.endswith(ref):
                card = c
                break
        verses[ref] = {
            "ref": ref,
            "text_ko": text_ko,
            "translation_id": "krv",
            "stage_id": stage.get("stage_id") or (card or {}).get("stage_id"),
            "stage_label_ko": stage.get("stage_label_ko"),
            "bottleneck_ko": (card or {}).get("bottleneck_ko") or stage.get("bottleneck_ko"),
            "verse_note_ko": _clean_excerpt((card or {}).get("excerpt_ko") or "") or None,
            "governance": (card or {}).get("governance") or "[HYPO][NON_GATING]",
        }

    for ref, row in vers_entries.items():
        if ref in verses:
            verses[ref]["governance"] = "[HYPO][NON_GATING] versification_proxy"
            if row.get("proxy_ref"):
                verses[ref]["verse_note_ko"] = f"versification_proxy via {row.get('proxy_ref')}"

    doc = {
        "schema_version": "logos_studio_verse_citation_shard_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "translation_note_ko": "개역개정(KRV) full corpus ingest — 신학·인과 단답·Track A 근거 아님.",
        "verse_count": len(verses),
        "verses": verses,
        "source_krv_jsonl": str(args.krv_jsonl),
        "reproducible_command": "py scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py",
    }

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")
    _write_readiness(args.krv_jsonl, ok=True, reason="krv_corpus_ingested", verse_count=len(verses))
    print(json.dumps({"ok": True, "verse_count": len(verses), "out": str(OUT_PUB)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
