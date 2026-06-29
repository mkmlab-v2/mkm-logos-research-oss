#!/usr/bin/env python3
"""Ensure LOGOS RAG 4e lexical+semantic artifacts exist before envelope/closure (B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
V3_BI = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json"
ST_SQLITE = PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"
DUAL_EVAL = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
DEFAULT_OUT = PILOT / "logos_rag_4e_presence_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(py: str, script: str, *extra: str) -> dict[str, Any]:
    cmd = [py, str(ROOT / script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "script": script,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-400:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rebuild-index", action="store_true")
    ap.add_argument("--skip-dual-eval", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(_run(py, "scripts/bootstrap_logos_semantic_query_set_v4_from_gold_human_v1.py"))
    if steps[-1]["exit_code"] != 0:
        return 2

    steps.append(_run(py, "scripts/bootstrap_logos_semantic_query_set_v3_bilingual_v1.py"))
    if steps[-1]["exit_code"] != 0:
        return 2

    need_index = args.rebuild_index or not ST_SQLITE.is_file()
    if need_index:
        steps.append(_run(py, "scripts/run_logos_rag_retrieval_round_v1.py", "--max-verses", "0"))
        if steps[-1]["exit_code"] != 0:
            return 2
    else:
        steps.append({"script": "run_logos_rag_retrieval_round_v1", "skipped": "sqlite_exists"})

    if not args.skip_dual_eval and not DUAL_EVAL.is_file():
        steps.append(_run(py, "scripts/run_logos_rag_dual_gold_eval_v1.py"))
        if steps[-1]["exit_code"] != 0:
            return 2
    elif DUAL_EVAL.is_file():
        steps.append({"script": "run_logos_rag_dual_gold_eval_v1", "skipped": "dual_eval_exists"})

    present = {
        "v3_bilingual": V3_BI.is_file(),
        "st_sqlite": ST_SQLITE.is_file(),
        "dual_eval": DUAL_EVAL.is_file(),
    }
    doc = {
        "schema": "logos_rag_4e_presence_chain_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "steps": steps,
        "present": present,
        "ok": all(present.values()),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "present": present, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if doc["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
