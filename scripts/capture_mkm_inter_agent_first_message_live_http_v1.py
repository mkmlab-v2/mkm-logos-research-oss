#!/usr/bin/env python3
"""Refresh first-message HTTP evidence via in-process TestClient (reproducible)."""

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

FIXTURE_COMPRESS = ROOT / "docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def capture() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    from scripts.report_multilens_performance_eval import _jaccard

    body = json.loads(FIXTURE_COMPRESS.read_text(encoding="utf-8"))
    sample = str(body.get("text") or "")
    client = TestClient(app)
    cr = client.post("/v2/compress", json=body)
    cr_body = cr.json() if cr.status_code == 200 else {}
    pkt = cr_body.get("compression_packet") if isinstance(cr_body, dict) else None
    expand_body = {"compression_packet": pkt} if isinstance(pkt, dict) else {}
    er = client.post("/v2/expand", json=expand_body)
    er_body = er.json() if er.status_code == 200 else {}
    expanded = str(er_body.get("text") or "")
    stub = (pkt or {}).get("residual_meta", {}).get(RESIDUAL_STUB_KEY) if isinstance(pkt, dict) else {}
    recon = stub.get("reconstructed_text") if isinstance(stub, dict) else ""
    metrics = cr_body.get("compression_metrics") or {}

    return {
        "schema": "mkm_inter_agent_first_message_live_http_v1",
        "captured_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "capture_mode": "in_process_testclient",
        "stub": "scripts/compression_token_api_v2_stub.py",
        "base_url": "in-process://testclient",
        "sample_input": sample,
        "curl": {
            "start_stub": "py -m uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011",
            "compress": (
                "curl -s -X POST http://127.0.0.1:8011/v2/compress "
                '-H "Content-Type: application/json" '
                "-d @docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json"
            ),
            "expand": (
                "curl -s -X POST http://127.0.0.1:8011/v2/expand "
                '-H "Content-Type: application/json" '
                "-d @docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json"
            ),
        },
        "machine_roundtrip": {
            "expand_equals_stub_reconstructed": expanded == recon,
            "token_in": metrics.get("token_in"),
            "token_out": metrics.get("token_out"),
            "savings_ratio": metrics.get("savings_ratio"),
            "jaccard_proxy": _jaccard(sample, expanded) if sample else None,
        },
        "responses": {"compress": cr_body, "expand": er_body},
        "boundary_ack": "In-process capture for CI reproducibility; optional manual curl on port 8011 for demos.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = capture()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool((doc.get("machine_roundtrip") or {}).get("expand_equals_stub_reconstructed"))
    print(json.dumps({"ok": ok, "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
