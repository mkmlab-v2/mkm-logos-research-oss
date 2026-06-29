#!/usr/bin/env python3
"""Plan-only: local Cursor → Track A compress stub proxy wiring (no server auto-start)."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "reports/cursor_coding_compress_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/local_cursor_compress_adapter_plan_v1_latest.json"
DEFAULT_STUB_URL = "http://127.0.0.1:8010"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _health_ok(base_url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def build_plan(*, base_url: str, bench_path: Path) -> dict[str, Any]:
    bench: dict[str, Any] = {}
    if bench_path.is_file():
        bench = json.loads(bench_path.read_text(encoding="utf-8-sig"))
    poc_pass = bool((bench.get("poc_gate") or {}).get("pass"))
    wiring_allowed = bool((bench.get("poc_gate") or {}).get("adapter_wiring_allowed"))

    return {
        "schema": "local_cursor_compress_adapter_plan_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "status": "plan_only",
        "poc_bench_ref": str(bench_path.relative_to(ROOT)).replace("\\", "/") if bench_path.is_file() else None,
        "poc_gate_pass": poc_pass,
        "wiring_allowed": wiring_allowed,
        "stub_health": {
            "base_url": base_url,
            "health_ok": _health_ok(base_url),
        },
        "stack": {
            "compress_endpoint": "POST /v1/compress",
            "stub_script": "scripts/compression_token_api_stub.py",
            "bench_script": "scripts/run_cursor_coding_compress_bench_v1.py",
            "backup_manifest": "scripts/build_local_dev_backup_manifest_v1.py",
        },
        "start_stub_example": (
            "py -m uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010"
        ),
        "hardening_config": "data/btrack/compression_coding_proxy_hardening_v1.json",
        "env_for_stub": {
            "COMPRESSION_HARDENING_CONFIG_PATH": "data/btrack/compression_coding_proxy_hardening_v1.json"
        },
        "cursor_override_steps": [
            "Set COMPRESSION_HARDENING_CONFIG_PATH=data/btrack/compression_coding_proxy_hardening_v1.json before stub start.",
            "Cursor Settings → Models → Override OpenAI Base URL (product UI; verify your Cursor version).",
            f"Base URL: {base_url}/v1 (OpenAI-compatible path — verify against stub OpenAPI).",
            "API key: stub local key or COMPRESSION_API_KEY from .env (never commit).",
            "Dogfood: enable eval_context.meter_log on compress requests → track_a_metering_log.",
            "Smoke: scripts/Invoke-LocalCursorCompressProxySmoke_v1.ps1",
        ],
        "commercialization_note": {
            "sku": "dev_finops_proxy",
            "not": ["clinic_mmp_required", "cursor_unlimited_replacement", "custom_coding_llm"],
            "evidence_needed": ["30d metering log", "1 team pilot LOI"],
        },
        "forbidden_until_poc_pass": not wiring_allowed,
        "boundary_ack": "Plan artifact only; no Track A promotion.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Write Cursor compress adapter wiring plan.")
    ap.add_argument("--base-url", default=DEFAULT_STUB_URL)
    ap.add_argument("--bench-json", default=str(BENCH))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--write-plan", action="store_true", help="Write plan JSON (default if no other action).")
    args = ap.parse_args()

    bench_path = Path(args.bench_json)
    if not bench_path.is_absolute():
        bench_path = ROOT / bench_path

    doc = build_plan(base_url=args.base_url.strip(), bench_path=bench_path)
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))

    if doc.get("forbidden_until_poc_pass"):
        print("WIRING_HOLD: run cursor coding bench until poc_gate.pass=true")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
