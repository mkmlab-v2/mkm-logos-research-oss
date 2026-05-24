#!/usr/bin/env python3
"""M20: Batch export (health sidecar) → JSONL audit → replay API (parallel-safe chain)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_batch_chain_v1_latest.json"
HEALTH_JSONL = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_health_sidecar_v1_latest.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_chain(*, turns: int = 4) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.audit_mkm_inter_agent_wire_session_jsonl_roundtrip_v1 import audit_jsonl
    from scripts.compression_token_api_v2_stub import app
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session
    from scripts.mkm_inter_agent_wire_replay_v1 import replay_jsonl_envelopes

    health = export_session(scenario="health", turns=turns, use_ko_health_sidecar=True)
    HEALTH_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with HEALTH_JSONL.open("w", encoding="utf-8") as fh:
        for row in health.get("envelopes") or []:
            line = {**row, "scenario": "health", "session_id": health.get("session_id"), "use_ko_health_sidecar": True}
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    audit = audit_jsonl(HEALTH_JSONL, run_batch_if_missing=False, min_lines=max(1, turns))
    replay_local = replay_jsonl_envelopes(HEALTH_JSONL)

    client = TestClient(app)
    api_replay = client.post(
        "/v1/research/mkm_inter_agent_wire/replay",
        json={"scenario": "health", "turns": turns, "use_ko_health_sidecar": True},
    )
    api_body = api_replay.json() if api_replay.status_code == 200 else {}

    avg_atoms = 0.0
    envs = health.get("envelopes") or []
    if envs:
        avg_atoms = sum(
            len((r.get("envelope") or {}).get("payload", {}).get("atom_id_sequence") or []) for r in envs
        ) / len(envs)

    ok = (
        bool(health.get("ok"))
        and bool(audit.get("ok"))
        and bool(replay_local.get("ok"))
        and api_replay.status_code == 200
        and bool(api_body.get("turn_count", 0) >= turns)
        and avg_atoms > 1.0
    )

    return {
        "ok": ok,
        "schema": "mkm_inter_agent_ko_health_sidecar_batch_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "health_jsonl": HEALTH_JSONL.relative_to(ROOT).as_posix(),
        "health_export": {
            "session_id": health.get("session_id"),
            "envelope_count": health.get("envelope_count"),
            "avg_atom_id_count": round(avg_atoms, 2),
        },
        "jsonl_audit": {
            "ok": audit.get("ok"),
            "line_count": audit.get("line_count"),
            "all_schema_valid": audit.get("all_schema_valid"),
        },
        "replay_jsonl": {"ok": replay_local.get("ok"), "turn_count": replay_local.get("turn_count")},
        "replay_api": {
            "status_code": api_replay.status_code,
            "turn_count": api_body.get("turn_count"),
            "ok": api_replay.status_code == 200,
        },
        "boundary_ack": "Health-only sidecar batch chain; not production default wire path.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_chain(turns=max(2, args.turns))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
