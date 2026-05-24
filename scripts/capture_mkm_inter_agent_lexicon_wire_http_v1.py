#!/usr/bin/env python3
"""Capture MKM lexicon wire HTTP evidence (in-process TestClient)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_lexicon_wire_http_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def capture() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    sample_text = (
        "strong morph greek logos bible reference message kai mercy "
        "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    )
    client = TestClient(app)
    enc = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": sample_text, "zstd_min_raw_bytes": 0},
    )
    enc_body = enc.json() if enc.status_code == 200 else {}
    wire_b64 = str(enc_body.get("wire_b64") or "")
    dec = client.post("/v1/research/mkm_lexicon_wire/decode", json={"wire_b64": wire_b64})
    dec_body = dec.json() if dec.status_code == 200 else {}
    enc_ids = enc_body.get("atom_id_sequence") or []
    dec_ids = dec_body.get("atom_id_sequence") or []

    return {
        "schema": "mkm_inter_agent_lexicon_wire_http_v1",
        "captured_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "research_only": True,
        "capture_mode": "in_process_testclient",
        "stub": "scripts/compression_token_api_v2_stub.py",
        "sample_text": sample_text,
        "encode": enc_body,
        "decode": dec_body,
        "roundtrip_ok": enc_ids == dec_ids and len(enc_ids) > 0,
        "wire_byte_len": enc_body.get("wire_byte_len"),
        "boundary_ack": "Research lane only; not production SLA or live trading.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = capture()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0 if doc.get("roundtrip_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
