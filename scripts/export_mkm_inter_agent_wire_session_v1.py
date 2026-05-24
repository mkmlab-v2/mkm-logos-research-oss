#!/usr/bin/env python3
"""M12: Export multi-turn wire-first session as JSONL + manifest (schema-validated envelopes)."""

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

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_export_v1_latest.json"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_export_v1_latest.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_session(
    *,
    scenario: str = "trading",
    turns: int = 4,
    routing_profile: str = "track_a_promoted",
    use_ko_health_sidecar: bool = False,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import (
        ALPHA_LINES_HEALTH,
        ALPHA_LINES_LEXICON_DENSE,
        ALPHA_LINES_TRADING,
        BETA_LINES_HEALTH,
        BETA_LINES_LEXICON_DENSE,
        BETA_LINES_TRADING,
    )
    from scripts.mkm_inter_agent_wire_envelope_v1 import envelope_utf8_byte_len, new_session_id
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1, send_turn_wire_v1
    from scripts.validate_mkm_inter_agent_wire_envelope_v1 import validate_doc

    if scenario == "health":
        alpha_lines, beta_lines = ALPHA_LINES_HEALTH, BETA_LINES_HEALTH
    elif scenario == "lexicon_dense":
        alpha_lines, beta_lines = ALPHA_LINES_LEXICON_DENSE, BETA_LINES_LEXICON_DENSE
    else:
        alpha_lines, beta_lines = ALPHA_LINES_TRADING, BETA_LINES_TRADING

    client = TestClient(app)
    session_id = new_session_id(f"export-{scenario}")
    envelopes: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    all_ok = True
    last_envelope: dict[str, Any] | None = None

    for turn in range(1, turns + 1):
        is_alpha = turn % 2 == 1
        from_agent = "agent_alpha_prophecy" if is_alpha else "agent_beta_executor"
        to_agent = "agent_beta_executor" if is_alpha else "agent_alpha_prophecy"
        line_idx = (turn - 1) // 2
        internal = (
            alpha_lines[min(line_idx, len(alpha_lines) - 1)]
            if is_alpha
            else beta_lines[min(line_idx, len(beta_lines) - 1)]
        )

        if last_envelope is not None:
            recv = receive_turn_wire_v1(client, last_envelope)
            all_ok = all_ok and bool(recv.get("ok"))

        sent = send_turn_wire_v1(
            client,
            text=internal,
            session_id=session_id,
            turn_id=turn,
            from_agent=from_agent,
            to_agent=to_agent,
            routing_profile=routing_profile,
            use_ko_health_sidecar=use_ko_health_sidecar,
        )
        all_ok = all_ok and bool(sent.get("ok"))
        envelope = sent.get("envelope") or {}
        try:
            validations.append({"turn": turn, **validate_doc(envelope)})
        except Exception as exc:
            validations.append({"turn": turn, "ok": False, "error": f"{type(exc).__name__}:{exc}"})
            all_ok = False

        envelopes.append(
            {
                "record_kind": "wire_envelope",
                "turn": turn,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "plaintext_char_len": len(internal),
                "envelope_utf8_byte_len": envelope_utf8_byte_len(envelope),
                "envelope": envelope,
            }
        )
        last_envelope = envelope

    return {
        "ok": all_ok and all(v.get("ok") for v in validations),
        "schema": "mkm_inter_agent_wire_session_export_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "session_id": session_id,
        "scenario": scenario,
        "turns": turns,
        "routing_profile": routing_profile,
        "use_ko_health_sidecar": use_ko_health_sidecar,
        "envelope_count": len(envelopes),
        "all_envelopes_schema_valid": all(v.get("ok") for v in validations),
        "validations": validations,
        "envelopes": envelopes,
        "boundary_ack": "Session export for B-track replay; not production A2A bus.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", choices=("trading", "health", "lexicon_dense"), default="trading")
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    args = ap.parse_args()

    doc = export_session(scenario=args.scenario, turns=max(2, args.turns))
    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.jsonl.open("w", encoding="utf-8") as fh:
        for row in doc.get("envelopes") or []:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {k: v for k, v in doc.items() if k != "envelopes"}
    manifest["envelopes_jsonl"] = args.jsonl.relative_to(ROOT).as_posix()
    manifest["total_envelope_utf8_bytes"] = sum(
        int(r.get("envelope_utf8_byte_len") or 0) for r in doc.get("envelopes") or []
    )

    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": manifest.get("ok"), "manifest": str(args.manifest_json), "jsonl": str(args.jsonl)}, ensure_ascii=False))
    return 0 if manifest.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
