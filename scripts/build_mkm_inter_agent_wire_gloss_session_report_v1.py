#!/usr/bin/env python3
"""M15b: Wire session turns + lexicon gloss decode (human replay report, research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_session_report_v1_latest.json"
DEFAULT_BATCH = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gloss_for_envelope(envelope: dict[str, Any], codebook_path: Path) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import gloss_rows_for_atom_ids

    payload = envelope.get("payload") or {}
    atom_ids = payload.get("atom_id_sequence") or []
    gloss_rows, meta = gloss_rows_for_atom_ids(atom_ids, codebook_path)
    gloss_text = " ".join(r["gloss"] for r in gloss_rows if r.get("gloss"))
    return {
        "atom_id_count": len(atom_ids),
        "gloss_text": gloss_text,
        "gloss_rows": gloss_rows,
        "gloss_meta": meta,
        "empty_lexicon_turn": len(atom_ids) == 0,
    }


def build_report(
    *,
    batch_manifest_path: Path = DEFAULT_BATCH,
    turns: int = 4,
    run_batch_if_missing: bool = True,
) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

    codebook = resolve_latest_codebook_path()
    if codebook is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    batch = None
    if batch_manifest_path.is_file():
        batch = json.loads(batch_manifest_path.read_text(encoding="utf-8"))
    elif run_batch_if_missing:
        from scripts.export_mkm_inter_agent_wire_sessions_batch_v1 import export_batch

        batch = export_batch(turns=turns)
        batch_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        batch_manifest_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        return {"ok": False, "error": "batch_manifest_missing"}

    if not batch or not batch.get("ok"):
        return {"ok": False, "error": "batch_not_ok"}

    combined_path = ROOT / str(batch.get("combined_jsonl") or "")
    if not combined_path.is_file():
        return {"ok": False, "error": "combined_jsonl_missing"}

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    raw_lines = [ln for ln in combined_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not raw_lines:
        return {"ok": False, "error": "combined_jsonl_empty", "combined_jsonl": batch.get("combined_jsonl")}

    for line in raw_lines:
        if not line.strip():
            continue
        row = json.loads(line)
        scenario = str(row.get("scenario") or "unknown")
        envelope = row.get("envelope") or {}
        gloss = _gloss_for_envelope(envelope, codebook)
        by_scenario.setdefault(scenario, []).append(
            {
                "turn": row.get("turn"),
                "from_agent": row.get("from_agent"),
                "to_agent": row.get("to_agent"),
                "plaintext_char_len": row.get("plaintext_char_len"),
                "envelope_utf8_byte_len": row.get("envelope_utf8_byte_len"),
                "wire_byte_len": (envelope.get("payload") or {}).get("wire_byte_len"),
                **gloss,
            }
        )

    scenario_summary: dict[str, Any] = {}
    for scenario, turns_rows in by_scenario.items():
        atom_counts = [int(t.get("atom_id_count") or 0) for t in turns_rows]
        scenario_summary[scenario] = {
            "turn_count": len(turns_rows),
            "avg_atom_id_count": round(sum(atom_counts) / len(atom_counts), 4) if atom_counts else 0,
            "empty_turn_count": sum(1 for t in turns_rows if t.get("empty_lexicon_turn")),
            "gloss_preview_turn_1": (turns_rows[0].get("gloss_text") or "")[:160] if turns_rows else "",
        }

    return {
        "ok": True,
        "schema": "mkm_inter_agent_wire_gloss_session_report_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "batch_manifest": batch_manifest_path.relative_to(ROOT).as_posix(),
        "combined_jsonl": batch.get("combined_jsonl"),
        "scenario_summary": scenario_summary,
        "turns_by_scenario": by_scenario,
        "boundary_ack": (
            "Gloss lookup on wire atom_id_sequence; complements L1 inverse decoder (~58% exact). "
            "Not lossless human translation."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--batch-manifest", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--no-run-batch", action="store_true")
    args = ap.parse_args()

    doc = build_report(
        batch_manifest_path=args.batch_manifest,
        turns=max(2, args.turns),
        run_batch_if_missing=not args.no_run_batch,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
