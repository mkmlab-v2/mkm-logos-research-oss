#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize gitea/internal merge precheck from git state + intent artifacts.

Internal-first only (gitea|internal). No GitHub PR coupling. research_only.

Usage:
  py scripts/build_coding_intent_gitea_merge_precheck_v1.py
  py scripts/build_coding_intent_gitea_merge_precheck_v1.py --strict
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
LINK_LATEST = WORKSPACE_ROOT / "reports" / "coding_intent_link_v1_latest.json"
MANIFEST_LATEST = WORKSPACE_ROOT / "reports" / "coding_intent_pr_manifest_v1_latest.json"
OUT_LATEST = WORKSPACE_ROOT / "reports" / "coding_intent_gitea_merge_precheck_v1_latest.json"
SCHEMA_PATH = WORKSPACE_ROOT / "docs" / "final" / "schemas" / "coding_intent_gitea_merge_precheck_v1.schema.json"

REMOTE_CANDIDATES = ("gitea", "internal")


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(args: list[str], *, cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def resolve_integration_remote(root: Path, preferred: str | None) -> str:
    remotes = set((_run_git(["remote"], cwd=root) or "").splitlines())
    if preferred and preferred in remotes:
        return preferred
    for candidate in REMOTE_CANDIDATES:
        if candidate in remotes:
            return candidate
    raise SystemExit("error: neither gitea nor internal remote found")


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_precheck(
    *,
    integration_remote: str,
    base_ref: str,
    branch: str,
    head_sha: str,
    ahead_commits: int,
    porcelain_lines: int,
    link_doc: dict | None,
    manifest_doc: dict | None,
    link_drift: list[str] | None,
    strict: bool = False,
) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []

    if manifest_doc is None:
        blockers.append("missing_pr_manifest")
    elif manifest_doc.get("base_ref") != base_ref:
        warnings.append("manifest_base_ref_stale")

    manifest_count = int((manifest_doc or {}).get("commit_count") or 0)
    if manifest_doc and manifest_count != ahead_commits:
        warnings.append("manifest_commit_count_ne_ahead")

    if link_doc is None:
        warnings.append("missing_link_latest")
    elif link_drift:
        warnings.append("link_drift:" + ",".join(link_drift))

    coverage = (manifest_doc or {}).get("coverage") or {}
    if manifest_doc and manifest_count > 0:
        intent_cov = int(coverage.get("commits_with_intent_ref") or 0)
        if intent_cov < manifest_count:
            warnings.append("incomplete_intent_ref_coverage")

    if ahead_commits == 0 and porcelain_lines == 0:
        warnings.append("no_ahead_commits_and_clean_tree")

    if porcelain_lines > 0:
        warnings.append("working_tree_dirty")

    link_ok = link_doc.get("link_ok") if link_doc else None
    if link_doc and not link_ok and porcelain_lines == 0:
        warnings.append("link_ok_false_on_clean_tree")

    precheck_ok = len(blockers) == 0
    if strict and warnings:
        precheck_ok = False

    next_commands = [
        "powershell -File scripts/Invoke-CodingIntentGiteaMergePrecheck_v1.ps1 -RecordLink",
        "powershell -File scripts/Invoke-CodingIntentGiteaMergePrecheck_v1.ps1",
        f"powershell -File scripts/SoloDev-MergeFeatureToGiteaMain.ps1 -DryRun",
        "powershell -File scripts/push-internal.ps1",
    ]

    return {
        "schema": "coding_intent_gitea_merge_precheck_v1",
        "checked_at_utc": _utc_now_z(),
        "research_only": True,
        "publication_mode": "internal_first",
        "integration_remote": integration_remote,
        "base_ref": base_ref,
        "branch": branch,
        "head_sha": head_sha,
        "ahead_commits": ahead_commits,
        "porcelain_lines": porcelain_lines,
        "link_ok": link_ok,
        "link_drift": link_drift or [],
        "manifest_coverage": coverage,
        "precheck_ok": precheck_ok,
        "blockers": blockers,
        "warnings": warnings,
        "evidence_paths": [
            "reports/coding_intent_gitea_merge_precheck_v1_latest.json",
            "reports/coding_intent_pr_manifest_v1_latest.json",
            "reports/coding_intent_link_v1_latest.json",
        ],
        "next_commands": next_commands,
    }


def compute_link_drift(root: Path, link_doc: dict | None) -> list[str]:
    if not link_doc:
        return []
    drift: list[str] = []
    live_sha = _run_git(["rev-parse", "HEAD"], cwd=root)
    if live_sha and live_sha != (link_doc.get("git") or {}).get("head_sha"):
        drift.append("git_head")
    central_rel = (link_doc.get("checkpoint") or {}).get("central_path")
    if central_rel:
        central = root / central_rel
        if central.is_file():
            import importlib.util

            record_script = root / "scripts" / "record_coding_intent_link_v1.py"
            spec = importlib.util.spec_from_file_location("record_coding_intent_link_v1", record_script)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                live_cp = mod._latest_checkpoint(central, root=root)
                if live_cp.get("stamp_utc") != (link_doc.get("checkpoint") or {}).get("stamp_utc"):
                    drift.append("checkpoint_stamp")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--integration-remote", default=None)
    parser.add_argument("--out", type=Path, default=OUT_LATEST)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    remote = resolve_integration_remote(root, args.integration_remote)
    base_ref = f"{remote}/main"
    base_ok = bool(_run_git(["rev-parse", "--verify", base_ref], cwd=root))
    head_sha = _run_git(["rev-parse", "HEAD"], cwd=root) or "0000000"
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root) or "unknown"
    ahead_s = _run_git(["rev-list", "--count", f"{base_ref}..HEAD"], cwd=root)
    ahead_commits = int(ahead_s) if ahead_s and ahead_s.isdigit() else 0
    porcelain = _run_git(["status", "--porcelain"], cwd=root) or ""
    porcelain_lines = len([ln for ln in porcelain.splitlines() if ln.strip()])

    link_doc = _load_json(LINK_LATEST if LINK_LATEST.is_absolute() else root / LINK_LATEST)
    manifest_doc = _load_json(MANIFEST_LATEST if MANIFEST_LATEST.is_absolute() else root / MANIFEST_LATEST)
    drift = compute_link_drift(root, link_doc)

    doc = build_precheck(
        integration_remote=remote,
        base_ref=base_ref,
        branch=branch,
        head_sha=head_sha,
        ahead_commits=ahead_commits,
        porcelain_lines=porcelain_lines,
        link_doc=link_doc,
        manifest_doc=manifest_doc,
        link_drift=drift,
        strict=args.strict,
    )
    if not base_ok:
        doc["blockers"] = ["base_ref_missing", *doc["blockers"]]
        doc["precheck_ok"] = False

    if SCHEMA_PATH.is_file():
        try:
            import jsonschema

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(doc, schema)
        except ImportError:
            pass

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(payload)
        return 0 if doc["precheck_ok"] else (2 if args.strict else 0)

    out_path = args.out if args.out.is_absolute() else root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"OK: {out_path}")
    print(
        json.dumps(
            {
                "precheck_ok": doc["precheck_ok"],
                "integration_remote": remote,
                "base_ref": base_ref,
                "ahead_commits": ahead_commits,
                "warnings": doc["warnings"],
                "blockers": doc["blockers"],
            },
            ensure_ascii=False,
        )
    )
    if not doc["precheck_ok"]:
        return 2 if args.strict else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
