#!/usr/bin/env python3
"""Gated System2 Vertex staging upload — export MD pack then optional GCS upload."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_SIGNOFF_SCHEMA = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "mkm_system2_human_signoff_ack_v1.schema.json"
)
DEFAULT_OUT = ROOT / "reports" / "mkm_system2_vertex_staging_upload_v1_latest.json"
DEFAULT_BUCKET = "mkm-lab-agi-2025-vertex-ai-staging"
DEFAULT_PROJECT = "mkm-lab-agi-2025"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_signoff(path: Path, *, required_scope: str, schema_path: Path) -> list[str]:
    from scripts.mkm_system2_human_signoff_v1 import validate_signoff as _validate

    return _validate(path, required_scope=required_scope, schema_path=schema_path)


def run_agent_search_corpus(*, dry_run: bool, skip_upload: bool = True) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_and_upload_agent_search_corpus_v1.py"),
        "--profile",
        "system2-gate",
    ]
    if dry_run:
        cmd.append("--dry-run")
    if skip_upload:
        cmd.append("--skip-upload")
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "")[-400:],
    }


def upload_md_files(files: list[dict[str, Any]], *, project: str, bucket: str, dry_run: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if dry_run:
        for f in files:
            out.append({**f, "uploaded": False, "dry_run_upload": True})
        return out
    try:
        from google.cloud import storage
    except ImportError:
        for f in files:
            out.append({**f, "uploaded": False, "error": "google_cloud_storage_missing"})
        return out
    client = storage.Client(project=project)
    bkt = client.bucket(bucket)
    for f in files:
        local = Path(f["local_md"])
        if not local.is_file():
            local = ROOT / f["local_md"]
        obj = f["gcs_object"]
        if not local.is_file():
            out.append({**f, "uploaded": False, "error": "missing_local_md"})
            continue
        blob = bkt.blob(obj)
        blob.upload_from_filename(str(local), content_type="text/markdown")
        out.append({**f, "uploaded": True, "gs_uri": f"gs://{bucket}/{obj}"})
    return out


def run_invoke(
    *,
    signoff_json: Path,
    apply_upload: bool,
    project: str,
    bucket: str,
    staging_jsonl: Path,
    agent_search_corpus_dry_run: bool = False,
) -> dict[str, Any]:
    signoff_errs = validate_signoff(signoff_json, required_scope="vertex_upload", schema_path=DEFAULT_SIGNOFF_SCHEMA)
    if signoff_errs:
        return {
            "schema": "mkm_system2_vertex_staging_upload_v1",
            "generated_at_utc": _utc(),
            "ok": False,
            "failed_reasons": signoff_errs,
            "boundary_ack": "human sign-off required for vertex_upload scope",
        }

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/export_system2_vertex_staging_pack_v1.py"),
            "--staging-jsonl",
            str(staging_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    export_ok = cp.returncode == 0
    manifest_path = ROOT / "reports/mkm_system2_vertex_staging_export_v1_latest.json"
    files: list[dict[str, Any]] = []
    if manifest_path.is_file():
        files = json.loads(manifest_path.read_text(encoding="utf-8")).get("files") or []

    upload_rows = upload_md_files(files, project=project, bucket=bucket, dry_run=not apply_upload)
    uploaded = sum(1 for r in upload_rows if r.get("uploaded"))

    corpus_step: dict[str, Any] | None = None
    if agent_search_corpus_dry_run and export_ok:
        corpus_step = run_agent_search_corpus(dry_run=True, skip_upload=True)

    ok = export_ok and (not apply_upload or uploaded > 0 or len(files) == 0)
    if corpus_step is not None:
        ok = ok and corpus_step.get("ok", False)

    return {
        "schema": "mkm_system2_vertex_staging_upload_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "apply_upload": apply_upload,
        "export": {"exit_code": cp.returncode, "ok": export_ok, "tail": (cp.stdout or cp.stderr or "")[-300:]},
        "upload_rows": upload_rows,
        "uploaded_count": uploaded,
        "agent_search_corpus": corpus_step,
        "human_sign_off_required": True,
        "boundary_ack": "System2 staging upload; no Track A/live auto-merge.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-signoff-json", required=True)
    ap.add_argument("--apply-upload", action="store_true", help="Upload to GCS; default is export plan only")
    ap.add_argument(
        "--agent-search-corpus-dry-run",
        action="store_true",
        help="After export, plan system2-gate Agent Search corpus (PDF dry-run)",
    )
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--staging-jsonl", default=str(ROOT / "reports/mkm_system2_vertex_staging_v1.jsonl"))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    doc = run_invoke(
        signoff_json=Path(args.human_signoff_json),
        apply_upload=args.apply_upload,
        project=args.project,
        bucket=args.bucket,
        staging_jsonl=Path(args.staging_jsonl),
        agent_search_corpus_dry_run=args.agent_search_corpus_dry_run,
    )
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out_json": str(out), "uploaded_count": doc.get("uploaded_count", 0)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
