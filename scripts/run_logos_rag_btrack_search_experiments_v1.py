#!/usr/bin/env python3
"""Parallel B-track retrieval experiments bundle (no L3 prod swap)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_OUT = PILOT / "comp_logos_rag_btrack_search_experiments_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"step": label, "exit_code": proc.returncode, "stderr_tail": (proc.stderr or "")[-400:] if proc.returncode else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-r6-pilots", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps = [
        _run([py, str(ROOT / "scripts/run_logos_rag_retrieval_sweep_r2_v1.py")], "r2_sweep"),
        _run([py, str(ROOT / "scripts/run_logos_rag_hybrid_improvement_sweep_v1.py")], "hybrid_sweep"),
        _run([py, str(ROOT / "scripts/run_logos_rag_retrieval_v5_v3_bilingual_v1.py")], "v5_bilingual"),
        _run([py, str(ROOT / "scripts/run_logos_rag_retrieval_eval_r3_v1.py")], "eval_r3"),
        _run(
            [
                py,
                str(ROOT / "scripts/run_logos_semantic_model_ab_sweep_v1.py"),
                "--sqlite",
                str(PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"),
                "--query-set-json",
                str(ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"),
                "--models",
                "sentence-transformers/all-MiniLM-L6-v2,sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            ],
            "model_ab_st_u",
        ),
    ]
    if not args.skip_r6_pilots:
        steps.append(
            _run([py, str(ROOT / "scripts/run_logos_rag_r6_ko_only_lane_v1.py"), "--skip-signoff"], "r6_lane")
        )

    summaries: dict[str, Any] = {}
    for name, path in (
        ("r2", PILOT / "comp_logos_rag_retrieval_sweep_r2_latest.json"),
        ("hybrid", PILOT / "comp_logos_rag_hybrid_improvement_sweep_v1_latest.json"),
        ("v5", PILOT / "comp_logos_rag_retrieval_v5_v3_bilingual_v1_latest.json"),
        ("r3", PILOT / "comp_logos_rag_retrieval_eval_r3_latest.json"),
        ("model_ab", ROOT / "docs/final/artifacts/logos_semantic_model_ab_sweep_latest.json"),
    ):
        if path.is_file():
            summaries[name] = json.loads(path.read_text(encoding="utf-8-sig"))

    failed = [s["step"] for s in steps if s.get("exit_code") not in (0, None)]
    doc = {
        "schema": "comp_logos_rag_btrack_search_experiments_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "ok": not failed,
        "steps": steps,
        "summaries": summaries,
        "track_wall": {"l3_prod_swap": False, "a_track_auto_promotion": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not failed, "failed": failed, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
