"""
Build a single-page MASTER_PROBE JSON from B-track 16-state audit JSONL.

Use: inject into NotebookLM / AI context instead of scanning many sources.
Does not call verse/regime pipelines (Logos-first separation preserved).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Reuse experiment line validation for base record shape
from myeongni_16_state_experiment_ledger import validate_experiment_record, _workspace_root

MASTER_PROBE_VERSION = "1"
DEFAULT_NEUTRAL_4D = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}

AUDIT_CONTRACT_B17: dict[str, Any] = {
    "layers": ["Provenance", "Integrity", "Evidence"],
    "fields": {
        "schema_version": "Audit bundle version (e.g. B-17_v1).",
        "source_work": "Pointer to corpus/manifest row or work id.",
        "chunk_id": "NotebookLM or chunk id for replay.",
        "line_start": "Inclusive line in source chunk (integer).",
        "line_end": "Inclusive line in source chunk (integer).",
        "sha256": "Content hash for integrity replay.",
        "rules_version": "Schema or constitution ref used when stamping.",
        "expected_parent": "Hypothesis tier / parent slot (P1–P3 etc.).",
        "confidence_score": "0..1 confidence in this state's audit stamp.",
        "edition_or_url": "Human-readable edition or URL (verify before production).",
        "license_note": "Licensing or research-only note.",
    },
    "meaning": {
        "Provenance": "Where the claim came from (traceable source_work + chunk).",
        "Integrity": "Tamper-evident binding (sha256, line range, rules_version).",
        "Evidence": "What supports the coordinate (confidence, expected_parent).",
    },
}


def _load_audit_jsonl(path: Path) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for i, raw in enumerate(text.splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"line {i}: must be JSON object")
        errs = validate_experiment_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        lines.append(obj)
    return lines


def _state_slot_from_record(rec: dict[str, Any]) -> dict[str, Any]:
    sid = rec.get("state_id")
    if sid is None:
        return {}
    slot: dict[str, Any] = {
        "state_id": sid,
        "mapping_target": rec.get("mapping_target"),
        "vector_4d": rec.get("vector_4d") or dict(DEFAULT_NEUTRAL_4D),
        "coverage": "audited",
    }
    if rec.get("consistency_rate") is not None:
        slot["consistency_rate"] = rec["consistency_rate"]
    if rec.get("self_contradiction_rate") is not None:
        slot["self_contradiction_rate"] = rec["self_contradiction_rate"]
    if rec.get("run_id") is not None:
        slot["run_id"] = rec["run_id"]
    if rec.get("conversation_id") is not None:
        slot["conversation_id"] = rec["conversation_id"]
    if isinstance(rec.get("audit"), dict):
        slot["audit"] = rec["audit"]
    return slot


def build_master_probe(
    audit_lines: list[dict[str, Any]],
    *,
    source_path: str,
) -> dict[str, Any]:
    """Merge audit lines into 16 slots; last line wins per state_id."""
    by_state: dict[int, dict[str, Any]] = {}
    for rec in audit_lines:
        sid = rec.get("state_id")
        if isinstance(sid, int) and 1 <= sid <= 16:
            by_state[sid] = _state_slot_from_record(rec)

    states: list[dict[str, Any]] = []
    for sid in range(1, 17):
        if sid in by_state:
            states.append(by_state[sid])
        else:
            states.append(
                {
                    "state_id": sid,
                    "coverage": "missing",
                    "vector_4d": dict(DEFAULT_NEUTRAL_4D),
                    "mapping_target": None,
                    "note": "No audit line yet; placeholder until JSONL includes this state_id.",
                }
            )

    audited_ids = sorted(by_state.keys())
    return {
        "master_probe_version": MASTER_PROBE_VERSION,
        "kind": "16_STATE_MASTER_PROBE",
        "title": "B-track 16-state coordinate + B-17 audit contract (single-page)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_audit_path": source_path,
        "source_line_count": len(audit_lines),
        "coverage_summary": {
            "states_with_audit": len(audited_ids),
            "state_ids_present": audited_ids,
            "states_total": 16,
        },
        "coordinate_system": {
            "state_dimension": 16,
            "vector_axes": ["S", "L", "K", "M"],
            "mapping_target_enum": ["bull", "bear", "sideways"],
            "divine_centroid_reference": "measurement anchor 0.25 per axis; observations may deviate (workspace IC).",
        },
        "audit_contract": AUDIT_CONTRACT_B17,
        "states": states,
        "usage": {
            "inject_as": "Single JSON context for NotebookLM or local RAG; not a trading trigger.",
            "boundary": "B-track hypothesis only; verse/Logos and production ledger stay separate until promoted.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate 16_STATE_MASTER_PROBE JSON from audit JSONL")
    p.add_argument(
        "--audit-path",
        type=Path,
        required=True,
        help="Path to myeongni_16_state_audit_v1.jsonl (or compatible experiment JSONL)",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON path (e.g. data/myeongni/16_STATE_MASTER_PROBE_v1.json)",
    )
    args = p.parse_args(argv)
    root = _workspace_root()
    audit_path = args.audit_path if args.audit_path.is_absolute() else (root / args.audit_path)
    out_path = args.output if args.output.is_absolute() else (root / args.output)

    if not audit_path.is_file():
        print(f"not found: {audit_path}", file=sys.stderr)
        return 2

    try:
        lines = _load_audit_jsonl(audit_path)
    except (json.JSONDecodeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        src_display = str(audit_path.relative_to(root))
    except ValueError:
        src_display = str(audit_path)
    probe = build_master_probe(lines, source_path=src_display)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(lines)} audit line(s), 16 state slots)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
