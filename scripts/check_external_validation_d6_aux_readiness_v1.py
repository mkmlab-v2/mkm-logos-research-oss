#!/usr/bin/env python3
"""Aux-PC readiness: required scripts, tests, and optional seed artifacts before D6 run."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_CHECKS = [
    "reports/mkm_high_delegation_preflight_v1_latest.json",
    "reports/hd_autonomous_evolution_completion_v1_latest.json",
    "reports/compression_proof_completion_chain_v1_latest.json",
    "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_head(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return "unknown"


def _paths_from_commands(commands: list[str]) -> tuple[list[str], list[str]]:
    scripts: list[str] = []
    tests: list[str] = []
    for cmd in commands:
        for match in re.finditer(r"scripts[\\/][^\s\"']+", cmd):
            rel = match.group(0).replace("\\", "/")
            if rel not in scripts:
                scripts.append(rel)
        for match in re.finditer(r"tests[\\/][^\s\"']+", cmd):
            rel = match.group(0).replace("\\", "/")
            if rel not in tests:
                tests.append(rel)
    return scripts, tests


def check(
    *,
    workspace_root: Path,
    share_dir: Path | None,
    manifest_path: Path | None,
    expected_git_head: str | None,
) -> dict[str, Any]:
    root = workspace_root.resolve()
    manifest_file = manifest_path or (share_dir / "manifest.json" if share_dir else None)
    if manifest_file is None or not manifest_file.exists():
        raise SystemExit(f"missing manifest: {manifest_file}")

    manifest = _read_json(manifest_file)
    commands = list(manifest.get("reproduce_week1") or [])
    artifact_checks = list(manifest.get("artifact_checks") or DEFAULT_ARTIFACT_CHECKS)
    required_scripts, required_tests = _paths_from_commands(commands)

    script_rows = [
        {"path": rel, "exists": (root / rel).exists(), "kind": "script"}
        for rel in required_scripts
    ]
    test_rows = [
        {"path": rel, "exists": (root / rel).exists(), "kind": "test"}
        for rel in required_tests
    ]
    artifact_rows = [
        {"path": rel, "exists": (root / rel).exists(), "kind": "artifact"}
        for rel in artifact_checks
    ]

    seed_dir = share_dir / "seed_artifacts" if share_dir else None
    seed_rows: list[dict[str, Any]] = []
    if seed_dir and seed_dir.is_dir():
        for rel in artifact_checks:
            seed_path = seed_dir / Path(rel).name
            seed_rows.append(
                {
                    "workspace_path": rel,
                    "seed_file": str(seed_path).replace("\\", "/"),
                    "seed_exists": seed_path.exists(),
                }
            )

    aux_head = _git_head(root)
    git_ok = True
    if expected_git_head and expected_git_head not in ("unknown", ""):
        git_ok = aux_head == expected_git_head

    scripts_ok = all(r["exists"] for r in script_rows)
    tests_ok = all(r["exists"] for r in test_rows)
    artifacts_ok = all(r["exists"] for r in artifact_rows)
    # scripts/ is not in git on main — bundle copy is the aux path; git head is advisory only.
    ready = scripts_ok and tests_ok

    return {
        "schema": "external_validation_d6_aux_readiness_v1",
        "generated_at_utc": _utc_now(),
        "workspace_root": str(root),
        "share_dir": str(share_dir.resolve()) if share_dir else None,
        "manifest_path": str(manifest_file),
        "expected_git_head": expected_git_head,
        "aux_git_head": aux_head,
        "git_head_match": git_ok if expected_git_head else None,
        "required_scripts": script_rows,
        "required_tests": test_rows,
        "artifact_checks": artifact_rows,
        "seed_artifacts": seed_rows,
        "summary": {
            "scripts_ok": scripts_ok,
            "tests_ok": tests_ok,
            "artifacts_ok": artifacts_ok,
            "git_ok": git_ok,
            "ready_for_d6": ready,
        },
        "status": "ok" if ready else "fail",
        "next_if_fail": [
            "Run COPY_WORKSPACE_BUNDLE.cmd from share folder (scripts not in git)",
            "Run APPLY_SEED_ARTIFACTS.cmd if artifact_checks missing",
            "Re-run CHECK_AUX_READINESS.cmd until ready_for_d6=true",
            "Then run RUN_D6_ON_AUX.cmd",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=Path(r"C:\workspace"))
    ap.add_argument("--share-dir", type=Path, default=None)
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--expected-git-head", default="")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    share = args.share_dir.resolve() if args.share_dir else None
    expected = (args.expected_git_head or "").strip()
    if not expected and share:
        job_path = share / "d6_job_request_v1.json"
        if job_path.exists():
            expected = str(_read_json(job_path).get("main_git_head") or "")

    doc = check(
        workspace_root=args.workspace_root,
        share_dir=share,
        manifest_path=args.manifest,
        expected_git_head=expected or None,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload.strip())
    return 0 if doc["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
