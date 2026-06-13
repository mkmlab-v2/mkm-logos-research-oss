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

ALPHA_LINES_TRADING = [
    (
        "WATCH regime: macro fragility elevated. Recommend REDUCE exposure 20% on BTC until gate clears. "
        "Prophecy lane B-track dual-leg KOSPI BTC divergence noted. Hold new longs; review at 09:00 KST. "
        "Executor standing by; risk profile unchanged; guardian gate WATCH; no Track A live trigger."
    ),
    (
        "Prophecy lane B-track: dual-leg KOSPI/BTC divergence noted. Hold new longs; review at 09:00 KST. "
        "Macro fragility elevated; REDUCE exposure advisory; executor ACK pending; regime_map primary gate. "
        "WATCH regime maintained; no Track A live trigger; guardian gate observability only."
    ),
]
BETA_LINES_TRADING = [
    (
        "ACK: exposure reduction logged. No new long orders until your next packet. "
        "Executor standing by; risk profile unchanged; prophecy lane B-track observability only."
    ),
    (
        "ACK: dual-leg brief received. Executor standing by; risk profile unchanged. "
        "No live trading trigger; WATCH regime maintained until next trust packet."
    ),
]
ALPHA_LINES_HEALTH = [
    "환자 건강 수면 식사 증상 호흡 피로 회복 체온 — 임상 진단 바이탈 Silver Tech 모니터링.",
    "건강검진 회복률 주의: 수면 부족·식사 불균형 시 증상 악화 가능. 의료 팀 검토 요청.",
]
BETA_LINES_HEALTH = [
    "ACK: 환자 바이탈·증상 패킷 수신. 수면·식사 권고 유지, 임상 게이트 통과 전 조치 보류.",
    "ACK: 건강검진 브리프 반영. 회복 지표 모니터링 지속, 추가 증상 시 재패킷 요청.",
]
# Repeated lexicon-mappable chunk — long enough to clear compress skip (>=32 tok) and
# exercise 41k atom rail on tp02 bench (~200+ tok per alpha turn at 4x repeat).
_LEXICON_DENSE_CHUNK = (
    "strong morph greek logos bible reference message kai mercy alpha beta gamma "
    "delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma "
    "hebrew aramaic covenant prophecy wisdom knowledge understanding counsel "
    "might lord god spirit holy righteousness judgment salvation redemption "
    "prophecy lane B-track WATCH regime macro fragility exposure REDUCE HOLD "
    "orders risk profile dual-leg KOSPI BTC executor standing guardian gate "
)
ALPHA_LINES_LEXICON_DENSE = [
    (_LEXICON_DENSE_CHUNK * 4).strip(),
    (_LEXICON_DENSE_CHUNK * 4 + " fragility elevated covenant renewal shadow advisory ").strip(),
]
BETA_LINES_LEXICON_DENSE = [
    (
        "ACK: lexicon-dense trust packet received; atom rail count noted for routing compare. "
        + _LEXICON_DENSE_CHUNK * 2
    ).strip(),
    (
        "ACK: greek hebrew token density high; executor standing by for next compressed turn. "
        + _LEXICON_DENSE_CHUNK * 2
    ).strip(),
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


def run_dialogue(
    *,
    turns: int = 4,
    loss_profile: str = "semantic_general",
    routing_profile: str = "track_a_promoted",
    scenario: str = "trading",
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    from scripts.report_multilens_performance_eval import _jaccard

    client = TestClient(app)
    transcript: list[dict[str, Any]] = []
    last_packet: dict[str, Any] | None = None
    all_packet_only = True
    all_expand_ok = True
    if scenario == "health":
        alpha_lines = ALPHA_LINES_HEALTH
        beta_lines = BETA_LINES_HEALTH
    elif scenario == "lexicon_dense":
        alpha_lines = ALPHA_LINES_LEXICON_DENSE
        beta_lines = BETA_LINES_LEXICON_DENSE
    else:
        alpha_lines = ALPHA_LINES_TRADING
        beta_lines = BETA_LINES_TRADING

    for turn in range(1, turns + 1):
        is_alpha = turn % 2 == 1
        role = "agent_alpha_prophecy" if is_alpha else "agent_beta_executor"
        line_idx = (turn - 1) // 2
        if is_alpha:
            internal_plain = alpha_lines[min(line_idx, len(alpha_lines) - 1)]
        else:
            expand_preview = ""
            if last_packet is not None:
                er0 = client.post("/v2/expand", json={"compression_packet": last_packet})
                if er0.status_code == 200:
                    expand_preview = (er0.json().get("text") or "")[:120]
            internal_plain = beta_lines[min(line_idx, len(beta_lines) - 1)]
            if expand_preview:
                internal_plain = f"{internal_plain} [inferred_from_packet: {expand_preview}]"

        cr = client.post(
            "/v2/compress",
            json={
                "text": internal_plain,
                "loss_profile": loss_profile,
                "routing_profile": routing_profile,
                "client_request_id": f"a2a-{scenario}-turn-{turn}",
            },
        )
        compress_ok = cr.status_code == 200
        cr_body = cr.json() if compress_ok else {}
        packet = cr_body.get("compression_packet") if compress_ok else None
        lexicon_count = 0
        if isinstance(packet, dict):
            rail = (packet.get("residual_meta") or {}).get("mkm_lexicon_rail_v1")
            if isinstance(rail, dict) and isinstance(rail.get("atom_id_sequence"), list):
                lexicon_count = len(rail["atom_id_sequence"])

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

        router_meta = (packet or {}).get("router_meta") if isinstance(packet, dict) else {}
        entry: dict[str, Any] = {
            "turn": turn,
            "role": role,
            "internal_plaintext": internal_plain,
            "wire_only": True,
            "compress": {
                "http_status": cr.status_code,
                "loss_profile": loss_profile,
                "routing_profile": routing_profile,
                "lexicon_atom_id_count": lexicon_count,
                "compression_metrics": cr_body.get("compression_metrics"),
                "integrity_flags": {
                    "routing_research_only": (cr_body.get("integrity_flags") or {}).get(
                        "routing_research_only"
                    ),
                    "shard_id": router_meta.get("shard_id") if isinstance(router_meta, dict) else None,
                    "domain": router_meta.get("domain") if isinstance(router_meta, dict) else None,
                },
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
        "routing_profile": routing_profile,
        "scenario": scenario,
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
    ap.add_argument("--routing-profile", default="track_a_promoted")
    ap.add_argument("--scenario", choices=("trading", "health", "lexicon_dense"), default="trading")
    ap.add_argument("--jsonl-out", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    summary = run_dialogue(
        turns=max(2, args.turns),
        routing_profile=args.routing_profile,
        scenario=args.scenario,
    )
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
