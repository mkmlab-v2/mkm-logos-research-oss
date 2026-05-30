#!/usr/bin/env python3
"""Full-corpus (31k) offline 4D kNN spike — separate staging paths, no canonical merge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD = ROOT / "scripts/build_logos_candidate_edges_offline_knn_v1.py"
REPORT = ROOT / "scripts/report_logos_candidate_edges_quality_v1.py"
SELECT = ROOT / "scripts/select_logos_candidate_edge_survivors_v1.py"

FULL_CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_full_corpus_spike_v1.jsonl"
FULL_BUILD_REPORT = ROOT / "docs/final/artifacts/logos_candidate_edges_offline_knn_full_corpus_spike_v1_latest.json"
FULL_QUALITY = ROOT / "docs/final/artifacts/logos_candidate_edges_quality_full_corpus_spike_v1_latest.json"
FULL_SURVIVORS = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_full_corpus_spike_v1_latest.json"
FULL_PRUNED = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_full_corpus_spike_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edges_offline_knn_full_corpus_spike_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-verses", type=int, default=0, help="0 = full corpus (~31102)")
    ap.add_argument("--max-candidates", type=int, default=20000)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--min-cosine", type=float, default=0.92)
    ap.add_argument("--survivor-top-n", type=int, default=200)
    ap.add_argument("--survivor-max-cosine", type=float, default=0.998)
    ap.add_argument("--survivor-max-per-src", type=int, default=1)
    ap.add_argument("--build-timeout-sec", type=int, default=3600)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    code, tail = _run(
        [
            sys.executable,
            str(BUILD),
            "--max-verses",
            str(int(args.max_verses)),
            "--top-k",
            str(int(args.top_k)),
            "--min-cosine",
            str(float(args.min_cosine)),
            "--max-candidates",
            str(int(args.max_candidates)),
            "--output-jsonl",
            str(FULL_CANDIDATES),
            "--report-json",
            str(FULL_BUILD_REPORT),
        ],
        timeout=int(args.build_timeout_sec),
    )
    steps.append({"step": "build_full_corpus_candidates", "exit_code": code, "tail": tail[-800:]})
    if code != 0:
        exit_code = code

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(REPORT),
                "--edges-jsonl",
                str(FULL_CANDIDATES),
                "--output-json",
                str(FULL_QUALITY),
            ]
        )
        steps.append({"step": "quality_report", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(SELECT),
                "--edges-jsonl",
                str(FULL_CANDIDATES),
                "--output-json",
                str(FULL_SURVIVORS),
                "--pruned-jsonl-out",
                str(FULL_PRUNED),
                "--top-n",
                str(int(args.survivor_top_n)),
                "--max-per-src",
                str(int(args.survivor_max_per_src)),
                "--max-cosine",
                str(float(args.survivor_max_cosine)),
                "--min-cosine",
                str(float(args.min_cosine)),
            ]
        )
        steps.append({"step": "lora_strict_survivor_select", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    build_doc: dict = {}
    qual_doc: dict = {}
    surv_doc: dict = {}
    if FULL_BUILD_REPORT.is_file():
        try:
            build_doc = json.loads(FULL_BUILD_REPORT.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    if FULL_QUALITY.is_file():
        try:
            qual_doc = json.loads(FULL_QUALITY.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    if FULL_SURVIVORS.is_file():
        try:
            surv_doc = json.loads(FULL_SURVIVORS.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    doc = {
        "schema": "logos_candidate_edges_offline_knn_full_corpus_spike_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "max_verses": int(args.max_verses),
        "exit_code": exit_code,
        "build_stats": build_doc.get("stats"),
        "quality_saturation_warning": qual_doc.get("saturation_warning"),
        "survivor_count": (surv_doc.get("stats") or {}).get("survivor_count"),
        "steps": steps,
        "artifacts": {
            "candidate_jsonl": str(FULL_CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
            "build_report_json": str(FULL_BUILD_REPORT.relative_to(ROOT)).replace("\\", "/"),
            "quality_json": str(FULL_QUALITY.relative_to(ROOT)).replace("\\", "/"),
            "survivors_json": str(FULL_SURVIVORS.relative_to(ROOT)).replace("\\", "/"),
        },
        "disclaimer_ko": "full corpus spike — production candidate/survivor/canonical 경로 미덮어씀.",
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
