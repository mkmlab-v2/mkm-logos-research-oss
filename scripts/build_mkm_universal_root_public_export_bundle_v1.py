#!/usr/bin/env python3
"""Validate or materialize mkm-universal-root public export bundle [HYPO/OSS].

  py scripts/build_mkm_universal_root_public_export_bundle_v1.py --verify-only
  py scripts/build_mkm_universal_root_public_export_bundle_v1.py --materialize
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_public_push_gate_lib_v1 import evaluate_public_push_gate  # noqa: E402

MANIFEST = ROOT / "docs/final/artifacts/mkm_universal_root_public_export_manifest_v1.json"
README_SSOT = ROOT / "docs/final/artifacts/mkm_universal_root_readme_hero_en_v1.md"
CONTRIBUTING_SSOT = ROOT / "docs/final/artifacts/mkm_universal_root_contributing_en_v1.md"
WORKFLOW_SSOT = ROOT / "docs/final/artifacts/mkm_universal_root_github_workflow_oss_smoke_v1.yml"
OUT_REPORT = ROOT / "reports/mkm_universal_root_public_export_bundle_v1_latest.json"
OUT_DIR_DEFAULT = ROOT / "exports/mkm-universal-root-v1"
PY = sys.executable

REQUIREMENTS_TXT = """jsonschema>=4.0
pytest>=7.0
"""

GITIGNORE_TXT = """__pycache__/
*.py[cod]
.pytest_cache/
.venv/
.env
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
    if doc.get("schema") != "mkm_universal_root_public_export_manifest_v1":
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


def _rmtree_onerror(func, path: str, exc_info: object) -> None:
    """Windows: clear read-only bits on nested .git objects before retry."""
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
    # Export README from SSOT hero
    if README_SSOT.is_file():
        (out_dir / "README.md").write_text(README_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("README.md (from hero SSOT)")
    if CONTRIBUTING_SSOT.is_file():
        (out_dir / "CONTRIBUTING.md").write_text(CONTRIBUTING_SSOT.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append("CONTRIBUTING.md (from contributing SSOT)")
    (out_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")
    copied.append("requirements.txt (generated)")
    (out_dir / ".gitignore").write_text(GITIGNORE_TXT, encoding="utf-8")
    copied.append(".gitignore (generated)")
    if WORKFLOW_SSOT.is_file():
        wf_dst = out_dir / ".github/workflows/oss-smoke.yml"
        wf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORKFLOW_SSOT, wf_dst)
        copied.append(".github/workflows/oss-smoke.yml (from workflow SSOT)")
    return {"out_dir": str(out_dir), "copied_count": len(copied), "copied": copied}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--materialize", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_REPORT)
    ap.add_argument("--run-smoke", action="store_true", help="Run OSS smoke after verify (monorepo cwd)")
    ap.add_argument(
        "--skip-push-gate",
        action="store_true",
        help="Skip public push substance gate (not for live export)",
    )
    ap.add_argument(
        "--commander-override-push-gate",
        action="store_true",
        help="Bypass public push gate (commander only)",
    )
    args = ap.parse_args()

    push_gate: dict[str, Any] | None = None
    if args.materialize and not args.skip_push_gate:
        push_gate = evaluate_public_push_gate(
            action="export_materialize",
            commander_override=args.commander_override_push_gate,
        )
        if not push_gate.get("ok"):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "public_push_gate_blocked",
                        "violations": push_gate.get("violations"),
                        "reproduce": push_gate.get("reproduce_substance"),
                    },
                    ensure_ascii=False,
                )
            )
            return 2

    manifest = _load_manifest(args.manifest)
    verification = verify_manifest(manifest)

    smoke: dict[str, Any] | None = None
    if args.run_smoke and verification["ok"]:
        proc = subprocess.run(
            [PY, "scripts/run_universal_root_oss_cursor_smoke_v1.py"],
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
        materialized = materialize(manifest, args.out_dir)

    doc = {
        "schema": "mkm_universal_root_public_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "repo_target": manifest.get("repo_target_name"),
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "readme_ssot": str(README_SSOT.relative_to(ROOT)).replace("\\", "/"),
        "verification": verification,
        "materialized": materialized,
        "smoke": smoke,
        "public_push_gate": push_gate,
        "ok": verification["ok"] and (smoke is None or smoke.get("ok", True)) and (push_gate is None or push_gate.get("ok", True)),
        "reproduce_verify": "py scripts/build_mkm_universal_root_public_export_bundle_v1.py --verify-only",
        "reproduce_materialize": "py scripts/build_mkm_universal_root_public_export_bundle_v1.py --materialize",
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
