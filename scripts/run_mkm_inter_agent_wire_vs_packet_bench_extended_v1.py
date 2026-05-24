#!/usr/bin/env python3
"""M14: Extended wire envelope vs Trust Packet bench (all dialogue corpus lines)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_vs_packet_bench_extended_v1_latest.json"

from scripts.build_mkm_inter_agent_lexicon_hit_rate_bench_v1 import CORPORA  # noqa: E402
from scripts.run_mkm_inter_agent_dialogue_mock_v1 import (  # noqa: E402
    ALPHA_LINES_HEALTH,
    ALPHA_LINES_LEXICON_DENSE,
    ALPHA_LINES_TRADING,
    BETA_LINES_HEALTH,
    BETA_LINES_LEXICON_DENSE,
    BETA_LINES_TRADING,
)
from scripts.mkm_inter_agent_wire_envelope_v1 import build_turn_envelope, envelope_utf8_byte_len, new_session_id  # noqa: E402

DIALOGUE_CORPORA: dict[str, list[str]] = {
    "trading": ALPHA_LINES_TRADING + BETA_LINES_TRADING,
    "health": ALPHA_LINES_HEALTH + BETA_LINES_HEALTH,
    "lexicon_dense": ALPHA_LINES_LEXICON_DENSE + BETA_LINES_LEXICON_DENSE,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bench_lines(client: Any, session_id: str, lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, text in enumerate(lines, start=1):
        enc = client.post(
            "/v1/research/mkm_lexicon_wire/encode",
            json={"text": text, "zstd_min_raw_bytes": 0},
        )
        enc_body = enc.json() if enc.status_code == 200 else {}
        env = build_turn_envelope(
            encode_response=enc_body,
            session_id=session_id,
            turn_id=i,
            from_agent="bench_sender",
            to_agent="bench_receiver",
        )
        env_b = envelope_utf8_byte_len(env)
        cr = client.post("/v2/compress", json={"text": text, "loss_profile": "semantic_general"})
        pkt_b = 0
        if cr.status_code == 200:
            pkt = cr.json().get("compression_packet")
            if isinstance(pkt, dict):
                pkt_b = len(json.dumps(pkt, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        rows.append(
            {
                "line_index": i,
                "char_len": len(text),
                "envelope_bytes": env_b,
                "packet_json_bytes": pkt_b,
                "byte_savings_vs_packet": round(1.0 - env_b / pkt_b, 6) if pkt_b else None,
                "atom_id_count": (env.get("payload") or {}).get("atom_id_count"),
            }
        )
    return rows


def run_extended_bench() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    session_id = new_session_id("bench-ext")
    corpora_out: dict[str, Any] = {}

    merged: dict[str, list[str]] = {}
    for name, lines in CORPORA.items():
        merged.setdefault(name, []).extend(lines)
    for name, lines in DIALOGUE_CORPORA.items():
        merged.setdefault(name, []).extend(lines)

    for name, lines in merged.items():
        unique_lines = list(dict.fromkeys(lines))
        rows = _bench_lines(client, session_id, unique_lines)
        savings = [r["byte_savings_vs_packet"] for r in rows if r.get("byte_savings_vs_packet") is not None]
        corpora_out[name] = {
            "line_count": len(unique_lines),
            "lines": rows,
            "avg_byte_savings_vs_packet": round(sum(savings) / len(savings), 6) if savings else None,
        }

    total_lines = sum(c.get("line_count", 0) for c in corpora_out.values())
    return {
        "ok": True,
        "schema": "mkm_inter_agent_wire_vs_packet_bench_extended_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "total_unique_lines": total_lines,
        "corpora": corpora_out,
        "summary": {
            "lexicon_dense_avg_byte_savings": corpora_out.get("lexicon_dense", {}).get("avg_byte_savings_vs_packet"),
            "trading_avg_byte_savings": corpora_out.get("trading", {}).get("avg_byte_savings_vs_packet"),
            "health_avg_byte_savings": corpora_out.get("health", {}).get("avg_byte_savings_vs_packet"),
        },
        "boundary_ack": "Extended byte bench; short KO health lines may show negative savings vs packet.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_extended_bench()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
