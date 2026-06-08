#!/usr/bin/env python3
"""tp01 A2A pilot — ops resume inject text → v2 compress when above skip threshold.

[HYPO] / research_only / B-track. Does not alter public resume pack MD for humans.

  py scripts/build_mkm_chat_resume_a2a_pilot_v1.py
  py scripts/build_mkm_chat_resume_a2a_pilot_v1.py --include-slice
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ops_memory_index_token_savings_v1 import _inject_pins_text  # noqa: E402
from mkm_a2a_compress_pilot_lib_v1 import (  # noqa: E402
    compress_plaintext_v2,
    count_tokens,
    load_compress_skip_rules,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json"


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_pilot_document(
    root: Path,
    *,
    top_n: int,
    include_slice: bool,
    slice_max_chars: int,
    lane: str | None,
    routing_profile: str,
) -> dict[str, Any]:
    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)

    inject_text = _inject_pins_text(
        root,
        top_n=top_n,
        include_slice=include_slice,
        slice_max_chars=slice_max_chars,
    )
    token_row = count_tokens(inject_text)

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    compress_row = compress_plaintext_v2(
        client,
        inject_text,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        client_request_id="a2a-tp01-resume-pilot",
    )

    return {
        "schema": "mkm_chat_resume_a2a_pilot_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "hypothesis_tier": "B",
        "target_point_id": "tp01_cursor_ops_resume_handoff",
        "status": "PILOT",
        "boundary_ack": (
            "[HYPO] tp01 pilot — machine wire handoff only. "
            "Human resume pack MD unchanged. No Track A·live merge."
        ),
        "a2a_target_points_ssot": "docs/final/artifacts/a2a_target_points_v1_latest.json",
        "options": {
            "top_n": top_n,
            "include_slice": include_slice,
            "slice_max_chars": slice_max_chars if include_slice else None,
            "lane": lane,
            "routing_profile": routing_profile,
        },
        "inject_payload": {
            "char_count": len(inject_text),
            **token_row,
            "preview_head": inject_text[:240] + ("..." if len(inject_text) > 240 else ""),
        },
        "compress_skip_rules_applied": skip_rules,
        "compress_result": compress_row,
        "wire_handoff_hint": {
            "when_compressed": "pass trust_packet_redacted + content_fingerprint to next agent chat",
            "when_skipped": "pass inject pins JSON or short essence lines only",
            "human_ui": "docs/final/artifacts/mkm_chat_resume_pack_latest.md unchanged",
        },
        "evidence_paths": [
            "scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
            "scripts/mkm_a2a_compress_pilot_lib_v1.py",
            "scripts/compression_token_api_v2_stub.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--include-slice", action="store_true")
    ap.add_argument("--slice-max-chars", type=int, default=1200)
    ap.add_argument("--lane", default=None)
    ap.add_argument(
        "--routing-profile",
        default="track_a_promoted",
        choices=["default", "track_a_promoted", "b_track_domain_relax"],
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    index_path = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    if not index_path.is_file():
        print(f"FAIL: ops memory index missing at {index_path}", file=sys.stderr)
        print("Run: py scripts/build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    doc = build_pilot_document(
        ROOT,
        top_n=args.top_n,
        include_slice=args.include_slice,
        slice_max_chars=args.slice_max_chars,
        lane=args.lane,
        routing_profile=args.routing_profile,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decision = (doc.get("compress_result") or {}).get("decision")
    tok = (doc.get("inject_payload") or {}).get("tokens")
    print(f"WROTE: {args.out}")
    print(f"decision={decision} inject_tokens={tok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
