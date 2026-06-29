#!/usr/bin/env python3
"""Path A enterprise inbound chain — publish · media fact sheet · counsel manifest · lint."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/path_a_enterprise_inbound_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"cmd": cmd, "exit_code": proc.returncode, "ok": proc.returncode == 0, "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-publish", action="store_true")
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_publish:
        steps["publish"] = _run(
            [sys.executable, "scripts/run_path_a_commercial_defense_publish_chain_v1.py"]
        )
        ok = ok and steps["publish"]["ok"]

    steps["media_fact_sheet"] = _run(
        [sys.executable, "scripts/patch_path_a_product_lane_media_fact_sheet_v1.py"]
    )
    ok = ok and steps["media_fact_sheet"]["ok"]

    steps["counsel_manifest"] = _run(
        [
            sys.executable,
            "scripts/build_compression_b2b_counsel_export_manifest_v1.py",
            "--fail-if-missing",
        ]
    )
    ok = ok and steps["counsel_manifest"]["ok"]

    steps["narrative_fact_lock"] = _run(
        [sys.executable, "scripts/check_compression_narrative_fact_lock_v1.py"]
    )
    ok = ok and steps["narrative_fact_lock"]["ok"]

    steps["counsel_zip"] = _run(
        [sys.executable, "scripts/build_compression_b2b_counsel_zip_pack_v1.py"]
    )
    ok = ok and steps["counsel_zip"]["ok"]

    doc = {
        "schema": "path_a_enterprise_inbound_chain_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "chain_ok": ok,
        "steps": steps,
        "artifacts": {
            "fact_sheet": "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json",
            "media_fact_sheet": "docs/final/artifacts/media_fact_sheet_compression_api_v1_latest.md",
            "counsel_manifest": "docs/final/artifacts/compression_b2b_counsel_export_manifest_v1_latest.json",
            "counsel_zip": "docs/final/artifacts/compression_b2b_counsel_export_pack_v1.zip",
            "counsel_zip_meta": "docs/final/artifacts/compression_b2b_counsel_zip_pack_v1_latest.json",
            "narrative_lint": "reports/compression_narrative_fact_lock_latest.json",
        },
        "reproducible_command": "py scripts/run_path_a_enterprise_inbound_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
