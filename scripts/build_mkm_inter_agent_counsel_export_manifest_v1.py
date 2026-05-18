#!/usr/bin/env python3
"""SHA256 manifest of counsel export files for RQ-019 legal review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_handoff_pack_latest.json"
SUBMISSION = ROOT / "docs/final/artifacts/mkm_inter_agent_commander_legal_submission_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_counsel_export_manifest_v1_latest.json"

EXTRA = [
    ROOT / "docs/final/artifacts/mkm_inter_agent_commander_legal_submission_v1_latest.json",
    ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json",
    ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md",
    ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_health_approved_latest.json",
    ROOT / "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
    ROOT / "docs/final/openapi_token_compression_v2_draft.yaml",
    ROOT / "docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json",
    ROOT / "docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_paths() -> list[Path]:
    paths: list[Path] = []
    if HANDOFF.is_file():
        doc = json.loads(HANDOFF.read_text(encoding="utf-8"))
        for rel in doc.get("documents_for_counsel") or []:
            p = ROOT / str(rel)
            if p.is_file():
                paths.append(p)
    for p in EXTRA:
        if p.is_file() and p not in paths:
            paths.append(p)
    if SUBMISSION.is_file() and SUBMISSION not in paths:
        paths.append(SUBMISSION)
    return sorted(paths, key=lambda x: x.as_posix())


def build() -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for p in _collect_paths():
        files.append(
            {
                "path": p.relative_to(ROOT).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": _sha256(p),
            }
        )
    return {
        "schema": "mkm_inter_agent_counsel_export_manifest_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "file_count": len(files),
        "files": files,
        "zip_hint": "Zip listed paths in order for counsel email; do not include .env or secrets.",
        "boundary_ack": "Manifest integrity only; not legal approval.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "file_count": doc["file_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
