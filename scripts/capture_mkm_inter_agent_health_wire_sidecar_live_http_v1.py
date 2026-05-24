#!/usr/bin/env python3
"""M23: Live HTTP health wire-first with [HYPO] KO health sidecar (ephemeral uvicorn)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_live_http_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capture(*, turns: int = 2) -> dict[str, Any]:
    from scripts.mkm_inter_agent_http_client_v1 import ephemeral_compression_api_server
    from scripts.run_mkm_inter_agent_dialogue_wire_first_live_http_v1 import run_live_dialogue

    with ephemeral_compression_api_server() as base:
        doc = run_live_dialogue(
            base_url=base,
            turns=turns,
            scenario="health",
            use_ko_health_sidecar=True,
        )
    tr = doc.get("transcript") or []
    avg_atoms = (
        sum(int(t.get("atom_id_count") or 0) for t in tr) / len(tr) if tr else 0.0
    )
    ok = bool(doc.get("ok")) and bool(doc.get("wire_turn_endpoint_ok")) and avg_atoms > 1.0
    return {
        "ok": ok,
        "schema": "mkm_inter_agent_health_wire_sidecar_live_http_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "capture_mode": doc.get("capture_mode"),
        "avg_atom_id_count": round(avg_atoms, 2),
        "wire_turn_endpoint_ok": doc.get("wire_turn_endpoint_ok"),
        "session_id": doc.get("session_id"),
        "boundary_ack": "Real HTTP over ephemeral server; not production SLA or Track A.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=2)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = capture(turns=max(2, args.turns))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
