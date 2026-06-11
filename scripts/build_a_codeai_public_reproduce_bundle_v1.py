#!/usr/bin/env python3
"""a-codeai public reproduce bundle — commands + HOLD gate (no auto-publish)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPRODUCE = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
LAUNCH = ROOT / "docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json"
OUT = ROOT / "docs/final/artifacts/a_codeai_public_reproduce_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()[:12]
    except OSError:
        pass
    return None


def build() -> dict[str, Any]:
    reproduce = json.loads(REPRODUCE.read_text(encoding="utf-8-sig")) if REPRODUCE.is_file() else {}
    launch = json.loads(LAUNCH.read_text(encoding="utf-8-sig")) if LAUNCH.is_file() else {}
    summary = launch.get("summary") or {}
    return {
        "schema": "a_codeai_public_reproduce_bundle_v1",
        "generated_at_utc": _utc(),
        "git_head": _git_head(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "launch_decision": summary.get("decision"),
        "launch_pass_count": summary.get("pass_count"),
        "one_command_reproduce": "py scripts/run_compression_evidence_lv1_chain_v1.py",
        "reproduce_pack": reproduce.get("skus"),
        "reproduce_commands": reproduce.get("reproduce_commands") or [],
        "deploy_note": (
            "Technical open-bench READY (8/8) — public HTML deploy is human-gated; "
            "SEND_GATE remains HOLD until legal sign-off."
        ),
        "boundary_ack": "FAIL-COMP-004 — do not merge SKU metrics in one headline.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
