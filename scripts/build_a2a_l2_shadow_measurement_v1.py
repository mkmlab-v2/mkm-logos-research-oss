#!/usr/bin/env python3
"""Tier 2 L2 shadow — log v2 compress on resume inject without changing human MD.

[HYPO] / research_only / B-track. Append `--append-log` on session upgrade / resume pack build.

  py scripts/build_a2a_l2_shadow_measurement_v1.py --append-log
  py scripts/build_a2a_l2_shadow_measurement_v1.py --lane infra --append-log
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

from bench_mkm_ltm_resume_lane_token_v1 import _lane_inject_text  # noqa: E402
from bench_mkm_ops_memory_index_token_savings_v1 import _inject_pins_text  # noqa: E402
from mkm_a2a_compress_pilot_lib_v1 import (  # noqa: E402
    compress_plaintext_v2,
    count_tokens,
    load_compress_skip_rules,
)
from mkm_ops_memory_index_lib_v1 import LANE_OPS_PACKS  # noqa: E402

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_l2_shadow_measurement_v1_latest.json"
DEFAULT_LOG = ROOT / "docs/final/artifacts/a2a_l2_shadow_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _log_path_display(root: Path, log_path: Path) -> str:
    try:
        return log_path.relative_to(root).as_posix()
    except ValueError:
        return log_path.as_posix()


def _resolve_inject_text(root: Path, *, lane: str | None, top_n: int) -> str:
    if lane:
        return _lane_inject_text(root, lane)
    return _inject_pins_text(root, top_n=top_n, include_slice=False)


def build_shadow_document(
    root: Path,
    *,
    lane: str | None = None,
    top_n: int = 3,
    routing_profile: str = "track_a_promoted",
) -> dict[str, Any]:
    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)
    inject_text = _resolve_inject_text(root, lane=lane, top_n=top_n)
    token_row = count_tokens(inject_text)
    inject_tokens = int(token_row.get("tokens") or 0)

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    lane_key = lane or "commander_default"
    compress_row = compress_plaintext_v2(
        client,
        inject_text,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        client_request_id=f"a2a-l2-shadow-{lane_key}",
    )

    metrics = compress_row.get("compression_metrics") or {}
    token_out = metrics.get("token_out")
    savings = metrics.get("savings_ratio")
    decision = compress_row.get("decision")
    shadow_ok = bool(inject_tokens > 0 and decision in {"compressed", "skipped_below_min_tokens"})
    if decision == "compressed":
        shadow_ok = shadow_ok and compress_row.get("http_status") == 200
        expand = compress_row.get("expand_packet_only") or {}
        shadow_ok = shadow_ok and expand.get("http_status") == 200

    return {
        "schema": "a2a_l2_shadow_measurement_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "tier": "tier2_shadow",
        "target_point_id": "tp01_cursor_ops_resume_handoff",
        "shadow_ok": shadow_ok,
        "boundary_ack": (
            "[HYPO] Tier 2 shadow — L2 compress logged only. Human resume pack MD unchanged. "
            "Not wire bus. Not Track A SLA."
        ),
        "options": {
            "lane": lane,
            "top_n": top_n if not lane else None,
            "routing_profile": routing_profile,
        },
        "inject_payload": {
            "char_count": len(inject_text),
            **token_row,
        },
        "compress_skip_rules_applied": skip_rules,
        "l2_compress": compress_row,
        "kpi_headline": {
            "inject_tokens": inject_tokens,
            "l2_token_out": token_out,
            "l2_savings_ratio": savings,
            "decision": decision,
        },
        "evidence_paths": [
            "scripts/build_a2a_l2_shadow_measurement_v1.py",
            "scripts/build_mkm_chat_resume_pack_v1.py",
            "scripts/Invoke-MkmCursorSessionUpgrade_v1.ps1",
        ],
    }


def _append_log_row(log_path: Path, doc: dict[str, Any]) -> None:
    headline = doc.get("kpi_headline") or {}
    opts = doc.get("options") or {}
    lane = opts.get("lane")
    inject_source = f"lane:{lane}" if lane else "commander_default"
    row = {
        "schema": "a2a_l2_shadow_log_v1",
        "measured_at_utc": doc.get("generated_at_utc"),
        "shadow_ok": doc.get("shadow_ok"),
        "lane": lane,
        "inject_source": inject_source,
        "inject_tokens": headline.get("inject_tokens"),
        "l2_token_out": headline.get("l2_token_out"),
        "l2_savings_ratio": headline.get("l2_savings_ratio"),
        "decision": headline.get("decision"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", choices=sorted(LANE_OPS_PACKS.keys()), default=None)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--routing-profile", default="track_a_promoted")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    doc = build_shadow_document(
        ROOT,
        lane=args.lane,
        top_n=max(1, args.top_n),
        routing_profile=args.routing_profile,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.append_log:
        _append_log_row(args.log, doc)

    headline = doc.get("kpi_headline") or {}
    print(f"WROTE: {args.out}")
    print(
        f"shadow_ok={doc.get('shadow_ok')} "
        f"inject_tokens={headline.get('inject_tokens')} "
        f"l2_savings={headline.get('l2_savings_ratio')} "
        f"decision={headline.get('decision')}"
    )
    if args.append_log:
        print(f"APPENDED: {_log_path_display(ROOT, args.log)}")

    if args.strict_exit and not doc.get("shadow_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
