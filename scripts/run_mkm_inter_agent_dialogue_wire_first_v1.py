#!/usr/bin/env python3
"""A2A wire-first dialogue: on-wire payload = wire envelope v1 (not full Trust Packet)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_latest.json"

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import (  # noqa: E402
    ALPHA_LINES_HEALTH,
    ALPHA_LINES_LEXICON_DENSE,
    ALPHA_LINES_TRADING,
    BETA_LINES_HEALTH,
    BETA_LINES_LEXICON_DENSE,
    BETA_LINES_TRADING,
)
from scripts.mkm_inter_agent_wire_envelope_v1 import (  # noqa: E402
    envelope_utf8_byte_len,
    new_session_id,
)
from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import (  # noqa: E402
    receive_turn_wire_v1,
    send_turn_wire_v1,
)


def run_dialogue(
    *,
    turns: int = 4,
    scenario: str = "trading",
    routing_profile: str = "track_a_promoted",
    use_ko_health_sidecar: bool = False,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    if scenario == "health":
        alpha_lines, beta_lines = ALPHA_LINES_HEALTH, BETA_LINES_HEALTH
    elif scenario == "lexicon_dense":
        alpha_lines, beta_lines = ALPHA_LINES_LEXICON_DENSE, BETA_LINES_LEXICON_DENSE
    else:
        alpha_lines, beta_lines = ALPHA_LINES_TRADING, BETA_LINES_TRADING

    sidecar_on = use_ko_health_sidecar and scenario == "health"

    client = TestClient(app)
    session_id = new_session_id(f"wire-{scenario}")
    transcript: list[dict[str, Any]] = []
    last_envelope: dict[str, Any] | None = None
    all_ok = True
    savings: list[float] = []

    for turn in range(1, turns + 1):
        is_alpha = turn % 2 == 1
        from_agent = "agent_alpha_prophecy" if is_alpha else "agent_beta_executor"
        to_agent = "agent_beta_executor" if is_alpha else "agent_alpha_prophecy"
        line_idx = (turn - 1) // 2
        internal = alpha_lines[min(line_idx, len(alpha_lines) - 1)] if is_alpha else beta_lines[
            min(line_idx, len(beta_lines) - 1)
        ]

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
            routing_profile=routing_profile,
            use_ko_health_sidecar=sidecar_on,
        )
        all_ok = all_ok and bool(sent.get("ok"))
        envelope = sent.get("envelope") or {}
        env_bytes = envelope_utf8_byte_len(envelope)

        cr = client.post(
            "/v2/compress",
            json={
                "text": internal,
                "loss_profile": "semantic_general",
                "routing_profile": routing_profile,
            },
        )
        packet_bytes = 0
        savings_ratio = None
        if cr.status_code == 200:
            pkt = cr.json().get("compression_packet")
            if isinstance(pkt, dict):
                packet_bytes = len(json.dumps(pkt, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            m = cr.json().get("compression_metrics")
            if isinstance(m, dict) and m.get("savings_ratio") is not None:
                savings_ratio = float(m["savings_ratio"])
                savings.append(savings_ratio)

        vs_packet = None
        if packet_bytes > 0:
            vs_packet = round(1.0 - (env_bytes / packet_bytes), 6)

        transcript.append(
            {
                "turn": turn,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "wire_envelope_bytes": env_bytes,
                "trust_packet_json_bytes": packet_bytes,
                "envelope_vs_packet_savings_ratio": vs_packet,
                "receive_prior": recv_row,
                "send": {"ok": sent.get("ok"), "atom_id_count": (envelope.get("payload") or {}).get("atom_id_count")},
                "compression_metrics_savings_ratio": savings_ratio,
            }
        )
        last_envelope = envelope

    return {
        "schema": "mkm_inter_agent_dialogue_wire_first_v1",
        "session_id": session_id,
        "scenario": scenario,
        "use_ko_health_sidecar": sidecar_on,
        "routing_profile": routing_profile,
        "turns": turns,
        "all_ok": all_ok,
        "avg_trust_packet_savings_ratio": (sum(savings) / len(savings)) if savings else None,
        "avg_envelope_vs_packet_savings": (
            sum(t["envelope_vs_packet_savings_ratio"] or 0 for t in transcript) / len(transcript)
            if transcript
            else None
        ),
        "transcript": transcript,
        "research_only": True,
        "boundary_ack": "Wire-first mock; envelope JSON on-wire. Not production A2A or Track A.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--scenario", choices=("trading", "health", "lexicon_dense"), default="trading")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--use-ko-health-sidecar",
        action="store_true",
        help="[HYPO] Apply KO health sidecar on encode when scenario=health.",
    )
    args = ap.parse_args()
    doc = run_dialogue(
        turns=max(2, args.turns),
        scenario=args.scenario,
        use_ko_health_sidecar=args.use_ko_health_sidecar,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("all_ok"), "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc.get("all_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
