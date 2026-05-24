#!/usr/bin/env python3
"""M16b: Replay wire envelopes → gloss rows (shared by API route and CLI)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def replay_envelopes(envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        gloss_rows_for_atom_ids,
        resolve_latest_codebook_path,
    )
    from scripts.mkm_inter_agent_wire_envelope_v1 import envelope_utf8_byte_len
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1

    codebook = resolve_latest_codebook_path()
    if codebook is None:
        return {"ok": False, "error": "lexicon_path_missing", "turns": []}

    turns_out: list[dict[str, Any]] = []
    all_ok = True
    test_client = None
    for idx, envelope in enumerate(envelopes, start=1):
        payload = envelope.get("payload") or {}
        atom_ids = payload.get("atom_id_sequence") or []
        gloss_rows, gloss_meta = gloss_rows_for_atom_ids(atom_ids, codebook)
        gloss_text = " ".join(r["gloss"] for r in gloss_rows if r.get("gloss"))
        decode_ok = True
        if payload.get("wire_b64"):
            if test_client is None:
                from fastapi.testclient import TestClient

                from scripts.compression_token_api_v2_stub import app

                test_client = TestClient(app)
            recv = receive_turn_wire_v1(test_client, envelope)
            decode_ok = bool(recv.get("ok"))
            all_ok = all_ok and decode_ok

        turns_out.append(
            {
                "index": idx,
                "turn_id": envelope.get("turn_id"),
                "session_id": envelope.get("session_id"),
                "from_agent": envelope.get("from_agent"),
                "to_agent": envelope.get("to_agent"),
                "envelope_utf8_byte_len": envelope_utf8_byte_len(envelope),
                "wire_byte_len": payload.get("wire_byte_len"),
                "atom_id_count": len(atom_ids),
                "gloss_text": gloss_text,
                "gloss_rows": gloss_rows,
                "wire_roundtrip_ok": decode_ok,
                "empty_lexicon_turn": len(atom_ids) == 0,
                "gloss_meta_status": gloss_meta.get("status"),
            }
        )

    return {
        "ok": all_ok and len(turns_out) > 0,
        "schema": "mkm_inter_agent_wire_replay_v1",
        "turn_count": len(turns_out),
        "turns": turns_out,
        "research_only": True,
        "integrity_flags": {"research_only": True, "replay": "gloss_plus_optional_wire_decode"},
    }


def replay_jsonl_envelopes(jsonl_path: Path) -> dict[str, Any]:
    import json

    envelopes: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        env = row.get("envelope")
        if isinstance(env, dict):
            envelopes.append(env)
    out = replay_envelopes(envelopes)
    out["source_jsonl"] = str(jsonl_path)
    out["line_count"] = len(envelopes)
    return out


def replay_scenario_demo(
    *,
    scenario: str = "trading",
    turns: int = 4,
    use_ko_health_sidecar: bool = False,
) -> dict[str, Any]:
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session

    session = export_session(scenario=scenario, turns=turns, use_ko_health_sidecar=use_ko_health_sidecar)
    if not session.get("ok"):
        return {"ok": False, "error": "session_export_failed", "scenario": scenario}
    envelopes = [r.get("envelope") or {} for r in session.get("envelopes") or []]
    out = replay_envelopes(envelopes)
    out["scenario"] = scenario
    out["session_id"] = session.get("session_id")
    out["use_ko_health_sidecar"] = use_ko_health_sidecar
    return out
