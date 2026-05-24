#!/usr/bin/env python3
"""Verify SANDBOX artifact bundle presence (post-chain gate)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports/sandbox_prophecy_evidence_manifest_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_artifacts_verify_v1_latest.json"

REQUIRED_KEYS = {
    "reports/sandbox_prophecy_panel_v1_latest.json": ["schema", "targets"],
    "reports/sandbox_prophecy_daily_chain_v1_latest.json": ["schema", "ok", "n_targets"],
    "reports/sandbox_prophecy_health_v1_latest.json": ["schema", "ok"],
    "reports/sandbox_prophecy_ops_dashboard_v1_latest.json": ["schema", "n_targets", "max_calendar_days"],
    "reports/sandbox_prophecy_operator_digest_v1_latest.json": ["schema", "digest_line_ko"],
    "reports/sandbox_prophecy_human_review_pack_v1_latest.json": ["schema", "status"],
}


def verify(*, manifest_path: Path) -> dict[str, Any]:
    missing: list[str] = []
    bad_schema: list[str] = []
    files: list[dict[str, Any]] = []

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        for f in manifest.get("files") or []:
            if isinstance(f, dict) and f.get("path"):
                rel = str(f["path"])
                p = ROOT / rel.replace("/", "\\") if "\\" in str(ROOT) else ROOT / rel
                files.append({**f, "resolved": str(p)})

    for rel, keys in REQUIRED_KEYS.items():
        p = ROOT / rel.replace("/", "\\") if "\\" in str(ROOT) else ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            bad_schema.append(f"{rel}:json_decode")
            continue
        if not isinstance(doc, dict):
            bad_schema.append(f"{rel}:not_object")
            continue
        for k in keys:
            if k not in doc:
                bad_schema.append(f"{rel}:missing_{k}")

    ok = not missing and not bad_schema
    return {
        "schema": "sandbox_prophecy_artifacts_verify_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "n_missing": len(missing),
        "n_bad_schema": len(bad_schema),
        "missing_paths": missing,
        "bad_schema": bad_schema,
        "manifest_files_count": len(files),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = verify(manifest_path=args.manifest_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"ok={doc['ok']} missing={doc['n_missing']} bad_schema={doc['n_bad_schema']}")
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
