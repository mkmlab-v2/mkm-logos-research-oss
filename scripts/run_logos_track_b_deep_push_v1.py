#!/usr/bin/env python3
"""High-delegation Logos Track B deep push — corpus→graph→distill→commander report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/logos_track_b_deep_push_v1_latest.json"
DISTILL_LATEST = ROOT / "docs/final/artifacts/logos_deep_research_distill_latest.json"
DISTILL_CHAIN = ROOT / "docs/final/artifacts/logos_deep_research_distill_track_b_chain_v1_latest.json"
BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
COMMANDER_JSON = ROOT / "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json"
COMMANDER_MD = ROOT / "reports/logos_track_b_commander_deep_report_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-600:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-ann-lite", action="store_true")
    ap.add_argument("--skip-insight-bundle", action="store_true")
    ap.add_argument("--graphrag-query-id", default="q01")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    for name, script in [
        ("manifest", "scripts/build_logos_corpus_manifest_v1.py"),
        ("graph_bundle", "scripts/build_logos_corpus_graph_bundle_v1.py"),
        ("policy_readiness", "scripts/report_logos_track_b_policy_readiness_v1.py"),
    ]:
        steps.append(_run(name, [PY, script]))

    steps.append(_run("vector_manifest", [PY, "scripts/build_logos_vector_index_manifest_v1.py"]))

    if not args.skip_ann_lite:
        steps.append(
            _run(
                "ann_lite",
                [PY, "scripts/build_logos_vector_index_ann_lite_v1.py", "--max-verses", "1500"],
            )
        )
        smoke_out = ROOT / "docs/final/artifacts/logos_vector_ann_lite_query_smoke_latest.json"
        smoke_args = [
            PY,
            "scripts/query_logos_vector_index_ann_lite_v1.py",
            "--query",
            "logos_track_b_deep_push_smoke",
            "--top-k",
            "3",
            "--output-json",
            str(smoke_out),
        ]
        steps.append(_run("ann_lite_query_smoke", smoke_args))

    steps.append(
        _run(
            "graphrag_router",
            [
                PY,
                "scripts/run_logos_subgraph_graphrag_router_v1.py",
                "--query-id",
                args.graphrag_query_id,
            ],
        )
    )

    steps.append(_run("lens_logos", [PY, "scripts/run_lens_logos.py"]))

    distill_cmd = [
        PY,
        "scripts/run_lens_logos_deep_fusion.py",
        "--bundle-json",
        str(BUNDLE),
        "--build-id",
        f"deep_push_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "--slice-id",
        "slice6_graph_enriched_distill",
        "--enrich-graph",
        "--write-template",
        str(DISTILL_LATEST),
    ]
    vm = ROOT / "docs/final/artifacts/logos_vector_index_manifest_v1_latest.json"
    ar = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"
    qs = ROOT / "docs/final/artifacts/logos_vector_ann_lite_query_smoke_latest.json"
    for flag, path in [
        ("--vector-manifest-json", vm),
        ("--ann-lite-report-json", ar),
        ("--ann-lite-query-smoke-json", qs),
    ]:
        if path.is_file():
            distill_cmd += [flag, str(path)]
    steps.append(_run("distill_enriched", distill_cmd))

    DISTILL_CHAIN.parent.mkdir(parents=True, exist_ok=True)
    if DISTILL_LATEST.is_file():
        DISTILL_CHAIN.write_text(DISTILL_LATEST.read_text(encoding="utf-8"), encoding="utf-8")

    steps.append(
        _run(
            "deep_fusion_job",
            [
                PY,
                "scripts/run_logos_track_b_deep_fusion_job_v1.py",
                "--write-distill-template",
                str(DISTILL_CHAIN),
            ],
        )
    )

    if not args.skip_insight_bundle:
        steps.append(_run("insight_bundle", [PY, "scripts/build_logos_insight_bundle_v1.py"]))

    steps.append(
        _run(
            "commander_report",
            [
                PY,
                "scripts/run_logos_track_b_commander_deep_report_v1.py",
                "--distill-json",
                str(DISTILL_LATEST),
            ],
        )
    )
    steps.append(
        _run(
            "commander_report_md",
            [PY, "scripts/build_logos_track_b_commander_report_md_v1.py"],
        )
    )

    distill_doc: dict[str, Any] = {}
    if DISTILL_LATEST.is_file():
        try:
            distill_doc = json.loads(DISTILL_LATEST.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            distill_doc = {}

    summary = {
        "schema": "logos_track_b_deep_push_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "lane": "logos_deep_research",
        "artifacts": {
            "distill_latest": str(DISTILL_LATEST.relative_to(ROOT)).replace("\\", "/"),
            "commander_json": str(COMMANDER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "commander_md": str(COMMANDER_MD.relative_to(ROOT)).replace("\\", "/"),
            "graphrag_router": "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json",
        },
        "distill_summary": {
            "evidence_ref_count": len(distill_doc.get("evidence_refs") or []),
            "graph_path_count": len(distill_doc.get("graph_paths") or []),
            "epistemic_uncertainty": distill_doc.get("epistemic_uncertainty"),
            "insufficient_evidence": (distill_doc.get("veto_flags") or {}).get(
                "insufficient_evidence"
            ),
            "review_gate_status": (distill_doc.get("review_gate") or {}).get("status"),
        },
        "steps": steps,
        "reproduce": "py scripts/run_logos_track_b_deep_push_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    all_ok = all(s.get("ok") for s in steps)
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(out_path.relative_to(ROOT)),
                "evidence_refs": summary["distill_summary"]["evidence_ref_count"],
                "graph_paths": summary["distill_summary"]["graph_path_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
