#!/usr/bin/env python3
"""M10: Korean + mixed corpora — lexicon hit rate + wire envelope vs packet bytes."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_wire_bench_v1_latest.json"

from scripts.build_mkm_inter_agent_lexicon_hit_rate_bench_v1 import CORPORA  # noqa: E402
from scripts.mkm_inter_agent_wire_envelope_v1 import build_turn_envelope, envelope_utf8_byte_len  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_bench() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.build_mkm_inter_agent_lexicon_hit_rate_bench_v1 import _bench_line
    from scripts.compression_token_api_v2_stub import app
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    client = TestClient(app)
    session_id = "ko-wire-bench"
    corpora_out: dict[str, Any] = {}
    ko_atom_rates: list[float] = []

    for name, lines in CORPORA.items():
        rows = []
        for i, text in enumerate(lines, start=1):
            lex = _bench_line(text, path)
            enc = client.post(
                "/v1/research/mkm_lexicon_wire/encode",
                json={"text": text, "zstd_min_raw_bytes": 0},
            )
            enc_body = enc.json() if enc.status_code == 200 else {}
            env = build_turn_envelope(
                encode_response=enc_body,
                session_id=session_id,
                turn_id=i,
                from_agent="bench",
                to_agent="bench",
            )
            env_b = envelope_utf8_byte_len(env)
            cr = client.post("/v2/compress", json={"text": text, "loss_profile": "semantic_general"})
            pkt_b = 0
            if cr.status_code == 200:
                pkt = cr.json().get("compression_packet")
                if isinstance(pkt, dict):
                    pkt_b = len(json.dumps(pkt, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            ar = lex.get("atom_rate_tokens")
            if name == "health" and ar is not None:
                ko_atom_rates.append(float(ar))
            rows.append(
                {
                    **lex,
                    "envelope_bytes": env_b,
                    "packet_json_bytes": pkt_b,
                    "wire_byte_len": enc_body.get("wire_byte_len"),
                    "byte_savings_vs_packet": round(1.0 - env_b / pkt_b, 6) if pkt_b else None,
                }
            )
        corpora_out[name] = {
            "lines": rows,
            "avg_atom_rate_tokens": round(
                sum(r["atom_rate_tokens"] or 0 for r in rows) / len(rows), 6
            )
            if rows
            else None,
        }

    return {
        "ok": True,
        "schema": "mkm_inter_agent_ko_wire_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "corpora": corpora_out,
        "summary": {
            "health_avg_atom_rate_tokens": round(sum(ko_atom_rates) / len(ko_atom_rates), 6)
            if ko_atom_rates
            else None,
            "health_note": "Korean health lines often have low atom_id match; empty wire is valid research outcome.",
        },
        "boundary_ack": "Hit rate and byte size only; not translation quality or Track A KPI.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_bench()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
