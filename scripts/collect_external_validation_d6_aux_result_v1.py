#!/usr/bin/env python3
"""Collect aux D6 result from Z: share into main reports and refresh closure."""
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
RESULT_NAME = "aux_d6_result_v1_latest.json"
OUT_MAIN = ROOT / "reports/external_validation_d6_independent_rehearsal_v1_latest.json"
OUT_AUX_COPY = ROOT / "reports/external_validation_d6_aux_true_third_party_v1_latest.json"
OUT_AUX_FULL_COPY = ROOT / "reports/external_validation_d6_aux_full_chain_v1_latest.json"
OUT = ROOT / "reports/external_validation_d6_aux_collect_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect(share: Path, *, result_name: str, promote: bool, rebuild_closure: bool) -> dict[str, Any]:
    result_path = share / result_name
    if not result_path.exists():
        raise SystemExit(f"missing aux result: {result_path}")

    doc = json.loads(result_path.read_text(encoding="utf-8"))
    aux_copy = OUT_AUX_FULL_COPY if "full_result" in result_name else OUT_AUX_COPY
    aux_copy.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if promote:
        shutil.copy2(result_path, OUT_MAIN)

    closure_exit = None
    if rebuild_closure and doc.get("status") == "ok":
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_external_validation_week2_closure_v1.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        closure_exit = proc.returncode

    return {
        "schema": "external_validation_d6_aux_collect_v1",
        "generated_at_utc": _utc_now(),
        "ok": doc.get("status") == "ok",
        "share_root": str(share).replace("\\", "/"),
        "aux_result": str(result_path).replace("\\", "/"),
        "promoted_to_main": promote,
        "main_report": str(OUT_MAIN.relative_to(ROOT)) if promote else None,
        "aux_copy": str(aux_copy.relative_to(ROOT)),
        "rehearsal_class": doc.get("rehearsal_class"),
        "chain_mode": doc.get("chain_mode"),
        "result_file": result_name,
        "operator": doc.get("operator"),
        "host": doc.get("host"),
        "aux_git_head": doc.get("aux_git_head"),
        "gate_match": doc.get("gate_match"),
        "summary": doc.get("summary"),
        "closure_rebuild_exit_code": closure_exit,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    ap.add_argument("--result-name", default=RESULT_NAME)
    ap.add_argument("--no-promote", action="store_true")
    ap.add_argument("--no-rebuild-closure", action="store_true")
    args = ap.parse_args()

    doc = collect(
        args.share_root,
        result_name=args.result_name,
        promote=not args.no_promote,
        rebuild_closure=not args.no_rebuild_closure,
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT.relative_to(ROOT))}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
