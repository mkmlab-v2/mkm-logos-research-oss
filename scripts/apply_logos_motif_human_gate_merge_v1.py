#!/usr/bin/env python3
"""Apply approved human_gate queue slots → registry extensions sidecar.

Does NOT edit PREFILLED inline — writes extensions JSON consumed by
build_logos_motif_registry_top100_v1.py.

Reproducible:
  py scripts/validate_logos_motif_human_gate_queue_v1.py
  py scripts/apply_logos_motif_human_gate_merge_v1.py --hd-auto-all
  py scripts/run_logos_spread_tuning_chain_v1.py
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
QUEUE = ROOT / "docs/final/artifacts/logos_motif_human_gate_queue_v1_latest.json"
VALIDATION = ROOT / "docs/final/artifacts/logos_motif_human_gate_validation_v1_latest.json"
APPROVAL = ROOT / "docs/final/artifacts/logos_motif_human_gate_approval_v1_latest.json"
EXTENSIONS = ROOT / "docs/final/artifacts/logos_motif_human_gate_extensions_v1.json"


def _gematria_text(entry: dict[str, Any]) -> str:
    lemma = entry.get("motif_lemma") or {}
    return str(lemma.get("greek") or lemma.get("hebrew") or entry.get("proposed_file_stem", ""))


def queue_entry_to_registry_spec(q: dict[str, Any]) -> dict[str, Any]:
    text = _gematria_text(q)
    bias = str(q.get("primitive_bias", "pathology"))
    summary = str(q.get("logos_summary_ko", "")).replace(" human_gate candidate", "")
    return {
        "slot_id": q["slot_id"],
        "file_stem": q["proposed_file_stem"],
        "anchor_id": q["proposed_anchor_id"],
        "verse_refs": list(q.get("proposed_verse_refs") or []),
        "category": bias,
        "primitive_bias": bias,
        "motif_lemma": dict(q.get("motif_lemma") or {}),
        "gematria_text": text,
        "gematria_texts": {
            "raw": text,
            "compressed": text,
            "reconstructed": text,
        },
        "logos_summary_ko": summary,
        "sasang_summary_ko": f"{bias} motif — human_gate_wave26",
        "constitution_hint": "none",
        "ohaeng_hint": "fire" if bias == "pathology" else "water",
        "source": "human_gate_queue_v1_merged",
    }


def load_queue(path: Path = QUEUE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_slots(
    queue: dict[str, Any],
    *,
    slot_ids: list[str] | None,
    wave: int | None,
    hd_auto_all: bool,
) -> list[str]:
    all_ids = [e["slot_id"] for e in queue.get("entries", [])]
    if hd_auto_all:
        return all_ids
    if slot_ids:
        return slot_ids
    if wave is not None:
        start = 41 + (wave - 1) * 10
        end = min(start + 9, 100)
        return [f"motif_{n:03d}" for n in range(start, end + 1)]
    raise ValueError("Specify --slots, --wave N, or --hd-auto-all")


def apply_merge(
    *,
    slot_ids: list[str],
    queue_path: Path = QUEUE,
    extensions_path: Path = EXTENSIONS,
    approval_path: Path = APPROVAL,
    merge_mode: str = "replace",
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue = load_queue(queue_path)
    by_slot = {e["slot_id"]: e for e in queue.get("entries", [])}
    missing = [s for s in slot_ids if s not in by_slot]
    if missing:
        raise SystemExit(f"Missing queue slots: {missing}")

    new_specs = [queue_entry_to_registry_spec(by_slot[s]) for s in slot_ids]
    existing: dict[str, dict[str, Any]] = {}
    if merge_mode == "append" and extensions_path.is_file():
        prev = json.loads(extensions_path.read_text(encoding="utf-8"))
        for e in prev.get("entries", []):
            existing[e["slot_id"]] = e
    for spec in new_specs:
        existing[spec["slot_id"]] = spec

    extensions_doc = {
        "schema": "logos_motif_human_gate_extensions_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "entry_count": len(existing),
        "entries": [existing[k] for k in sorted(existing.keys())],
        "reproducible_command": "py scripts/apply_logos_motif_human_gate_merge_v1.py",
    }
    extensions_path.parent.mkdir(parents=True, exist_ok=True)
    extensions_path.write_text(
        json.dumps(extensions_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    approval_doc = {
        "schema": "logos_motif_human_gate_approval_v1",
        "generated_at_utc": generated_at_utc,
        "approved_slot_ids": slot_ids,
        "approval_mode": merge_mode,
        "hd_auto": True,
        "human_gate_note": "agent_staged_hd_m — Fact-Lock validate pass required",
        "extensions_path": extensions_path.relative_to(ROOT).as_posix(),
        "total_enabled_after_registry_build": 40 + len(existing),
    }
    approval_path.write_text(
        json.dumps(approval_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "extensions_path": str(extensions_path),
        "approved_count": len(slot_ids),
        "total_extensions": len(existing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--extensions", type=Path, default=EXTENSIONS)
    parser.add_argument("--approval", type=Path, default=APPROVAL)
    parser.add_argument("--slots", type=str, default="", help="Comma-separated motif_041,...")
    parser.add_argument("--wave", type=int, default=0, help="Wave 1=041-050, ... wave 6=091-100")
    parser.add_argument("--hd-auto-all", action="store_true", help="Merge all 60 queue slots")
    parser.add_argument("--merge-mode", choices=("replace", "append"), default="replace")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--run-chain", action="store_true")
    args = parser.parse_args()

    if not args.skip_validate:
        proc = subprocess.run(
            [sys.executable, "scripts/validate_logos_motif_human_gate_queue_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("FAIL: validation", file=sys.stderr)
            return proc.returncode
        val = json.loads(VALIDATION.read_text(encoding="utf-8"))
        if not val.get("pass"):
            print("FAIL: validation report pass=false", file=sys.stderr)
            return 1

    slot_ids = select_slots(
        load_queue(args.queue),
        slot_ids=[s.strip() for s in args.slots.split(",") if s.strip()] or None,
        wave=args.wave if args.wave > 0 else None,
        hd_auto_all=args.hd_auto_all,
    )

    result = apply_merge(
        slot_ids=slot_ids,
        queue_path=args.queue,
        extensions_path=args.extensions,
        approval_path=args.approval,
        merge_mode=args.merge_mode,
    )
    print(f"WROTE: {args.extensions}")
    print(f"  approved={result['approved_count']} total_extensions={result['total_extensions']}")

    if args.run_chain:
        proc = subprocess.run(
            [sys.executable, "scripts/run_logos_spread_tuning_chain_v1.py"],
            cwd=ROOT,
            check=False,
        )
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
