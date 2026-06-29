#!/usr/bin/env python3
"""Fact-Lock validate human_gate motif queue before merge.

Reproducible:
  py scripts/validate_logos_motif_human_gate_queue_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/final/artifacts/logos_motif_human_gate_queue_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_motif_human_gate_validation_v1_latest.json"

VERSE_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _slot_num(slot_id: str) -> int:
    return int(str(slot_id).split("_")[1])


def validate(queue_path: Path = QUEUE, registry_path: Path = REGISTRY) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    reg = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.is_file() else {}
    enabled_stems = {
        e.get("file_stem")
        for e in reg.get("entries", [])
        if e.get("enabled") and e.get("file_stem") and _slot_num(str(e.get("slot_id", ""))) <= 40
    }
    enabled_anchors = {
        e.get("anchor_id")
        for e in reg.get("entries", [])
        if e.get("enabled") and e.get("anchor_id") and _slot_num(str(e.get("slot_id", ""))) <= 40
    }
    errors: list[str] = []
    warnings: list[str] = []
    per_entry: list[dict[str, Any]] = []
    seen_stems: set[str] = set()
    seen_slots: set[str] = set()

    for entry in queue.get("entries", []):
        slot_id = str(entry.get("slot_id", ""))
        stem = str(entry.get("proposed_file_stem", ""))
        row_errors: list[str] = []
        row_warnings: list[str] = []

        if not slot_id.startswith("motif_"):
            row_errors.append("invalid slot_id")
        slot_num = entry.get("slot_num")
        if not isinstance(slot_num, int) or slot_num < 41 or slot_num > 100:
            row_errors.append("slot_num out of range 41..100")
        if slot_id in seen_slots:
            row_errors.append("duplicate slot_id")
        seen_slots.add(slot_id)

        if not stem:
            row_errors.append("missing proposed_file_stem")
        elif stem in seen_stems:
            row_errors.append("duplicate stem in queue")
        elif stem in enabled_stems:
            row_errors.append("stem conflict with enabled registry")
        seen_stems.add(stem)

        anchor_id = str(entry.get("proposed_anchor_id", ""))
        if anchor_id in enabled_anchors:
            row_errors.append("anchor_id conflict with enabled registry")

        lemma = entry.get("motif_lemma") or {}
        if not isinstance(lemma, dict) or not lemma:
            row_errors.append("missing motif_lemma")
        elif not (lemma.get("greek") or lemma.get("hebrew")):
            row_errors.append("lemma needs greek or hebrew")

        verses = entry.get("proposed_verse_refs") or []
        if not verses:
            row_errors.append("missing proposed_verse_refs")
        else:
            for v in verses:
                if not VERSE_RE.match(str(v)):
                    row_errors.append(f"invalid verse ref: {v}")

        if entry.get("conflict_with_enabled_stem"):
            row_errors.append("conflict_with_enabled_stem flag set")

        bias = entry.get("primitive_bias")
        if bias not in ("pathology", "survival"):
            row_errors.append("primitive_bias must be pathology|survival")

        if entry.get("verse_note"):
            row_warnings.append(f"verse_note: {entry['verse_note']}")

        per_entry.append(
            {
                "slot_id": slot_id,
                "proposed_file_stem": stem,
                "ok": not row_errors,
                "errors": row_errors,
                "warnings": row_warnings,
            }
        )
        errors.extend(f"{slot_id}: {e}" for e in row_errors)
        warnings.extend(f"{slot_id}: {w}" for w in row_warnings)

    ok_count = sum(1 for r in per_entry if r["ok"])
    report = {
        "schema": "logos_motif_human_gate_validation_v1",
        "generated_at_utc": generated_at_utc,
        "queue_path": queue_path.relative_to(ROOT).as_posix(),
        "registry_path": registry_path.relative_to(ROOT).as_posix() if registry_path.is_file() else None,
        "queue_count": len(per_entry),
        "ok_count": ok_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "pass": ok_count == len(per_entry) and len(per_entry) > 0,
        "errors": errors,
        "warnings": warnings,
        "per_entry": per_entry,
        "reproducible_command": "py scripts/validate_logos_motif_human_gate_queue_v1.py",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    report = validate(args.queue, args.registry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  pass={report['pass']} ok={report['ok_count']}/{report['queue_count']}")
    if report["errors"]:
        for e in report["errors"][:10]:
            print(f"  ERR: {e}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
