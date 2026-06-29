#!/usr/bin/env python3
"""[HYPO] Minimal workspace bundle for aux NG-40 shard (faster than full scripts mirror)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nextgen_aux_workspace_bundle_v1_latest.json"
SHARE_DEFAULT = Path("Z:/nextgen_cpu_aux/workspace_bundle")
BTRACK_PILOT = ROOT / "reports/constitution/btrack_pilot"
CODEBOOK_POINTER = BTRACK_PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
MYEONGNI_PROBE = ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json"

ARTIFACT_NAMES = [
    "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
    "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json",
    "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
]


def _utc() -> str:
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
        "/XD",
        "__pycache__",
        ".venv",
        "node_modules",
        ".git",
    ]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return 0 if proc.returncode < 8 else proc.returncode


def build(share: Path) -> dict[str, Any]:
    share.mkdir(parents=True, exist_ok=True)
    scripts_dest = share / "scripts_bundle"
    docs_dest = share / "docs_artifacts_bundle"
    btrack_dest = share / "reports_btrack_pilot_bundle"

    scripts_exit = _robocopy(ROOT / "scripts", scripts_dest)
    docs_dest.mkdir(parents=True, exist_ok=True)
    copied_docs: list[str] = []
    for name in ARTIFACT_NAMES:
        src = ROOT / "docs/final/artifacts" / name
        if src.is_file():
            shutil.copy2(src, docs_dest / name)
            copied_docs.append(name)

    btrack_dest.mkdir(parents=True, exist_ok=True)
    btrack_copied: list[str] = []
    if CODEBOOK_POINTER.is_file():
        shutil.copy2(CODEBOOK_POINTER, btrack_dest / CODEBOOK_POINTER.name)
        btrack_copied.append(CODEBOOK_POINTER.name)
        try:
            pointer = json.loads(CODEBOOK_POINTER.read_text(encoding="utf-8"))
            lex_rel = ((pointer.get("production_ssot") or {}).get("path") or "").strip()
            if lex_rel:
                lex_src = (ROOT / lex_rel.replace("\\", "/")).resolve()
                if lex_src.is_file():
                    shutil.copy2(lex_src, btrack_dest / lex_src.name)
                    btrack_copied.append(lex_src.name)
        except (OSError, json.JSONDecodeError):
            pass

    data_exit = 0
    if (ROOT / "data/compression").is_dir():
        data_exit = _robocopy(ROOT / "data/compression", share / "data_bundle/compression")

    myeongni_copied: list[str] = []
    if MYEONGNI_PROBE.is_file():
        myeongni_dest = share / "data_bundle/myeongni"
        myeongni_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MYEONGNI_PROBE, myeongni_dest / MYEONGNI_PROBE.name)
        myeongni_copied.append(MYEONGNI_PROBE.name)

    return {
        "schema": "nextgen_aux_workspace_bundle_v1",
        "generated_at_utc": _utc(),
        "ok": scripts_exit == 0 and bool(copied_docs),
        "share_root": str(share).replace("\\", "/"),
        "scripts_bundle": str(scripts_dest).replace("\\", "/"),
        "docs_artifacts_bundle": str(docs_dest).replace("\\", "/"),
        "reports_btrack_pilot_bundle": str(btrack_dest).replace("\\", "/"),
        "robocopy_exit_codes": {"scripts": scripts_exit, "data": data_exit},
        "docs_artifacts_copied": copied_docs,
        "reports_btrack_pilot_copied": btrack_copied,
        "myeongni_probe_copied": myeongni_copied,
        "purpose": "aux C:\\workspace sync for RUN_NG40_SHARD_ON_AUX",
        "copy_cmd_on_aux": "Z:\\nextgen_cpu_aux\\COPY_WORKSPACE_BUNDLE.cmd",
        "note": "scripts-only mirror with exclusions; no full git clone on aux",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    args = ap.parse_args()

    if not args.share_root.parent.exists():
        print(json.dumps({"error": "share_not_mounted", "path": str(args.share_root.parent)}))
        return 1

    doc = build(args.share_root)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
