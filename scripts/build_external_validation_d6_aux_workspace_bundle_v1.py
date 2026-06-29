#!/usr/bin/env python3
"""Copy scripts/tests/minimal artifacts from main workspace to aux share (git does not track scripts/)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARE_DEFAULT = Path("Z:/external_validation_d6_aux")
OUT = ROOT / "reports/external_validation_d6_aux_workspace_bundle_v1_latest.json"
BTRACK_PILOT = ROOT / "reports/constitution/btrack_pilot"
CODEBOOK_POINTER = BTRACK_PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"

DOCS_ARTIFACT_NAMES = [
    "edge_encoder_spec_v1_latest.json",
    "compression_b2b_legal_send_signoff_v1_latest.json",
    "compression_b2b_pilot_roi_report_v1_latest.json",
    "a_codeai_public_benchmark_launch_checklist_v1.json",
    "patient_intake_send_gate_v1_latest.json",
    "compression_b2b_recommended_workflow_v1.json",
    "hybrid_b2b_commercialization_pipeline_v1_latest.json",
    "edge_encoder_air_gap_poc_pack_v1_latest.json",
    "rib55_angle_overlay_manifest_v1.json",
    "compression_b2b_prospect_poc_corpus_intake_v1.template.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _robocopy(src: Path, dest: Path, extra: list[str] | None = None) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        "robocopy",
        str(src),
        str(dest),
        "/E",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/nc",
        "/ns",
        "/np",
    ]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return 0 if proc.returncode < 8 else proc.returncode


def _copy_codebook_parity_pack(dest: Path) -> tuple[int, list[str]]:
    """Minimal lexicon SSOT for compression parity on aux (main has full reports/)."""
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if CODEBOOK_POINTER.is_file():
        shutil.copy2(CODEBOOK_POINTER, dest / CODEBOOK_POINTER.name)
        copied.append(CODEBOOK_POINTER.name)
    lexicon_rel: str | None = None
    if CODEBOOK_POINTER.is_file():
        try:
            pointer = json.loads(CODEBOOK_POINTER.read_text(encoding="utf-8"))
            prod = pointer.get("production_ssot") or {}
            raw = prod.get("path")
            if isinstance(raw, str) and raw.strip():
                lexicon_rel = raw.strip().replace("\\", "/")
        except (OSError, json.JSONDecodeError):
            lexicon_rel = None
    if lexicon_rel:
        lex_src = (ROOT / lexicon_rel).resolve()
        if lex_src.is_file():
            shutil.copy2(lex_src, dest / lex_src.name)
            copied.append(lex_src.name)
    return (0 if copied else 1), copied


def build(share: Path) -> dict[str, Any]:
    share.mkdir(parents=True, exist_ok=True)
    scripts_dest = share / "scripts_bundle"
    tests_dest = share / "tests_bundle"
    docs_dest = share / "docs_artifacts_bundle"

    scripts_exit = _robocopy(ROOT / "scripts", scripts_dest)
    tests_exit = _robocopy(ROOT / "tests", tests_dest)
    data_dest = share / "data_bundle"
    docs_md_dest = share / "docs_final_md_bundle"
    data_exit = 0
    if (ROOT / "data/anatomy").is_dir():
        data_exit = max(
            data_exit,
            _robocopy(ROOT / "data/anatomy", data_dest / "anatomy"),
        )
    if (ROOT / "data/compression").is_dir():
        data_exit = max(
            data_exit,
            _robocopy(ROOT / "data/compression", data_dest / "compression"),
        )
    docs_md_exit = 0
    docs_root_dest = share / "docs_root_bundle"
    storage_dest = share / "storage_bundle"
    docs_root_exit = 0
    storage_exit = 0
    if (ROOT / "docs/final").is_dir():
        docs_md_dest.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                "robocopy",
                str(ROOT / "docs/final"),
                str(docs_md_dest),
                "*.md",
                "/S",
                "/NFL",
                "/NDL",
                "/NJH",
                "/NJS",
                "/nc",
                "/ns",
                "/np",
            ],
            capture_output=True,
            text=True,
        )
        docs_md_exit = 0 if proc.returncode < 8 else proc.returncode

    nl_manifest = ROOT / "docs/NotebookLM_sources_manifest.md"
    if nl_manifest.exists():
        docs_root_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nl_manifest, docs_root_dest / nl_manifest.name)

    index_src = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    if index_src.exists():
        meta_dest = storage_dest / "meta"
        meta_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(index_src, meta_dest / index_src.name)
        storage_exit = 0

    docs_dest.mkdir(parents=True, exist_ok=True)
    copied_docs: list[str] = []
    artifacts_root = ROOT / "docs/final/artifacts"
    for name in DOCS_ARTIFACT_NAMES:
        src = artifacts_root / name
        if src.exists():
            shutil.copy2(src, docs_dest / name)
            copied_docs.append(name)

    seed_dir = share / "seed_artifacts"
    if seed_dir.is_dir():
        for item in seed_dir.glob("*.json"):
            dest = docs_dest / item.name
            if not dest.exists() and item.name.startswith("hybrid_"):
                shutil.copy2(item, dest)
                copied_docs.append(item.name)

    btrack_dest = share / "reports_btrack_pilot_bundle"
    btrack_exit, btrack_copied = _copy_codebook_parity_pack(btrack_dest)

    return {
        "schema": "external_validation_d6_aux_workspace_bundle_v1",
        "generated_at_utc": _utc_now(),
        "ok": scripts_exit == 0 and tests_exit == 0 and btrack_exit == 0,
        "share_root": str(share).replace("\\", "/"),
        "scripts_bundle": str(scripts_dest).replace("\\", "/"),
        "tests_bundle": str(tests_dest).replace("\\", "/"),
        "data_bundle": str(data_dest).replace("\\", "/"),
        "docs_final_md_bundle": str(docs_md_dest).replace("\\", "/"),
        "docs_root_bundle": str(docs_root_dest).replace("\\", "/"),
        "storage_bundle": str(storage_dest).replace("\\", "/"),
        "docs_artifacts_bundle": str(docs_dest).replace("\\", "/"),
        "reports_btrack_pilot_bundle": str(btrack_dest).replace("\\", "/"),
        "reports_btrack_pilot_copied": btrack_copied,
        "robocopy_exit_codes": {
            "scripts": scripts_exit,
            "tests": tests_exit,
            "data": data_exit,
            "docs_md": docs_md_exit,
            "storage": storage_exit,
            "reports_btrack_pilot": btrack_exit,
        },
        "docs_artifacts_copied": copied_docs,
        "note": "scripts/ is excluded from git; aux must COPY_WORKSPACE_BUNDLE.cmd before D6.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    args = ap.parse_args()

    doc = build(args.share_root)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT.relative_to(ROOT))}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
