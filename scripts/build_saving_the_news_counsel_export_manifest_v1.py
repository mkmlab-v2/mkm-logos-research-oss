#!/usr/bin/env python3
"""Build Saving the News counsel export manifest (SHA256 file list)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "saving_the_news_counsel_export_manifest_v1_latest.json"
HANDOFF_OUT = ART / "saving_the_news_legal_counsel_handoff_v1_latest.json"

DEFAULT_PATHS: tuple[str, ...] = (
    "docs/research/saving_the_news_blueprint_v1.md",
    "docs/research/saving_the_news_perplexity_external_grounding_v1.md",
    "docs/final/artifacts/track_c_saving_the_news_offer_onepager_v1_latest.md",
    "docs/final/artifacts/saving_the_news_phase1_poc_scope_v1_latest.json",
    "docs/final/artifacts/saving_the_news_internal_roadmap_closure_v1_latest.json",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "docs/final/artifacts/saving_the_news_news_rt_bench_result_v1_latest.json",
    "docs/final/artifacts/saving_the_news_finance_hypo_status_v1_latest.json",
    "docs/final/artifacts/saving_the_news_matrix_panel_slice_v1_latest.json",
    "docs/final/artifacts/saving_the_news_commander_next_actions_v1_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


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
        "schema": "saving_the_news_counsel_export_manifest_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "research_only",
        "ready_for_external_send": False,
        "file_count": len(files),
        "files": files,
        "missing_paths": missing,
        "handoff_ref": _display_path(HANDOFF_OUT),
        "zip_hint": "scripts/build_saving_the_news_counsel_zip_pack_v1.py",
        "boundary_ack": "Manifest integrity only; not COUNSEL_REVIEWED or external send authorization.",
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
