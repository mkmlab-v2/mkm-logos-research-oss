#!/usr/bin/env python3
"""Build Human Gate queue wave from corpus expansion pilot (proposed only).

Reproducible:
  py scripts/run_logos_corpus_expansion_pilot_v1.py
  py scripts/build_logos_corpus_expansion_human_gate_queue_v1.py --wave 1
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

from scripts.core.logos_verse_corpus_lookup_v1 import lookup_verse, normalize_verse_ref

PILOT = ROOT / "docs/final/artifacts/logos_corpus_expansion_pilot_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_corpus_expansion_human_gate_queue_v1_latest.json"
TEMPLATE = ROOT / "docs/final/artifacts/logos_corpus_expansion_human_gate_queue_template_v1.json"

VERSE_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _registry_occupied(registry_path: Path) -> set[str]:
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for e in reg.get("entries", []):
        if e.get("enabled"):
            for v in e.get("verse_refs") or []:
                out.add(normalize_verse_ref(str(v)))
    return out


def _stem_from_verse(verse_id: str) -> str:
    book = verse_id.split(".")[0].lower()
    ch_v = verse_id.replace(".", "_").lower()
    return f"verse_{book}_{ch_v}"


def build_queue(
    *,
    pilot_path: Path = PILOT,
    registry_path: Path = REGISTRY,
    wave: int = 1,
    wave_size: int = 100,
    start_slot: int = 101,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    scan = pilot["tier1_scan"]
    occupied = _registry_occupied(registry_path)
    candidates = scan.get("expansion_candidate_preview") or []
    # Backfill from motif ranking samples if preview shorter than wave_size
    target_pool = wave_size * (wave + 1)
    if len(candidates) < target_pool:
        seen_vids = {str(c.get("verse_id")) for c in candidates}
        for row in scan.get("motif_hit_ranking") or []:
            for vid in row.get("sample_verse_ids") or []:
                if vid in occupied or vid in seen_vids:
                    continue
                candidates.append({"verse_id": vid, "motif_hit_count": 1})
                seen_vids.add(vid)
                if len(candidates) >= target_pool:
                    break
            if len(candidates) >= target_pool:
                break

    entries: list[dict[str, Any]] = []
    slot = start_slot + (wave - 1) * wave_size
    added = 0
    skipped_offset = 0
    candidate_offset = (wave - 1) * wave_size
    for cand in candidates:
        if added >= wave_size:
            break
        vid = str(cand.get("verse_id") or "")
        if not VERSE_RE.match(vid) or vid in occupied:
            continue
        if skipped_offset < candidate_offset:
            skipped_offset += 1
            continue
        hit = lookup_verse(vid)
        lemma = {}
        raw_preview = ""
        if hit:
            raw_preview = hit.get("raw") or hit.get("text_preview") or ""
            tokens = [t for t in raw_preview.split() if len(t) >= 4 and not t.isascii()]
            if tokens:
                lemma = {"greek": max(tokens, key=len)[:48]}
            elif raw_preview.split():
                tok = raw_preview.split()[0]
                lemma = {"greek": tok[:48]} if not tok.isascii() else {"greek": vid}
            else:
                lemma = {"greek": vid}
        stem = _stem_from_verse(vid)
        entries.append(
            {
                "slot_id": f"motif_{slot:03d}",
                "slot_num": slot,
                "status": "human_gate_proposed",
                "enabled": False,
                "tier": "tier1_canon_expansion",
                "wave": wave,
                "proposed_file_stem": stem,
                "proposed_anchor_id": f"cosmic_anchor_{stem}",
                "proposed_verse_refs": [vid],
                "motif_lemma": lemma,
                "motif_hit_count": cand.get("motif_hit_count"),
                "logos_summary_ko": f"코퍼스 확장 후보 — {vid} [wave{wave}]",
                "source": "corpus_expansion_pilot_v1",
                "nl_reference_only": True,
            }
        )
        slot += 1
        added += 1

    return {
        "schema": "logos_corpus_expansion_human_gate_queue_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "wave": wave,
        "wave_size": wave_size,
        "queue_count": len(entries),
        "merge_policy": "human_gate: commander ACCEPT → separate expansion merge (not Top100 SSOT overwrite)",
        "pilot_artifact": pilot_path.relative_to(ROOT).as_posix(),
        "entries": entries,
        "reproducible_command": "py scripts/build_logos_corpus_expansion_human_gate_queue_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=PILOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--wave", type=int, default=1)
    parser.add_argument("--wave-size", type=int, default=100)
    args = parser.parse_args()
    if not args.pilot.is_file():
        print(f"Missing pilot: {args.pilot}", file=sys.stderr)
        return 2
    doc = build_queue(
        pilot_path=args.pilot,
        registry_path=args.registry,
        wave=args.wave,
        wave_size=args.wave_size,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  wave={args.wave} proposed={doc['queue_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
