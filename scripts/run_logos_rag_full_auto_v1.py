#!/usr/bin/env python3
"""P15 2안 RAG — full auto: index → R6 ko_only pilots → merge → pack → dual eval → bridge → pytest."""
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
ST_SQLITE = PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"
DEFAULT_OUT = PILOT / "comp_logos_rag_full_auto_v1_latest.json"
V3 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json"
V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
MERGED_R6 = PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"
MERGED_R4 = PILOT / "philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-600:],
    }


def _query_set_path() -> Path | None:
    if V3.is_file():
        return V3
    if V4.is_file():
        return V4
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild-index", action="store_true", help="Force ST index rebuild (slow).")
    ap.add_argument(
        "--skip-auto-adjudication",
        action="store_true",
        default=True,
        help="Default True: keep commander/precision gold (no KO top-1 overwrite).",
    )
    ap.add_argument("--skip-pilots", action="store_true", help="Skip 12x R6 ko_only pilot batch.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []
    merged = MERGED_R6 if MERGED_R6.is_file() else MERGED_R4

    if args.rebuild_index or not ST_SQLITE.is_file():
        steps.append(
            _run(
                [py, str(ROOT / "scripts/run_logos_rag_retrieval_round_v1.py"), "--max-verses", "0"],
                "build_st_index",
            )
        )
    else:
        steps.append({"step": "build_st_index", "exit_code": 0, "skipped": "sqlite_exists"})

    qpath = _query_set_path()
    if not args.skip_pilots and qpath:
        doc = json.loads(qpath.read_text(encoding="utf-8-sig"))
        for it in doc.get("items") or []:
            if not isinstance(it, dict):
                continue
            qid = str(it.get("id") or "")
            en = str(it.get("query_en") or "").strip()
            ko = str(it.get("query_ko") or "").strip()
            if not en or not ko:
                continue
            out = PILOT / f"philosophy_lane_rag_pilot_r6_{qid}_ko_only_latest.json"
            steps.append(
                _run(
                    [
                        py,
                        str(ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"),
                        "--query-en",
                        en,
                        "--query-ko",
                        ko,
                        "--query-route",
                        "ko_only",
                        "--rag-lane",
                        "ko_only",
                        "--top-k",
                        "5",
                        "--out",
                        str(out),
                    ],
                    f"pilot_r6_{qid}",
                )
            )
        merged = MERGED_R6
    elif args.skip_pilots:
        steps.append({"step": "pilot_r6_batch", "exit_code": 0, "skipped": True})

    steps.append(_run([py, str(ROOT / "scripts/merge_logos_rag_pilot_ko_v1.py")], "merge_pilots"))
    if MERGED_R6.is_file():
        merged = MERGED_R6

    steps.append(_run([py, str(ROOT / "scripts/bootstrap_logos_query_gold_human_v1.py")], "bootstrap_pack"))
    if not args.skip_auto_adjudication:
        steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_auto_adjudication_v1.py")], "auto_adjudication"))
    steps.append(_run([py, str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py")], "dual_gold_eval"))
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
                "--philosophy-pilot-json",
                str(merged),
                "--calibration-kind",
                "none",
                "--track",
                "Track_C_advisory",
                "--gating",
                "NON_GATING",
                "--out",
                str(BRIDGE),
            ],
            "semantic_rag_bridge_merged",
        )
    )
    steps.append(
        _run(
            [
                py,
                "-m",
                "pytest",
                "tests/test_logos_rag_query_route_v1.py",
                "tests/test_logos_semantic_query_set_v4_ko_en_v1.py",
                "tests/test_logos_rag_retrieval_round_v1.py",
                "tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py",
                "-q",
            ],
            "pytest_smoke",
        )
    )

    eval_summary: dict[str, Any] = {}
    dep = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
    if dep.is_file():
        eval_summary = json.loads(dep.read_text(encoding="utf-8-sig")).get("summary") or {}

    bridge_count = 0
    if BRIDGE.is_file():
        bridge_count = len(json.loads(BRIDGE.read_text(encoding="utf-8-sig")).get("rag_evidence") or [])

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    doc = {
        "schema": "comp_logos_rag_full_auto_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "pilot_lane": "r6_ko_only" if MERGED_R6.is_file() else "r4_ko_legacy",
        "query_set": str(qpath) if qpath else None,
        "ok": not failed,
        "steps": steps,
        "dual_eval_summary": eval_summary,
        "bridge_rag_evidence_count": bridge_count,
        "merged_pilot": str(merged),
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "out": str(args.output_json),
                "failed": len(failed),
                "dual_eval": eval_summary,
                "bridge_evidence": bridge_count,
                "pilot_lane": doc["pilot_lane"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
