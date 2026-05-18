#!/usr/bin/env python3
"""Capture one v2 Trust Packet round-trip for MKM inter-agent worked example (INTERNAL)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT_JSON = ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json"
SAMPLE_INPUT = (
    "사상의학 체질 분류 예시. MKM inter-agent message rail demo. "
    "sasang taeeum soeum myeongri logos atom_id trust_packet."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truncate(s: str, max_len: int = 240) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _redact_packet(pkt: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(pkt, ensure_ascii=False))
    stub = (out.get("residual_meta") or {}).get("mk_stub_v2")
    if isinstance(stub, dict) and isinstance(stub.get("reconstructed_text"), str):
        stub["reconstructed_text"] = _truncate(stub["reconstructed_text"], 320)
    if isinstance(out.get("compressed_text"), str):
        out["compressed_text"] = _truncate(out["compressed_text"], 320)
    return out


def capture() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    from scripts.report_multilens_performance_eval import _jaccard

    client = TestClient(app)
    cr = client.post(
        "/v2/compress",
        json={"text": SAMPLE_INPUT, "loss_profile": "semantic_general"},
    )
    compress_status = cr.status_code
    compress_body: dict[str, Any] = cr.json() if compress_status == 200 else {"error": cr.text}

    packet = compress_body.get("compression_packet") if compress_status == 200 else None
    expand_body: dict[str, Any] | None = None
    expand_status: int | None = None
    machine_roundtrip: dict[str, Any] = {}

    if isinstance(packet, dict):
        er = client.post("/v2/expand", json={"compression_packet": packet})
        expand_status = er.status_code
        expand_body = er.json() if expand_status == 200 else {"error": er.text}
        stub = (packet.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
        recon = stub.get("reconstructed_text") if isinstance(stub, dict) else None
        expanded = expand_body.get("text") if isinstance(expand_body, dict) else None
        machine_roundtrip = {
            "expand_equals_stub_reconstructed": expanded == recon,
            "jaccard_input_vs_expanded": _jaccard(SAMPLE_INPUT, expanded or ""),
            "jaccard_input_vs_stub_reconstructed": _jaccard(SAMPLE_INPUT, recon or ""),
            "original_text_on_expand_request": False,
        }

    l1_path = ROOT / "docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json"
    l1_agg: dict[str, Any] | None = None
    if l1_path.is_file():
        try:
            l1_doc = json.loads(l1_path.read_text(encoding="utf-8"))
            if isinstance(l1_doc.get("aggregate"), dict):
                l1_agg = l1_doc["aggregate"]
        except json.JSONDecodeError:
            l1_agg = None

    return {
        "schema": "mkm_inter_agent_first_message_worked_example_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "boundary_ack": (
            "Machine roundtrip (v2 packet-only expand) is not human lossless decode. "
            "No production SLA. Not industry interoperability proof."
        ),
        "sample_input": SAMPLE_INPUT,
        "compress": {
            "http_status": compress_status,
            "request": {"loss_profile": "semantic_general"},
            "response_packet_redacted": _redact_packet(packet) if isinstance(packet, dict) else None,
            "compression_metrics": compress_body.get("compression_metrics")
            if compress_status == 200
            else None,
            "integrity_flags": compress_body.get("integrity_flags")
            if compress_status == 200
            else None,
        },
        "expand_packet_only": {
            "http_status": expand_status,
            "response_text_preview": _truncate((expand_body or {}).get("text", "") or "", 320)
            if isinstance(expand_body, dict)
            else None,
            "machine_roundtrip": machine_roundtrip,
        },
        "human_decode_research_only": {
            "source": l1_path.relative_to(ROOT).as_posix(),
            "research_only": True,
            "aggregate": l1_agg,
            "public_copy_ko": (
                "역복원 게이트(연구 스파이크) 기준 exact 복원률은 약 57.9%이며, "
                "무손실 통역·100% 복원을 주장하지 않습니다."
            ),
        },
        "evidence_paths": [
            "scripts/compression_token_api_v2_stub.py",
            "docs/final/openapi_token_compression_v2_draft.yaml",
            "tests/test_compression_token_api_v2_stub.py",
            "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
            "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
        ],
    }


def main() -> int:
    out = DEFAULT_OUT_JSON
    doc = capture()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool(doc.get("expand_packet_only", {}).get("machine_roundtrip", {}).get("expand_equals_stub_reconstructed"))
    print(json.dumps({"ok": ok, "output": str(out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
