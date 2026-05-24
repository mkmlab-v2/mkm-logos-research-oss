#!/usr/bin/env python3
"""M17b: Audit batch session JSONL — schema + wire decode round-trip per envelope."""

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

DEFAULT_JSONL = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_jsonl_roundtrip_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def audit_jsonl(
    jsonl_path: Path,
    *,
    run_batch_if_missing: bool = True,
    min_lines: int = 6,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1
    from scripts.validate_mkm_inter_agent_wire_envelope_v1 import validate_doc

    jsonl_path = jsonl_path.resolve()

    def _line_count(path: Path) -> int:
        return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())

    line_count = _line_count(jsonl_path) if jsonl_path.is_file() else 0
    need_batch = False
    if not jsonl_path.is_file() or line_count == 0:
        need_batch = run_batch_if_missing
    elif line_count < max(1, min_lines):
        need_batch = run_batch_if_missing
    if need_batch:
        if not run_batch_if_missing:
            return {"ok": False, "error": "jsonl_missing_or_incomplete", "path": str(jsonl_path)}
        from scripts.export_mkm_inter_agent_wire_sessions_batch_v1 import export_batch

        batch = export_batch(turns=4)
        if not batch.get("ok"):
            return {"ok": False, "error": "batch_export_failed"}
        jsonl_path = (ROOT / str(batch.get("combined_jsonl") or "")).resolve()
    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    all_ok = True
    by_scenario: dict[str, dict[str, int]] = {}

    for line_no, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        scenario = str(row.get("scenario") or "unknown")
        envelope = row.get("envelope") or {}
        schema_ok = True
        schema_err = None
        try:
            validate_doc(envelope)
        except Exception as exc:
            schema_ok = False
            schema_err = f"{type(exc).__name__}:{exc}"
            all_ok = False

        recv = receive_turn_wire_v1(client, envelope)
        wire_ok = bool(recv.get("ok"))
        empty_turn = bool(recv.get("empty_lexicon_turn"))
        if not wire_ok and not empty_turn:
            all_ok = False

        payload = envelope.get("payload") or {}
        enc_ids = list(payload.get("atom_id_sequence") or [])
        dec_ids = list((recv.get("decode") or {}).get("atom_id_sequence") or [])

        entry = {
            "line_no": line_no,
            "scenario": scenario,
            "turn": row.get("turn"),
            "session_id": row.get("session_id"),
            "schema_valid": schema_ok,
            "schema_error": schema_err,
            "wire_roundtrip_ok": wire_ok,
            "empty_lexicon_turn": empty_turn,
            "atom_id_count": len(enc_ids),
            "encode_decode_atom_match": enc_ids == dec_ids,
        }
        rows.append(entry)

        agg = by_scenario.setdefault(
            scenario,
            {"lines": 0, "schema_pass": 0, "wire_pass": 0, "empty_turns": 0},
        )
        agg["lines"] += 1
        if schema_ok:
            agg["schema_pass"] += 1
        if wire_ok:
            agg["wire_pass"] += 1
        if empty_turn:
            agg["empty_turns"] += 1

    return {
        "ok": all_ok and len(rows) > 0,
        "schema": "mkm_inter_agent_wire_session_jsonl_roundtrip_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source_jsonl": jsonl_path.relative_to(ROOT).as_posix(),
        "line_count": len(rows),
        "all_schema_valid": all(r["schema_valid"] for r in rows),
        "all_wire_roundtrip_ok": all(r["wire_roundtrip_ok"] for r in rows),
        "by_scenario": by_scenario,
        "rows": rows,
        "boundary_ack": "JSONL replay audit; empty_lexicon_turn is valid for low-hit KO health lines.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-run-batch", action="store_true")
    args = ap.parse_args()
    doc = audit_jsonl(args.jsonl, run_batch_if_missing=not args.no_run_batch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
