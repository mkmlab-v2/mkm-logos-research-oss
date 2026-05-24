#!/usr/bin/env python3
"""[HYPO] L1 research wire: atom_id_sequence-only msgpack vs full Trust Packet JSON size."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_l1_lexicon_wire_demo_v1_latest.json"
LEXICON_WIRE_SCHEMA = "mkm_lexicon_wire_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lexicon_wire_payload(atom_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": LEXICON_WIRE_SCHEMA,
        "symbol_key": "atom_id",
        "atom_id_sequence": atom_ids,
    }


def run_demo(text: str) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import LEXICON_RAIL_KEY, app
    from scripts.l1_side_channel_wire_codec import (
        codec_availability,
        decode_adaptive_msgpack,
        encode_adaptive_msgpack,
        json_utf8_payload_bytes,
    )

    client = TestClient(app)
    cr = client.post("/v2/compress", json={"text": text, "loss_profile": "semantic_general"})
    if cr.status_code != 200:
        return {"ok": False, "error": f"compress_{cr.status_code}"}

    pkt = cr.json().get("compression_packet") or {}
    rail = (pkt.get("residual_meta") or {}).get(LEXICON_RAIL_KEY) or {}
    atom_ids = rail.get("atom_id_sequence") if isinstance(rail, dict) else None
    if not isinstance(atom_ids, list):
        atom_ids = []

    avail = codec_availability()
    wire_result: dict[str, Any] = {"msgpack_available": avail.msgpack, "zstandard_available": avail.zstandard}
    if avail.msgpack and atom_ids:
        payload = _lexicon_wire_payload(atom_ids)
        try:
            wire_bytes, variant = encode_adaptive_msgpack(payload)
            roundtrip = decode_adaptive_msgpack(wire_bytes)
            wire_result = {
                **wire_result,
                "variant": variant,
                "wire_byte_len": len(wire_bytes),
                "json_utf8_byte_len": json_utf8_payload_bytes(payload),
                "roundtrip_ok": roundtrip.get("atom_id_sequence") == atom_ids,
            }
        except Exception as exc:
            wire_result["error"] = f"{type(exc).__name__}:{exc}"

    full_packet_json = len(json.dumps(pkt, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    compressed_only = len(str(pkt.get("compressed_text") or "").encode("utf-8"))
    rail_only_json = len(json.dumps({"atom_id_sequence": atom_ids}, ensure_ascii=False).encode("utf-8"))

    return {
        "ok": True,
        "schema": "mkm_inter_agent_l1_lexicon_wire_demo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "Byte-size comparison only; not production wire standard. "
            "Does not replace Trust Packet for human decode or Track A."
        ),
        "input_text": text,
        "atom_id_count": len(atom_ids),
        "atom_id_sequence": atom_ids,
        "size_bytes": {
            "full_trust_packet_json": full_packet_json,
            "compressed_text_utf8": compressed_only,
            "atom_id_list_json": rail_only_json,
            "lexicon_wire_msgpack": wire_result.get("wire_byte_len"),
        },
        "lexicon_wire": wire_result,
        "compression_metrics": cr.json().get("compression_metrics"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--text",
        default="MKM inter-agent message rail demo strong morph bible logos sasang myeongri.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = run_demo(args.text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        json.dumps(
            {
                "ok": doc.get("ok"),
                "atom_id_count": doc.get("atom_id_count"),
                "wire_bytes": (doc.get("lexicon_wire") or {}).get("wire_byte_len"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
