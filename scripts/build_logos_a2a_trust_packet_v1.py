#!/usr/bin/env python3
"""Build Logos A2A trust packet pilot — vector_4d + anchor ids only ([HYPO] / B-track).

  py scripts/build_logos_a2a_trust_packet_v1.py
"""
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
sys.path.insert(0, str(ROOT / "scripts"))

from logos_a2a_wire_lib_v1 import build_logos_wire_plaintext, load_logos_wire_refs  # noqa: E402
from mkm_a2a_compress_pilot_lib_v1 import compress_plaintext_v2, load_compress_skip_rules  # noqa: E402

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_a2a_trust_packet_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_document(root: Path, *, routing_profile: str = "track_a_promoted") -> dict[str, Any]:
    refs = load_logos_wire_refs(root)
    plaintext = build_logos_wire_plaintext(refs)
    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    compress_row = compress_plaintext_v2(
        client,
        plaintext,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        client_request_id="logos-a2a-trust-packet-v1",
        must_keep_overlay_terms=[
            "gematria_bridge_v1",
            "[NON_GATING]",
            "research_only",
            "send_gate",
        ],
    )

    return {
        "schema": "logos_a2a_trust_packet_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "target_point_id": "tp_logos_math_vector_anchor_wire",
        "status": "PILOT",
        "boundary_ack": (
            "[HYPO] Logos math wire — vector_4d + anchor_ids only; no full corpus on wire. "
            "Structural router/gold gates are not prophecy accuracy. No Track A·live merge."
        ),
        "logos_wire_refs": refs,
        "inject_payload": {
            "char_count": len(plaintext),
            "preview_head": plaintext[:240] + ("..." if len(plaintext) > 240 else ""),
        },
        "compress_skip_rules_applied": skip_rules,
        "compress_result": compress_row,
        "wire_handoff_hint": {
            "pass_fields": ["logos_wire_refs.vector_4d", "logos_wire_refs.anchor_ids"],
            "omit_on_wire": ["per_anchor", "resonance_edges", "full_graph_bundle"],
        },
        "repro_command": "py scripts/build_logos_a2a_trust_packet_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--routing-profile", default="track_a_promoted")
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    doc = build_document(root, routing_profile=args.routing_profile)
    refs = doc.get("logos_wire_refs") or {}
    if not refs.get("anchor_ids"):
        print("FAIL: no anchor_ids in logos_wire_refs", file=sys.stderr)
        return 1
    if doc.get("compress_result", {}).get("decision") not in ("compressed",):
        print(
            f"FAIL: compress decision={doc.get('compress_result', {}).get('decision')}",
            file=sys.stderr,
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"anchors={len(refs.get('anchor_ids') or [])} "
        f"vector_4d={refs.get('vector_4d')} decision=compressed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
