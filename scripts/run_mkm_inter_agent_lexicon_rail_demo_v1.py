#!/usr/bin/env python3
"""Demo: v2 Trust Packet + 41k lexicon atom_id rail (MKM language vocabulary layer)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_lexicon_rail_demo_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_demo(text: str, *, loss_profile: str = "semantic_general") -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import LEXICON_RAIL_KEY, RESIDUAL_STUB_KEY, app

    client = TestClient(app)
    cr = client.post("/v2/compress", json={"text": text, "loss_profile": loss_profile})
    if cr.status_code != 200:
        return {"ok": False, "error": f"compress_{cr.status_code}"}
    pkt = cr.json().get("compression_packet") or {}
    er = client.post("/v2/expand", json={"compression_packet": pkt})
    if er.status_code != 200:
        return {"ok": False, "error": f"expand_{er.status_code}"}
    rail = (pkt.get("residual_meta") or {}).get(LEXICON_RAIL_KEY) or {}
    stub = (pkt.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
    return {
        "ok": True,
        "schema": "mkm_inter_agent_lexicon_rail_demo_v1",
        "generated_at_utc": _utc(),
        "research_only": False,
        "boundary_ack": "Vocabulary rail only; not production SLA or complete MKM Language.",
        "input_text": text,
        "loss_profile": loss_profile,
        "atom_id_sequence": rail.get("atom_id_sequence"),
        "lexicon_meta": rail.get("lexicon_meta"),
        "compressed_text": pkt.get("compressed_text"),
        "reconstructed_text": stub.get("reconstructed_text"),
        "expanded_text": er.json().get("text"),
        "packet_fingerprint": pkt.get("content_fingerprint"),
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
    print(json.dumps({"ok": doc.get("ok"), "atom_id_count": len(doc.get("atom_id_sequence") or [])}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
