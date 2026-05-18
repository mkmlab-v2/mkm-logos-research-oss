#!/usr/bin/env python3
"""A2A dialogue mock: two agents speak only via v2 Trust Packets (B-track · INTERNAL)."""

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

DEFAULT_JSONL = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_mock_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json"

ALPHA_LINES = [
    "WATCH regime: macro fragility elevated. Recommend REDUCE exposure 20% on BTC until gate clears.",
    "Prophecy lane B-track: dual-leg KOSPI/BTC divergence noted. Hold new longs; review at 09:00 KST.",
]
BETA_LINES = [
    "ACK: exposure reduction logged. No new long orders until your next packet.",
    "ACK: dual-leg brief received. Executor standing by; risk profile unchanged.",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _redact_packet(pkt: dict[str, Any], max_len: int = 280) -> dict[str, Any]:
    out = json.loads(json.dumps(pkt, ensure_ascii=False))
    if isinstance(out.get("compressed_text"), str) and len(out["compressed_text"]) > max_len:
        out["compressed_text"] = out["compressed_text"][: max_len - 3] + "..."
    stub = (out.get("residual_meta") or {}).get("mk_stub_v2")
    if isinstance(stub, dict) and isinstance(stub.get("reconstructed_text"), str):
        rt = stub["reconstructed_text"]
        if len(rt) > max_len:
            stub["reconstructed_text"] = rt[: max_len - 3] + "..."
    return out


def run_dialogue(*, turns: int = 4, loss_profile: str = "semantic_general") -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    from scripts.report_multilens_performance_eval import _jaccard

    client = TestClient(app)
    transcript: list[dict[str, Any]] = []
    last_packet: dict[str, Any] | None = None
    all_packet_only = True
    all_expand_ok = True

    for turn in range(1, turns + 1):
        is_alpha = turn % 2 == 1
        role = "agent_alpha_prophecy" if is_alpha else "agent_beta_executor"
        line_idx = (turn - 1) // 2
        if is_alpha:
            internal_plain = ALPHA_LINES[min(line_idx, len(ALPHA_LINES) - 1)]
        else:
            expand_preview = ""
            if last_packet is not None:
                er0 = client.post("/v2/expand", json={"compression_packet": last_packet})
                if er0.status_code == 200:
                    expand_preview = (er0.json().get("text") or "")[:120]
            internal_plain = BETA_LINES[min(line_idx, len(BETA_LINES) - 1)]
            if expand_preview:
                internal_plain = f"{internal_plain} [inferred_from_packet: {expand_preview}]"

        cr = client.post(
            "/v2/compress",
            json={"text": internal_plain, "loss_profile": loss_profile},
        )
        compress_ok = cr.status_code == 200
        packet = cr.json().get("compression_packet") if compress_ok else None

        expand_row: dict[str, Any] | None = None
        if last_packet is not None:
            er = client.post(
                "/v2/expand",
                json={"compression_packet": last_packet},
            )
            expand_ok = er.status_code == 200
            all_expand_ok = all_expand_ok and expand_ok
            body = er.json() if expand_ok else {"error": er.text}
            stub = (last_packet.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
            recon = stub.get("reconstructed_text") if isinstance(stub, dict) else None
            expanded = body.get("text") if isinstance(body, dict) else ""
            expand_row = {
                "from_role": "agent_alpha_prophecy" if (turn - 1) % 2 == 1 else "agent_beta_executor",
                "to_role": role,
                "http_status": er.status_code,
                "expanded_text_preview": expanded[:200],
                "expand_equals_stub_reconstructed": expanded == recon,
                "jaccard_internal_vs_expanded": _jaccard(internal_plain, expanded),
                "original_text_on_request": False,
            }

        entry: dict[str, Any] = {
            "turn": turn,
            "role": role,
            "internal_plaintext": internal_plain,
            "wire_only": True,
            "compress": {
                "http_status": cr.status_code,
                "loss_profile": loss_profile,
            },
            "trust_packet_redacted": _redact_packet(packet) if isinstance(packet, dict) else None,
        }
        if expand_row is not None:
            entry["expand_inbound_packet_only"] = expand_row
        transcript.append(entry)

        if isinstance(packet, dict):
            last_packet = packet
        else:
            all_expand_ok = False

    return {
        "schema": "mkm_inter_agent_dialogue_mock_summary_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "boundary_ack": (
            "Simulated agents; plaintext is logged for audit only. On-wire payload is Trust Packet only. "
            "Not production A2A. Not Track A trading trigger."
        ),
        "turns_requested": turns,
        "turns_recorded": len(transcript),
        "all_compress_ok": all(c.get("compress", {}).get("http_status") == 200 for c in transcript),
        "all_expand_packet_only": all_packet_only,
        "all_expand_ok": all_expand_ok,
        "transcript": transcript,
        "evidence_paths": [
            "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "scripts/compression_token_api_v2_stub.py",
            "tests/test_run_mkm_inter_agent_dialogue_mock_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="MKM inter-agent A2A dialogue mock (Trust Packet only).")
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--jsonl-out", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    summary = run_dialogue(turns=max(2, args.turns))
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    with args.jsonl_out.open("w", encoding="utf-8") as fh:
        for row in summary.get("transcript", []):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    ok = bool(summary.get("all_compress_ok") and summary.get("all_expand_ok"))
    print(json.dumps({"ok": ok, "summary": str(args.summary_out), "jsonl": str(args.jsonl_out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
