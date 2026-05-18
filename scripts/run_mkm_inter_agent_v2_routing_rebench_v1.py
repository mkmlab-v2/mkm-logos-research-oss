#!/usr/bin/env python3
"""B-track: compare v2 compress routing profiles on sample + V2 health/ssot snippets."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_v2_routing_rebench_latest.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
PROFILES = ("default", "track_a_promoted", "b_track_domain_relax")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _samples_from_v2_input() -> list[dict[str, str]]:
    out: list[dict[str, str]] = [
        {
            "id": "inter_agent_demo",
            "text": (
                "사상의학 체질 분류 예시. MKM inter-agent message rail demo. "
                "sasang myeongri logos trust_packet."
            ),
        }
    ]
    if INPUT_V2.is_file():
        try:
            doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
            for case in doc.get("compression_cases") or []:
                if not isinstance(case, dict):
                    continue
                cid = str(case.get("id", ""))
                raw = str(case.get("raw_text", "") or "")
                if cid in {"cmp2_011", "cmp2_006", "cmp2_004"} and raw:
                    out.append({"id": cid, "text": raw})
        except json.JSONDecodeError:
            pass
    return out


def run_rebench() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    for sample in _samples_from_v2_input():
        for profile in PROFILES:
            cr = client.post(
                "/v2/compress",
                json={
                    "text": sample["text"],
                    "loss_profile": "semantic_general",
                    "client_request_id": sample["id"],
                    "routing_profile": profile,
                },
            )
            body = cr.json() if cr.status_code == 200 else {}
            metrics = body.get("compression_metrics") or {}
            flags = body.get("integrity_flags") or {}
            pkt = body.get("compression_packet") or {}
            route = (pkt.get("router_meta") or {}) if isinstance(pkt, dict) else {}
            rows.append(
                {
                    "sample_id": sample["id"],
                    "routing_profile": profile,
                    "http_status": cr.status_code,
                    "token_in": metrics.get("token_in"),
                    "token_out": metrics.get("token_out"),
                    "savings_ratio": metrics.get("savings_ratio"),
                    "shard_id": route.get("shard_id"),
                    "domain": route.get("domain"),
                    "v2_case_id": flags.get("v2_case_id"),
                    "routing_research_only": flags.get("routing_research_only"),
                }
            )
    return {
        "schema": "mkm_inter_agent_v2_routing_rebench_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "boundary_ack": (
            "Per-request v2 compress samples only — not full 40-case Track A bench. "
            "track_a_promoted uses signoff allowlist when client_request_id matches cmp2_*."
        ),
        "profiles": list(PROFILES),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_rebench()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "row_count": len(doc["rows"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
