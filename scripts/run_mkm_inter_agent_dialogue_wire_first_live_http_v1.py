#!/usr/bin/env python3
"""M13: Wire-first dialogue over real HTTP (env base URL or ephemeral uvicorn)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_live_http_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_live_dialogue(
    *,
    base_url: str,
    turns: int = 2,
    scenario: str = "trading",
    use_ko_health_sidecar: bool = False,
) -> dict[str, Any]:
    from scripts.mkm_inter_agent_http_client_v1 import MkmCompressionHttpClient
    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import (
        ALPHA_LINES_HEALTH,
        ALPHA_LINES_TRADING,
        BETA_LINES_HEALTH,
        BETA_LINES_TRADING,
    )
    from scripts.mkm_inter_agent_wire_envelope_v1 import envelope_utf8_byte_len, new_session_id
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1, send_turn_wire_v1

    if scenario == "health":
        alpha_lines, beta_lines = ALPHA_LINES_HEALTH, BETA_LINES_HEALTH
    else:
        alpha_lines, beta_lines = ALPHA_LINES_TRADING, BETA_LINES_TRADING
    sidecar_on = use_ko_health_sidecar and scenario == "health"
    client = MkmCompressionHttpClient(base_url)
    health = client.get("/health")
    if health.status_code != 200:
        return {"ok": False, "error": f"health_status_{health.status_code}", "base_url": base_url}

    session_id = new_session_id(f"live-http-{scenario}")
    transcript: list[dict[str, Any]] = []
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

        recv_row = None
        if last_envelope is not None:
            recv_row = receive_turn_wire_v1(client, last_envelope)
            all_ok = all_ok and bool(recv_row.get("ok"))

        sent = send_turn_wire_v1(
            client,
            text=internal,
            session_id=session_id,
            turn_id=turn,
            from_agent=from_agent,
            to_agent=to_agent,
            use_ko_health_sidecar=sidecar_on,
        )
        all_ok = all_ok and bool(sent.get("ok"))
        envelope = sent.get("envelope") or {}
        transcript.append(
            {
                "turn": turn,
                "wire_envelope_bytes": envelope_utf8_byte_len(envelope),
                "receive_prior": recv_row,
                "send_ok": sent.get("ok"),
                "atom_id_count": (envelope.get("payload") or {}).get("atom_id_count"),
            }
        )
        last_envelope = envelope

    turn_body: dict[str, Any] = {"text": alpha_lines[0], "session_id": session_id, "turn_id": turns + 1}
    if sidecar_on:
        turn_body["use_ko_health_sidecar"] = True
    turn_ep = client.post("/v1/research/mkm_inter_agent_wire/turn", json=turn_body)
    turn_ok = turn_ep.status_code == 200
    all_ok = all_ok and turn_ok

    return {
        "ok": all_ok,
        "schema": "mkm_inter_agent_dialogue_wire_first_live_http_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "capture_mode": "real_http",
        "base_url": base_url,
        "session_id": session_id,
        "scenario": scenario,
        "use_ko_health_sidecar": sidecar_on,
        "turns": turns,
        "transcript": transcript,
        "wire_turn_endpoint_ok": turn_ok,
        "boundary_ack": "Live HTTP research capture; not production SLA.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=2)
    ap.add_argument("--scenario", choices=("trading", "health", "lexicon_dense"), default="trading")
    ap.add_argument("--base-url", type=str, default="", help="Override MKM_*_HTTP_BASE_URL env")
    ap.add_argument("--ephemeral", action="store_true", help="Spin local uvicorn (default if no base URL)")
    ap.add_argument("--use-ko-health-sidecar", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    from scripts.mkm_inter_agent_http_client_v1 import ephemeral_compression_api_server, resolve_inter_agent_http_base_url

    base = (args.base_url or "").strip() or resolve_inter_agent_http_base_url()
    if base:
        doc = run_live_dialogue(
            base_url=base,
            turns=max(2, args.turns),
            scenario=args.scenario,
            use_ko_health_sidecar=args.use_ko_health_sidecar,
        )
    elif args.ephemeral or not base:
        with ephemeral_compression_api_server() as ephemeral_base:
            doc = run_live_dialogue(
                base_url=ephemeral_base,
                turns=max(2, args.turns),
                scenario=args.scenario,
                use_ko_health_sidecar=args.use_ko_health_sidecar,
            )
            doc["capture_mode"] = "ephemeral_uvicorn_http"
    else:
        doc = {"ok": False, "error": "no_base_url"}

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
