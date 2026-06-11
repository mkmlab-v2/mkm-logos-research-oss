#!/usr/bin/env python3
"""Check prophecy contributions manifest + validate contributor JSONL corpora (B-track Moat)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/prophecy/contributions/prophecy_contributions_manifest_v1.json"
DEFAULT_OUT = ROOT / "reports/prophecy_contributions_manifest_check_v1_latest.json"
VALIDATE_SCRIPT = ROOT / "scripts/validate_prophecy_contributor_jsonl_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing manifest: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "prophecy_contributions_manifest_v1":
        raise ValueError(f"unexpected schema: {doc.get('schema')}")
    return doc


def _run_validate(jsonl: Path, *, min_rows: int, out_json: Path | None) -> tuple[int, dict[str, Any] | None]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT), "--jsonl", str(jsonl), "--min-rows", str(min_rows)]
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--out-json", str(out_json)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    detail: dict[str, Any] | None = None
    if out_json and out_json.is_file():
        detail = json.loads(out_json.read_text(encoding="utf-8"))
    return proc.returncode, detail


def _resolve_repo_path(raw: str) -> Path:
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (ROOT / raw).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pr-strict", action="store_true")
    ap.add_argument("--validate-reference", action="store_true")
    args = ap.parse_args()

    manifest = _load_manifest(args.manifest.resolve())
    min_rows = int((manifest.get("validate") or {}).get("min_rows") or 5)
    contributions_dir = _resolve_repo_path(str(manifest.get("contributions_dir") or "data/prophecy/contributions"))

    entry_results: list[dict[str, Any]] = []
    ok = True
    for ent in manifest.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        rel_path = str(ent.get("jsonl") or ent.get("path") or "")
        jsonl = _resolve_repo_path(rel_path)
        out_val = ROOT / f"reports/prophecy_contributor_manifest_validate_{ent.get('id', 'row')}_v1.json"
        code, detail = _run_validate(jsonl, min_rows=min_rows, out_json=out_val)
        entry_results.append({"id": ent.get("id"), "jsonl": rel_path, "exit_code": code, "validation_ok": code == 0})
        ok = ok and code == 0

    if args.validate_reference:
        ref = str(manifest.get("reference_example") or "")
        if ref:
            code, _ = _run_validate(_resolve_repo_path(ref), min_rows=min_rows, out_json=None)
            ok = ok and code == 0

    if args.pr_strict and contributions_dir.is_dir():
        manifest_paths = {str(ent.get("jsonl") or ent.get("path") or "").replace("\\", "/") for ent in (manifest.get("entries") or [])}
        for p in sorted(contributions_dir.glob("*.jsonl")):
            rel = _rel(p)
            if rel not in manifest_paths:
                ok = False
                entry_results.append({"id": None, "jsonl": rel, "exit_code": 1, "validation_ok": False, "error": "not_in_manifest"})

    doc = {
        "schema": "prophecy_contributions_manifest_check_v1",
        "generated_at_utc": _utc(),
        "manifest": _rel(args.manifest.resolve()),
        "check_ok": ok,
        "pr_strict": args.pr_strict,
        "entries": entry_results,
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"check_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
