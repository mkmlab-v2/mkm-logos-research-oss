#!/usr/bin/env python3
"""Validate or materialize mkm-bible-topology-crosswalk public export bundle [HYPO/OSS].

  py scripts/build_mkm_bible_topology_crosswalk_public_export_bundle_v1.py --verify-only
  py scripts/build_mkm_bible_topology_crosswalk_public_export_bundle_v1.py --materialize
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_public_export_manifest_v1.json"
README_SSOT = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_readme_en_v1.md"
CONTRIBUTING_SSOT = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_contributing_en_v1.md"
SECURITY_SSOT = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_security_en_v1.md"
WORKFLOW_SSOT = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_github_workflow_v1.yml"
GITIGNORE_SSOT = ROOT / "docs/final/artifacts/mkm_bible_topology_crosswalk_gitignore_v1.txt"
OUT_REPORT = ROOT / "reports/mkm_bible_topology_crosswalk_public_export_bundle_v1_latest.json"
OUT_DIR_DEFAULT = ROOT / "exports/mkm-bible-topology-crosswalk-v1"
OUT_DIR_PUSH = ROOT / "exports/_push-mkm-bible-topology-crosswalk"
PY = sys.executable

REQUIREMENTS_TXT = """pytest>=7.0
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
    if doc.get("schema") != "mkm_bible_topology_crosswalk_public_export_manifest_v1":
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
    for item in manifest.get("export_root_copies") or []:
        src_rel = str(item.get("from", "")).replace("\\", "/")
        if not src_rel:
            continue
        deny = _deny_hit(src_rel, manifest)
        if deny:
            denied.append({"path": src_rel, "reason": deny})
            continue
        p = ROOT / src_rel
        if not p.is_file():
            missing.append(f"export_root_copy:{src_rel}")
        else:
            present.append({"path": src_rel, "export_as": item.get("to"), "sha256": _sha256(p)})
    return {
        "missing": missing,
        "denied": denied,
        "present_count": len(present),
        "present": present,
        "ok": not missing and not denied,
    }


def _rmtree_onerror(func, path: str, exc_info: object) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise


def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    shutil.rmtree(path, onerror=_rmtree_onerror)


def materialize(manifest: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        _safe_rmtree(out_dir)
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
    for item in manifest.get("export_root_copies") or []:
        src_rel = str(item.get("from", "")).replace("\\", "/")
        dst_rel = str(item.get("to", "")).replace("\\", "/")
        if not src_rel or not dst_rel:
            continue
        src = ROOT / src_rel
        if not src.is_file():
            continue
        dst = out_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(f"{dst_rel} (from {src_rel})")
    if README_SSOT.is_file():
        (out_dir / "README.md").write_text(README_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("README.md (from readme SSOT)")
    if CONTRIBUTING_SSOT.is_file():
        (out_dir / "CONTRIBUTING.md").write_text(CONTRIBUTING_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("CONTRIBUTING.md (from contributing SSOT)")
    if SECURITY_SSOT.is_file():
        (out_dir / "SECURITY.md").write_text(SECURITY_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("SECURITY.md (from security SSOT)")
    (out_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
    copied.append("requirements.txt (generated)")
    if GITIGNORE_SSOT.is_file():
        (out_dir / ".gitignore").write_text(GITIGNORE_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(".gitignore (from SSOT)")
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = reports_dir / ".gitkeep"
    if not gitkeep.is_file():
        gitkeep.write_text("", encoding="utf-8")
        copied.append("reports/.gitkeep (generated)")
    if WORKFLOW_SSOT.is_file():
        wf_dst = out_dir / ".github/workflows/topology-contrib-lint.yml"
        wf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORKFLOW_SSOT, wf_dst)
        copied.append(".github/workflows/topology-contrib-lint.yml (from workflow SSOT)")
    return {"out_dir": str(out_dir), "copied_count": len(copied), "copied": copied}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--materialize", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    ap.add_argument("--push-dir", action="store_true", help=f"Materialize to {OUT_DIR_PUSH.name} (push staging)")
    ap.add_argument("--out", type=Path, default=OUT_REPORT)
    ap.add_argument("--run-smoke", action="store_true", help="Run bible topology OSS smoke after verify")
    args = ap.parse_args()

    if not args.verify_only and not args.materialize and not args.run_smoke:
        args.verify_only = True

    manifest = _load_manifest(args.manifest)
    verification = verify_manifest(manifest)

    smoke: dict[str, Any] | None = None
    if args.run_smoke and verification["ok"]:
        proc = subprocess.run(
            [PY, "scripts/run_bible_topology_oss_smoke_v1.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        smoke = {"exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": (proc.stdout or proc.stderr)[-400:]}

    materialized: dict[str, Any] | None = None
    if args.materialize:
        if not verification["ok"]:
            raise SystemExit(f"manifest verify failed: missing={verification['missing']}")
        out_target = OUT_DIR_PUSH if args.push_dir else args.out_dir
        materialized = materialize(manifest, out_target)

    doc = {
        "schema": "mkm_bible_topology_crosswalk_public_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "repo_target": manifest.get("repo_target_name"),
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "verification": verification,
        "materialized": materialized,
        "smoke": smoke,
        "ok": verification["ok"] and (smoke is None or smoke.get("ok", True)),
        "reproduce_verify": "py scripts/build_mkm_bible_topology_crosswalk_public_export_bundle_v1.py --verify-only",
        "reproduce_materialize": "py scripts/build_mkm_bible_topology_crosswalk_public_export_bundle_v1.py --materialize",
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
