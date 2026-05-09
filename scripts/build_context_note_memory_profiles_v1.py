#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.6, M:0.8}
# Balance: 90
# Purpose: Build domain-specific context note memory indices (ops/strategy/research).
# Keywords: sqlite, memory, profiles, retrieval, indexing

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_context_note_memory_index_v1.py"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/context_note_profile_build_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_profile(
    *,
    profile_name: str,
    glob_pat: str,
    excludes: list[str],
    sqlite_out: Path,
    relations_out: Path,
    model_id: str,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(BUILD),
        "--glob",
        glob_pat,
        "--max-files",
        "0",
        "--embedding-backend",
        "sentence_transformers",
        "--sentence-transformer-model",
        model_id,
        "--sqlite-out",
        str(sqlite_out),
        "--relations-json",
        str(relations_out),
        "--dry-run",
    ]
    for ex in excludes:
        cmd.extend(["--exclude-glob", ex])
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "profile": profile_name,
        "command_ok": cp.returncode == 0,
        "exit_code": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
        "sqlite_out": str(sqlite_out).replace("\\", "/"),
        "relations_out": str(relations_out).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sentence-transformer-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    common_excludes = [
        "docs/final/artifacts/archive/**/*.md",
        "docs/final/artifacts/vibe_runs_raw/**/*.md",
        "docs/final/artifacts/workspace_postit_index_latest.md",
        "docs/final/artifacts/ai_triage_bundle_latest.md",
    ]
    profiles = [
        {
            "name": "ops",
            "glob": "docs/final/**/*ops*.md",
            "sqlite": ROOT / "docs/final/artifacts/context_note_memory_ops_v1.sqlite",
            "relations": ROOT / "docs/final/artifacts/context_note_relations_ops_latest.json",
        },
        {
            "name": "strategy",
            "glob": "docs/final/**/*plan*.md",
            "sqlite": ROOT / "docs/final/artifacts/context_note_memory_strategy_v1.sqlite",
            "relations": ROOT / "docs/final/artifacts/context_note_relations_strategy_latest.json",
        },
        {
            "name": "research",
            "glob": "docs/final/**/*.md",
            "sqlite": ROOT / "docs/final/artifacts/context_note_memory_research_v1.sqlite",
            "relations": ROOT / "docs/final/artifacts/context_note_relations_research_latest.json",
        },
    ]

    rows = []
    for p in profiles:
        rows.append(
            _run_profile(
                profile_name=p["name"],
                glob_pat=p["glob"],
                excludes=common_excludes,
                sqlite_out=p["sqlite"],
                relations_out=p["relations"],
                model_id=args.sentence_transformer_model,
            )
        )

    overall_ok = all(bool(r.get("command_ok")) for r in rows)
    out = {
        "schema": "context_note_profile_build_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "overall_ok": overall_ok,
        "profiles": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

