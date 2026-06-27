#!/usr/bin/env python3
"""Check compression contributions manifest + validate JSONL corpora (B-track Moat).

Default: manifest schema OK; each manifest entry JSONL exists and passes validator.
--pr-strict: every *.jsonl under contributions_dir must appear in manifest.entries.
--validate-reference: also validate reference_example (deny-valve corpus).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/compression/contributions/compression_contributions_manifest_v1.json"
DEFAULT_OUT = ROOT / "reports/compression_contributions_manifest_check_v1_latest.json"
VALIDATE_SCRIPT = ROOT / "scripts/validate_compression_contributor_jsonl_v1.py"


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
    if doc.get("schema") != "compression_contributions_manifest_v1":
        raise ValueError(f"unexpected schema: {doc.get('schema')}")
    return doc


def _run_validate(jsonl: Path, *, min_rows: int, out_json: Path | None) -> tuple[int, dict[str, Any] | None]:
    cmd = [
        sys.executable,
        str(VALIDATE_SCRIPT),
        "--jsonl",
        str(jsonl),
        "--min-rows",
        str(min_rows),
    ]
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--out-json", str(out_json)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    detail: dict[str, Any] | None = None
    if out_json and out_json.is_file():
        detail = json.loads(out_json.read_text(encoding="utf-8"))
    elif proc.stdout.strip():
        try:
            detail = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            detail = None
    return proc.returncode, detail


def _resolve_repo_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p.resolve()
    return (ROOT / raw).resolve()


def _contributions_dir(manifest: dict[str, Any]) -> Path:
    rel = str(manifest.get("contributions_dir") or "data/compression/contributions")
    return _resolve_repo_path(rel)


def _entry_jsonl_paths(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("entries") or []
    paths: list[str] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        p = ent.get("jsonl") or ent.get("path")
        if isinstance(p, str) and p.strip():
            paths.append(p.strip().replace("\\", "/"))
    return paths


def _entry_min_rows_map(manifest: dict[str, Any], default_min_rows: int) -> dict[str, int]:
    entries = manifest.get("entries") or []
    out: dict[str, int] = {}
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        p = ent.get("jsonl") or ent.get("path")
        if not isinstance(p, str) or not p.strip():
            continue
        min_rows = ent.get("min_rows")
        if isinstance(min_rows, int) and min_rows > 0:
            out[p.strip().replace("\\", "/")] = min_rows
        else:
            out[p.strip().replace("\\", "/")] = default_min_rows
    return out


def _discover_contribution_jsonls(contributions_dir: Path) -> list[Path]:
    if not contributions_dir.is_dir():
        return []
    return sorted(
        p
        for p in contributions_dir.glob("*.jsonl")
        if p.is_file()
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pr-strict", action="store_true", help="Require manifest entry for each contributions/*.jsonl")
    ap.add_argument("--validate-reference", action="store_true", help="Validate reference_example outside dir")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    issues: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    try:
        manifest = _load_manifest(args.manifest.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: manifest: {exc}", file=sys.stderr)
        return 2

    min_rows = int((manifest.get("validate") or {}).get("min_rows") or 10)
    contributions_dir = _contributions_dir(manifest)
    manifest_paths = set(_entry_jsonl_paths(manifest))
    entry_min_rows_map = _entry_min_rows_map(manifest, min_rows)
    on_disk = _discover_contribution_jsonls(contributions_dir)
    on_disk_rels = {_rel(p) for p in on_disk}

    if args.pr_strict:
        for rel in sorted(on_disk_rels):
            if rel not in manifest_paths:
                issues.append(
                    {
                        "code": "manifest_missing_entry",
                        "path": rel,
                        "message": "contributions JSONL must be listed in manifest.entries",
                    }
                )
        for rel in sorted(manifest_paths):
            if rel not in on_disk_rels and not _resolve_repo_path(rel).is_file():
                issues.append(
                    {
                        "code": "manifest_stale_entry",
                        "path": rel,
                        "message": "manifest entry points to missing file",
                    }
                )

    to_validate: list[Path] = []
    for rel in sorted(manifest_paths):
        to_validate.append(_resolve_repo_path(rel))
    if args.validate_reference:
        ref = manifest.get("reference_example")
        if isinstance(ref, str) and ref.strip():
            to_validate.append(_resolve_repo_path(ref.strip()))

    seen: set[str] = set()
    for path in to_validate:
        key = _rel(path)
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            issues.append({"code": "missing_jsonl", "path": key, "message": "file not found"})
            continue
        out_report = ROOT / "reports" / f"compression_contributions_manifest_validate_{path.stem}_v1.json"
        current_min_rows = entry_min_rows_map.get(key, min_rows)
        code, detail = _run_validate(path, min_rows=current_min_rows, out_json=out_report)
        row = {
            "path": key,
            "exit_code": code,
            "validation_ok": bool(detail and detail.get("validation_ok")) if detail else code == 0,
            "min_rows": current_min_rows,
        }
        if detail:
            row["row_count"] = detail.get("row_count")
        checked.append(row)
        if code != 0:
            issues.append(
                {
                    "code": "validate_failed",
                    "path": key,
                    "message": f"validate_compression_contributor_jsonl_v1 exit {code}",
                }
            )

    ok = len(issues) == 0
    doc: dict[str, Any] = {
        "schema": "compression_contributions_manifest_check_v1",
        "generated_at_utc": _utc(),
        "manifest_path": _rel(args.manifest.resolve()),
        "contributions_dir": _rel(contributions_dir),
        "pr_strict": args.pr_strict,
        "validate_reference": args.validate_reference,
        "manifest_entry_count": len(manifest_paths),
        "on_disk_jsonl_count": len(on_disk_rels),
        "check_ok": ok,
        "issue_count": len(issues),
        "issues": issues,
        "checked": checked,
        "send_gate": manifest.get("send_gate", "HOLD"),
        "auto_track_a_promotion_allowed": False,
    }

    if not args.stdout_only:
        out = args.out_json.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"check_ok": ok, "issues": len(issues), "checked": len(checked)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
