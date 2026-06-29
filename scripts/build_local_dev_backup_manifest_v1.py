#!/usr/bin/env python3
"""Local dev backup manifest — Cursor/MKM paths only (no secrets, no .env body)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/local_dev_backup_manifest_latest.json"

# Paths to snapshot presence + sha256 (never read .env values).
MANIFEST_PATHS = [
    ".cursor/mcp.json",
    ".cursorrules",
    "AGENTS.md",
    "CLAUDE.md",
    "MISSION_LOG.md",
    "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs/final/artifacts/startup_package_ai_2026_submission_checklist_v1_latest.json",
    "reports/kstartup_startup_package_ai_submit_runbook_v1.txt",
    "reports/kstartup_startup_package_ai_g0_human_checklist_v1.txt",
    "scripts/check_kstartup_startup_package_ai_submission_gate_v1.py",
    "scripts/compression_token_api_stub.py",
    "scripts/run_cursor_coding_compress_bench_v1.py",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
        return out.strip()[:12] or None
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return None


def _file_entry(rel: str) -> dict[str, Any]:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return {"path": rel, "exists": False}
    data = p.read_bytes()
    return {
        "path": rel,
        "exists": True,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


def _cursor_rules_count() -> int:
    rules_dir = ROOT / ".cursor" / "rules"
    if not rules_dir.is_dir():
        return 0
    return sum(1 for _ in rules_dir.glob("*.mdc"))


def build() -> dict[str, Any]:
    entries = [_file_entry(rel) for rel in MANIFEST_PATHS]
    missing = [e["path"] for e in entries if not e.get("exists")]
    return {
        "schema": "local_dev_backup_manifest_v1",
        "generated_at_utc": _utc(),
        "git_head": _git_head(),
        "workspace_root": str(ROOT),
        "cursor_rules_mdc_count": _cursor_rules_count(),
        "entries": entries,
        "missing_count": len(missing),
        "missing_paths": missing,
        "secrets_policy": "never_included — backup .env manually offline; do not commit",
        "restore_hint": [
            "git checkout <sha> for tracked files",
            "Cursor: Settings export + .cursor/mcp.json from this manifest",
            "User env: docs/final/LOCAL_MACHINE_POINTER_V1.md (local only)",
        ],
        "boundary_ack": "Manifest presence only; not a full machine image.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build local dev backup manifest (no secrets).")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    doc = build()
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0 if doc["missing_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
