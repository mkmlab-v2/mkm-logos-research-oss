#!/usr/bin/env python3
"""Validate or materialize mkm-logos-research-oss public export bundle.

  py scripts/build_logos_oss_public_export_bundle_v1.py --verify-only
  py scripts/build_logos_oss_public_export_bundle_v1.py --materialize
  py scripts/build_logos_oss_public_export_bundle_v1.py --verify-only --run-smoke
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/logos_oss_public_export_manifest_v1.json"
GUIDE = ROOT / "docs/final/artifacts/logos_oss_premarket_smoke_guide_v1.md"
PUBLIC_README = ROOT / "docs/final/artifacts/logos_oss_public_readme_v1.md"
OUT_REPORT = ROOT / "reports/logos_oss_public_export_bundle_v1_latest.json"
OUT_DIR_DEFAULT = ROOT / "exports/mkm-logos-research-oss-v1"
WORKFLOW_SSOT = ROOT / "docs/final/artifacts/logos_oss_github_workflow_oss_smoke_v1.yml"
ISSUE_TEMPLATE_BETA = ROOT / "docs/final/artifacts/logos_oss_github_issue_template_beta_feedback_v1.yml"
ISSUE_TEMPLATE_CONFIG = ROOT / "docs/final/artifacts/logos_oss_github_issue_template_config_v1.yml"
PY = sys.executable

REQUIREMENTS_TXT = """pytest>=7.0
"""

GITIGNORE_TXT = """__pycache__/
*.py[cod]
.pytest_cache/
.venv/
.env
data/logos/gnosis_kg/*.json
!data/logos/gnosis_kg/README.md
"""


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "logos_oss_public_export_manifest_v1":
        raise SystemExit("manifest schema mismatch")
    return doc


def _deny_hit(rel: str, manifest: dict[str, Any]) -> str | None:
    rel_norm = rel.replace("\\", "/")
    for sub in manifest.get("deny_path_substrings") or []:
        if sub in rel_norm:
            return f"deny_path_substring:{sub}"
    name = Path(rel).name.lower()
    for pat in manifest.get("deny_filename_patterns") or []:
        if pat.lower() in name:
            return f"deny_filename:{pat}"
    return None


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    denied: list[dict[str, str]] = []
    present: list[dict[str, str]] = []
    for rel in manifest.get("paths") or []:
        rel_s = str(rel).replace("\\", "/")
        deny = _deny_hit(rel_s, manifest)
        if deny:
            denied.append({"path": rel_s, "reason": deny})
            continue
        p = ROOT / rel_s
        if not p.is_file():
            missing.append(rel_s)
        else:
            present.append({"path": rel_s, "sha256": _sha256(p)})
    return {
        "missing": missing,
        "denied": denied,
        "present_count": len(present),
        "present": present,
        "ok": not missing and not denied,
    }


def materialize(manifest: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    git_dir = out_dir / ".git"
    preserve_git = git_dir.is_dir() and any(git_dir.iterdir())
    if out_dir.exists() and not preserve_git:
        if git_dir.exists():
            shutil.rmtree(git_dir, ignore_errors=True)
        for child in out_dir.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in manifest.get("paths") or []:
        rel_s = str(rel).replace("\\", "/")
        if _deny_hit(rel_s, manifest):
            continue
        src = ROOT / rel_s
        if not src.is_file():
            continue
        dst = out_dir / rel_s
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel_s)
    if PUBLIC_README.is_file():
        (out_dir / "README.md").write_text(PUBLIC_README.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("README.md (from public readme SSOT)")
    elif GUIDE.is_file():
        (out_dir / "README.md").write_text(GUIDE.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("README.md (from guide SSOT)")
    (out_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
    copied.append("requirements.txt (generated)")
    (out_dir / ".gitignore").write_text(GITIGNORE_TXT, encoding="utf-8")
    copied.append(".gitignore (generated)")
    if WORKFLOW_SSOT.is_file():
        wf_dst = out_dir / ".github/workflows/oss-smoke.yml"
        wf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORKFLOW_SSOT, wf_dst)
        copied.append(".github/workflows/oss-smoke.yml (from workflow SSOT)")
    if ISSUE_TEMPLATE_BETA.is_file():
        it_dst = out_dir / ".github/ISSUE_TEMPLATE/beta_feedback.yml"
        it_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ISSUE_TEMPLATE_BETA, it_dst)
        copied.append(".github/ISSUE_TEMPLATE/beta_feedback.yml (from SSOT)")
    if ISSUE_TEMPLATE_CONFIG.is_file():
        cfg_dst = out_dir / ".github/ISSUE_TEMPLATE/config.yml"
        cfg_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ISSUE_TEMPLATE_CONFIG, cfg_dst)
        copied.append(".github/ISSUE_TEMPLATE/config.yml (from SSOT)")
    return {"out_dir": str(out_dir), "copied_count": len(copied), "copied": copied}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--materialize", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_REPORT)
    ap.add_argument("--run-smoke", action="store_true")
    args = ap.parse_args()

    if not args.verify_only and not args.materialize:
        args.verify_only = True

    manifest = _load_manifest(args.manifest)
    verification = verify_manifest(manifest)

    smoke: dict[str, Any] | None = None
    if args.run_smoke and verification["ok"]:
        proc = subprocess.run(
            [PY, "scripts/run_logos_oss_premarket_smoke_v1.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        smoke = {"exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": (proc.stdout or proc.stderr)[-500:]}

    materialized: dict[str, Any] | None = None
    if args.materialize:
        if not verification["ok"]:
            raise SystemExit(f"manifest verify failed: missing={verification['missing']}")
        materialized = materialize(manifest, args.out_dir)

    doc = {
        "schema": "logos_oss_public_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "release_gate": manifest.get("release_gate", "OPEN_SOURCE_PREP"),
        "send_gate_scope": manifest.get("send_gate_scope"),
        "repo_target": manifest.get("repo_target_name"),
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "verification": verification,
        "materialized": materialized,
        "smoke": smoke,
        "ok": verification["ok"] and (smoke is None or smoke.get("ok", True)),
        "reproduce_verify": "py scripts/build_logos_oss_public_export_bundle_v1.py --verify-only",
        "reproduce_materialize": "py scripts/build_logos_oss_public_export_bundle_v1.py --materialize",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "present_count": verification["present_count"],
                "missing": verification["missing"],
                "materialized": materialized.get("out_dir") if materialized else None,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
