#!/usr/bin/env python3
"""Build compression B2B SEND-prep counsel export manifest (SHA256 file list)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "compression_b2b_counsel_export_manifest_v1_latest.json"
ENVELOPE_OUT = ART / "compression_b2b_send_prep_counsel_envelope_v1_latest.json"

DEFAULT_PATHS: tuple[str, ...] = (
    "docs/final/artifacts/compression_b2b_send_prep_counsel_envelope_v1_latest.json",
    "docs/final/artifacts/compression_proof_project_closure_v1_latest.json",
    "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json",
    "docs/final/artifacts/compression_pilot_target_intake_kit_v1_latest.json",
    "docs/final/artifacts/compression_b2b_recommended_workflow_v1.json",
    "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json",
    "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
    "docs/final/artifacts/compression_b2b_pilot_onepager_v1.md",
    "docs/final/artifacts/compression_b2b_solo_self_audit_signoff_v1_latest.json",
    "docs/final/artifacts/compression_b2b_prospect_poc_corpus_intake_v1.template.json",
    "docs/final/artifacts/media_fact_sheet_compression_api_v1_latest.md",
    "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json",
    "reports/human_paste/path_a_github_funnel_inbound_appendix_v1_latest.md",
    "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "docs/final/artifacts/compression_sku_separation_brief_v1_latest.md",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(paths: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in paths:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        files.append(
            {
                "path": rel.replace("\\", "/"),
                "size_bytes": src.stat().st_size,
                "sha256": _sha256(src),
            }
        )
    return {
        "schema": "compression_b2b_counsel_export_manifest_v1",
        "generated_at_utc": _utc(),
        "classification": "INTERNAL_ONLY",
        "lane": "compression_b2b_send_prep",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "file_count": len(files),
        "files": files,
        "missing_paths": missing,
        "envelope_ref": ENVELOPE_OUT.relative_to(ROOT).as_posix(),
        "zip_hint": "scripts/build_compression_b2b_counsel_zip_pack_v1.py",
        "boundary_ack": (
            "SEND-prep counsel review pack — not legal approval. "
            "Customer dollar/KRW ROI remains null until masked JSONL intake. "
            "FAIL-COMP-004: do not merge Track A %, handoff %, tenant stub % in one headline."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fail-if-missing", action="store_true")
    args = ap.parse_args()
    doc = build_manifest(list(DEFAULT_PATHS))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": len(doc.get("missing_paths") or []) == 0,
                "file_count": doc["file_count"],
                "missing": doc.get("missing_paths"),
            },
            ensure_ascii=False,
        )
    )
    if args.fail_if_missing and doc.get("missing_paths"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
