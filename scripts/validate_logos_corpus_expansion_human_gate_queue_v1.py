#!/usr/bin/env python3
"""Validate corpus expansion Human Gate queue (wave 101+)."""

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

from scripts.core.logos_verse_corpus_lookup_v1 import normalize_verse_ref

QUEUE = ROOT / "docs/final/artifacts/logos_corpus_expansion_human_gate_queue_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_corpus_expansion_validation_v1_latest.json"

VERSE_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")
MIN_LEMMA_LEN = 3


def _occupied_enabled(registry_path: Path) -> set[str]:
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for e in reg.get("entries", []):
        if e.get("enabled"):
            for v in e.get("verse_refs") or []:
                out.add(normalize_verse_ref(str(v)))
    return out


def validate(queue_path: Path = QUEUE, registry_path: Path = REGISTRY) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    wave = int(queue.get("wave", 1))
    min_slot = 101 + (wave - 1) * int(queue.get("wave_size", 100))
    occupied = _occupied_enabled(registry_path)
    errors: list[str] = []
    per_entry: list[dict[str, Any]] = []
    seen_verses: set[str] = set()
    seen_slots: set[str] = set()

    for entry in queue.get("entries", []):
        row_errors: list[str] = []
        slot_id = str(entry.get("slot_id", ""))
        slot_num = entry.get("slot_num")
        if not (isinstance(slot_num, int) and slot_num >= min_slot):
            row_errors.append(f"slot_num must be >= {min_slot} for wave {wave}")
        if slot_id in seen_slots:
            row_errors.append("duplicate slot_id")
        seen_slots.add(slot_id)

        verses = entry.get("proposed_verse_refs") or []
        if not verses:
            row_errors.append("missing verse ref")
        else:
            vid = str(verses[0])
            if not VERSE_RE.match(vid):
                row_errors.append(f"invalid verse: {vid}")
            if vid in occupied:
                row_errors.append("conflicts with enabled registry")
            if vid in seen_verses:
                row_errors.append("duplicate verse in queue")
            seen_verses.add(vid)

        lemma = entry.get("motif_lemma") or {}
        text = str(lemma.get("greek") or lemma.get("hebrew") or "")
        if len(text) < MIN_LEMMA_LEN:
            row_errors.append(f"lemma too short (<{MIN_LEMMA_LEN})")

        per_entry.append(
            {
                "slot_id": slot_id,
                "verse_ref": verses[0] if verses else None,
                "ok": not row_errors,
                "errors": row_errors,
            }
        )
        errors.extend(f"{slot_id}: {e}" for e in row_errors)

    ok_count = sum(1 for r in per_entry if r["ok"])
    return {
        "schema": "logos_corpus_expansion_validation_v1",
        "generated_at_utc": generated_at_utc,
        "queue_count": len(per_entry),
        "ok_count": ok_count,
        "pass": ok_count == len(per_entry) and len(per_entry) > 0,
        "errors": errors,
        "per_entry": per_entry,
        "reproducible_command": "py scripts/validate_logos_corpus_expansion_human_gate_queue_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = validate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"  pass={report['pass']} ok={report['ok_count']}/{report['queue_count']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
