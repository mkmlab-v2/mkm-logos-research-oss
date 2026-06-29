#!/usr/bin/env python3
"""RQ-027 live bridge smoke — uses pre-built dry-run request; fixture fallback on block [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQ = ROOT / "reports" / "tmp" / "commander_dev_pack_pet_bridge_request_dry_run_latest.json"
DEFAULT_RES = ROOT / "reports" / "commander_dev_pack_pet_bridge_live_smoke_latest.json"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--request-json", type=Path, default=DEFAULT_REQ)
    ap.add_argument("--response-out", type=Path, default=DEFAULT_RES)
    ap.add_argument("--force", action="store_true", help="Run even if MKM_PET_BRIDGE_ENABLE_LIVE_POST unset")
    ap.add_argument("--dry-run-only", action="store_true")
    args = ap.parse_args()
    _load_dotenv()

    if not args.force and not _truthy("MKM_PET_BRIDGE_ENABLE_LIVE_POST"):
        out = {
            "schema": "commander_dev_pack_pet_bridge_live_smoke_v1",
            "generated_at_utc": _utc_now(),
            "skipped": True,
            "reason": "MKM_PET_BRIDGE_ENABLE_LIVE_POST not set",
        }
        args.response_out.parent.mkdir(parents=True, exist_ok=True)
        args.response_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("SKIP: set MKM_PET_BRIDGE_ENABLE_LIVE_POST=1 to run live smoke")
        return 0

    req_path = args.request_json if args.request_json.is_absolute() else ROOT / args.request_json
    if not req_path.is_file():
        print(f"MISSING: {req_path}", flush=True)
        return 2

    res_path = args.response_out if args.response_out.is_absolute() else ROOT / args.response_out
    req_out = ROOT / "reports" / "pet_companion_device_bridge_live_request_latest.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "fetch_pet_companion_device_bridge_live_v1.py"),
        "--request-out",
        str(req_out),
        "--response-out",
        str(res_path),
        "--fallback-fixture-on-block",
    ]
    if args.dry_run_only:
        cmd.append("--dry-run")

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary: Dict[str, Any] = {
        "schema": "commander_dev_pack_pet_bridge_live_smoke_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "dry_run_only": args.dry_run_only,
        "fetch_exit_code": proc.returncode,
        "fetch_stdout_tail": (proc.stdout or "")[-500:],
        "fetch_stderr_tail": (proc.stderr or "")[-500:],
    }
    if res_path.is_file():
        try:
            body = json.loads(res_path.read_text(encoding="utf-8-sig"))
            if isinstance(body, dict):
                summary["response_schema"] = body.get("schema")
                summary["response_status"] = body.get("status")
                summary["skipped"] = body.get("skipped")
        except json.JSONDecodeError:
            summary["response_parse_error"] = True

    meta_path = res_path.with_name("commander_dev_pack_pet_bridge_live_smoke_meta_latest.json")
    meta_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
