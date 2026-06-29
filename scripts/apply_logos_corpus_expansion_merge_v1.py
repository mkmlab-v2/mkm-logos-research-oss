#!/usr/bin/env python3
"""Apply corpus expansion wave queue → expansion extensions sidecar (slots 101+).

Does NOT overwrite logos_motif_human_gate_extensions_v1.json (Top100 SSOT).

Reproducible:
  py scripts/validate_logos_corpus_expansion_human_gate_queue_v1.py
  py scripts/apply_logos_corpus_expansion_merge_v1.py --hd-auto-wave 1
  py scripts/run_logos_corpus_expansion_wave_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/final/artifacts/logos_corpus_expansion_human_gate_queue_v1_latest.json"
VALIDATION = ROOT / "docs/final/artifacts/logos_corpus_expansion_validation_v1_latest.json"
APPROVAL = ROOT / "docs/final/artifacts/logos_corpus_expansion_approval_v1_latest.json"
EXPANSION = ROOT / "docs/final/artifacts/logos_corpus_expansion_extensions_v1.json"


def _lemma_text(entry: dict[str, Any]) -> str:
    lemma = entry.get("motif_lemma") or {}
    return str(lemma.get("greek") or lemma.get("hebrew") or "")


def _stem_from_verse(verse_id: str) -> str:
    return verse_id.replace(".", "_").lower()


def queue_to_spec(q: dict[str, Any]) -> dict[str, Any]:
    vid = str((q.get("proposed_verse_refs") or [""])[0])
    stem = _stem_from_verse(vid)
    text = _lemma_text(q)
    return {
        "slot_id": q["slot_id"],
        "file_stem": stem,
        "anchor_id": f"cosmic_anchor_{stem}",
        "verse_refs": [vid],
        "category": "canon_expansion",
        "tier": q.get("tier", "tier1_canon_expansion"),
        "wave": q.get("wave", 1),
        "motif_lemma": dict(q.get("motif_lemma") or {}),
        "gematria_text": text,
        "gematria_texts": {"raw": text, "compressed": text, "reconstructed": text},
        "logos_summary_ko": str(q.get("logos_summary_ko", "")),
        "sasang_summary_ko": f"코퍼스 확장 wave{q.get('wave', 1)}",
        "constitution_hint": "none",
        "ohaeng_hint": "none",
        "source": "corpus_expansion_wave_v1",
        "motif_hit_count": q.get("motif_hit_count"),
    }


def apply_wave(
    *,
    wave: int,
    queue_path: Path = QUEUE,
    expansion_path: Path = EXPANSION,
    approval_path: Path = APPROVAL,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    selected = [e for e in queue.get("entries", []) if e.get("wave") == wave]
    if not selected:
        raise SystemExit(f"No queue entries for wave {wave}")

    new_specs = [queue_to_spec(e) for e in selected]
    existing: dict[str, dict[str, Any]] = {}
    if expansion_path.is_file():
        prev = json.loads(expansion_path.read_text(encoding="utf-8"))
        for e in prev.get("entries", []):
            existing[e["slot_id"]] = e
    for spec in new_specs:
        existing[spec["slot_id"]] = spec

    waves_present = sorted({int(e.get("wave", 1)) for e in existing.values()})
    doc = {
        "schema": "logos_corpus_expansion_extensions_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "waves_present": waves_present,
        "wave_last": wave,
        "entry_count": len(existing),
        "entries": [existing[k] for k in sorted(existing.keys())],
        "reproducible_command": "py scripts/apply_logos_corpus_expansion_merge_v1.py",
    }
    expansion_path.parent.mkdir(parents=True, exist_ok=True)
    expansion_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    approval_path.write_text(
        json.dumps(
            {
                "schema": "logos_corpus_expansion_approval_v1",
                "generated_at_utc": generated_at_utc,
                "wave": wave,
                "approved_slot_ids": [s["slot_id"] for s in new_specs],
                "hd_auto": True,
                "expansion_path": expansion_path.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"approved": len(new_specs), "total": len(existing)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wave", type=int, default=1)
    parser.add_argument("--hd-auto-wave", type=int, default=0, help="Merge entire wave (e.g. 1)")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--run-chain", action="store_true")
    args = parser.parse_args()

    wave = args.hd_auto_wave or args.wave
    if not args.skip_validate:
        proc = subprocess.run(
            [sys.executable, "scripts/validate_logos_corpus_expansion_human_gate_queue_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    result = apply_wave(wave=wave)
    print(f"WROTE: {EXPANSION}")
    print(f"  wave={wave} approved={result['approved']} total={result['total']}")

    if args.run_chain:
        proc = subprocess.run(
            [sys.executable, "scripts/run_logos_corpus_expansion_wave_chain_v1.py", "--skip-merge"],
            cwd=ROOT,
            check=False,
        )
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
