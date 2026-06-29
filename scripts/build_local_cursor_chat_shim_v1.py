#!/usr/bin/env python3
"""Plan-only: OpenAI-compatible chat shim (compress → upstream API). B-track research_only."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "reports/cursor_coding_compress_bench_v1_latest.json"
EXTRACT = ROOT / "reports/cursor_coding_agent_extract_gate_v1_latest.json"
SHADOW = ROOT / "reports/chat_shim_upstream_shadow_v1_latest.json"
PHASE4 = ROOT / "reports/chat_shim_phase4_dogfood_readiness_v1_latest.json"
SIGNOFF = ROOT / "data/btrack/chat_shim_cursor_override_signoff_v1.json"
DEFAULT_OUT = ROOT / "reports/local_cursor_chat_shim_plan_v1_latest.json"
DEFAULT_PORT = 8011
DEFAULT_COMPRESS_PORT = 8010


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_plan(*, shim_port: int, compress_port: int) -> dict[str, Any]:
    bench = _load(BENCH)
    extract = _load(EXTRACT)
    shadow = _load(SHADOW)
    phase4 = _load(PHASE4)
    signoff = _load(SIGNOFF)
    poc_pass = bool((bench.get("poc_gate") or {}).get("pass"))
    extract_pass = bool((extract.get("gate") or {}).get("pass"))
    shadow_pass = bool(shadow.get("shadow_pass"))
    phase4_ready = bool(phase4.get("ready_for_dogfood"))
    signoff_approved = bool(signoff.get("cursor_override_dogfood_approved"))
    human_session = bool((signoff.get("attestations") or {}).get("human_cursor_session_completed"))
    ready = poc_pass and extract_pass
    # Human signoff gates override; shadow/phase4 live probe gates upstream_live only (429/503 transient).
    if signoff_approved and human_session:
        override_ready = ready
    else:
        override_ready = ready and phase4_ready

    return {
        "schema": "local_cursor_chat_shim_plan_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "status": "plan_and_v0_stub",
        "ready_for_cursor_override": override_ready,
        "ready_for_upstream_live": shadow_pass and ready,
        "prerequisites": {
            "compress_bench_pass": poc_pass,
            "extract_gate_pass": extract_pass,
            "chain_ready": ready,
            "upstream_shadow_pass": shadow_pass,
            "phase4_dogfood_ready": phase4_ready,
            "cursor_override_signoff_approved": signoff_approved,
            "human_cursor_session_completed": human_session,
        },
        "human_signoff": {
            "schema": "chat_shim_cursor_override_signoff_v1",
            "path": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "example_path": "data/btrack/chat_shim_cursor_override_signoff_v1.example.json",
            "record_script": "scripts/sandbox/record_chat_shim_cursor_override_signoff_v1.py",
        },
        "ports": {
            "chat_shim": shim_port,
            "compress_stub": compress_port,
            "note": "Separate processes; shim does in-process compress (no HTTP to 8010 required).",
        },
        "stack": {
            "shim_app": "scripts/cursor_chat_shim_v1.py",
            "compress_core": "scripts/core/coding_proxy_compress_v1.py",
            "hardening_config": "data/btrack/compression_coding_proxy_hardening_v1.json",
            "auto_chain": "scripts/Invoke-CursorCodingProxyAutoChain_v1.ps1",
            "shim_smoke": "scripts/Invoke-LocalCursorChatShimSmoke_v1.ps1",
            "upstream_shadow": "scripts/sandbox/run_chat_shim_upstream_shadow_v1.py",
        },
        "upstream_env": {
            "MKM_CHAT_SHIM_UPSTREAM_BASE_URL": "OpenAI-compatible base (e.g. https://api.deepseek.com or OpenRouter)",
            "MKM_CHAT_SHIM_UPSTREAM_API_KEY": "from .env only; never commit",
            "MKM_CHAT_SHIM_UPSTREAM_MODEL": "e.g. deepseek-chat or gpt-4.1-mini",
            "MKM_CHAT_SHIM_DRY_RUN": "1 for local smoke without upstream billing",
            "COMPRESSION_HARDENING_CONFIG_PATH": "data/btrack/compression_coding_proxy_hardening_v1.json",
        },
        "cursor_override_when_ready": [
            "Prerequisite: Invoke-LocalCursorChatShimSmoke_v1.ps1 exit 0 with DRY_RUN off and upstream set.",
            f"Base URL: http://127.0.0.1:{shim_port}/v1",
            "API key: any non-empty string if shim does not enforce (or MKM_CHAT_SHIM_API_KEY).",
            "NEVER enable while on Cursor unlimited Auto-only path without BYOK — verify product UI.",
        ],
        "pipeline": [
            "POST /v1/chat/completions",
            "compress system+user message bodies (structured preserve)",
            "forward to upstream",
            "append track_a_metering_log_v1.jsonl",
        ],
        "forbidden_claims": [
            "cursor_unlimited_replacement",
            "unlimited_free_coding",
            "track_a_promotion_from_shim",
            "ms_headline_47_percent_on_chat",
        ],
        "boundary_ack": "v0 shim for local dogfood; not production SLA.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Write chat shim wiring plan (B-track).")
    ap.add_argument("--shim-port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--compress-port", type=int, default=DEFAULT_COMPRESS_PORT)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--write-plan", action="store_true")
    args = ap.parse_args()

    doc = build_plan(shim_port=args.shim_port, compress_port=args.compress_port)
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))

    if not doc.get("prerequisites", {}).get("chain_ready"):
        print("PLAN_HOLD: compress bench or extract gate not pass")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
