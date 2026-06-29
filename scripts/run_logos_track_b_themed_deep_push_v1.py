#!/usr/bin/env python3
"""Themed Logos Track B deep push — dan_aramaic / john_1_logos (+ citation-lock)."""

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
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"
THEMED_REGISTRY = ART / "logos_concept_bridge_registry_themed_v1_latest.json"
DEFAULT_THEMES = ("dan_aramaic", "john_1_logos")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_presets() -> dict[str, Any]:
    doc = json.loads(PRESETS.read_text(encoding="utf-8"))
    return doc.get("themes") or {}


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _paths_for_theme(theme_id: str) -> dict[str, Path]:
    return {
        "distill": ART / f"logos_deep_research_distill_{theme_id}_latest.json",
        "distill_locked": ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json",
        "commander_json": ART / f"logos_track_b_commander_deep_report_{theme_id}_latest.json",
        "commander_md": REPORTS / f"logos_track_b_commander_deep_report_{theme_id}_latest.md",
        "graphrag": ART / f"logos_subgraph_graphrag_router_{theme_id}_latest.json",
    }


def push_theme(theme_id: str, preset: dict[str, Any]) -> dict[str, Any]:
    paths = _paths_for_theme(theme_id)
    steps: list[dict[str, Any]] = []

    query = str(preset.get("graphrag_query_ko") or "")
    gr_cmd = [
        PY,
        "scripts/run_logos_subgraph_graphrag_router_v1.py",
        "--query",
        query,
        "--registry-json",
        str(THEMED_REGISTRY if THEMED_REGISTRY.is_file() else ART / "logos_concept_bridge_registry_v1_latest.json"),
        "--output-json",
        str(paths["graphrag"]),
        "--top-bridges",
        "3",
    ]
    steps.append(_run("graphrag_router", gr_cmd))
    steps.append(
        _run(
            "graphrag_xref_enrich",
            [
                PY,
                "scripts/enrich_logos_subgraph_router_with_xref_v1.py",
                "--no-run-router",
                "--themes",
                theme_id,
            ],
        )
    )

    vec_build = [
        PY,
        "scripts/build_logos_themed_vector_index_v1.py",
        "--theme",
        theme_id,
        "--try-sentence-transformers",
    ]
    steps.append(_run("themed_vector_build", vec_build))
    steps.append(
        _run(
            "themed_vector_query",
            [PY, "scripts/query_logos_themed_vector_index_v1.py", "--theme", theme_id],
        )
    )

    distill_cmd = [
        PY,
        "scripts/run_lens_logos_deep_fusion.py",
        "--bundle-json",
        str(BUNDLE),
        "--build-id",
        f"themed_{theme_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "--slice-id",
        str(preset.get("slice_id") or f"slice7_{theme_id}"),
        "--enrich-graph",
        "--theme",
        theme_id,
        "--write-template",
        str(paths["distill"]),
    ]
    steps.append(_run("distill_themed", distill_cmd))
    steps.append(
        _run(
            "distill_vector_enrich",
            [
                PY,
                "scripts/enrich_logos_distill_themed_vector_v1.py",
                "--theme",
                theme_id,
                "--in-place",
            ],
        )
    )

    lock_cmd = [
        PY,
        "scripts/run_logos_llm_distill_citation_lock_v1.py",
        "--allow-llm-distill",
        "--input",
        str(paths["distill"]),
        "--output",
        str(paths["distill_locked"]),
    ]
    steps.append(_run("citation_lock", lock_cmd))

    cmd_report = [
        PY,
        "scripts/run_logos_track_b_commander_deep_report_v1.py",
        "--distill-json",
        str(paths["distill_locked"]),
        "--output",
        str(paths["commander_json"]),
    ]
    steps.append(_run("commander_report", cmd_report))

    repro = f"py scripts/run_logos_track_b_themed_deep_push_v1.py --theme {theme_id}"
    md_cmd = [
        PY,
        "scripts/build_logos_track_b_commander_report_md_v1.py",
        "--input",
        str(paths["commander_json"]),
        "--distill",
        str(paths["distill_locked"]),
        "--output",
        str(paths["commander_md"]),
        "--reproduce-cmd",
        repro,
    ]
    steps.append(_run("commander_md", md_cmd))

    distill_doc: dict[str, Any] = {}
    if paths["distill_locked"].is_file():
        try:
            distill_doc = json.loads(paths["distill_locked"].read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            distill_doc = {}

    return {
        "theme_id": theme_id,
        "title_ko": preset.get("title_ko"),
        "artifacts": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in paths.items()},
        "distill_summary": {
            "evidence_ref_count": len(distill_doc.get("evidence_refs") or []),
            "graph_path_count": len(distill_doc.get("graph_paths") or []),
            "citation_locked": (distill_doc.get("citation_lock") or {}).get("locked_count"),
            "llm_invoked": (distill_doc.get("distill_narrative_stub_ko") or {}).get("llm_invoked"),
        },
        "steps": steps,
        "ok": all(s.get("ok") for s in steps),
        "reproduce": repro,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--theme",
        action="append",
        default=[],
        help=f"Theme id (repeatable). Default: {', '.join(DEFAULT_THEMES)}",
    )
    ap.add_argument("--out", type=Path, default=REPORTS / "logos_track_b_themed_deep_push_v1_latest.json")
    args = ap.parse_args()

    themes_map = _load_presets()
    theme_ids = args.theme or list(DEFAULT_THEMES)
    results: list[dict[str, Any]] = []
    for tid in theme_ids:
        if tid not in themes_map:
            print(json.dumps({"ok": False, "error": f"unknown theme: {tid}"}), file=sys.stderr)
            return 2
        results.append(push_theme(tid, themes_map[tid]))

    summary = {
        "schema": "logos_track_b_themed_deep_push_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "themes": results,
        "all_ok": all(r.get("ok") for r in results),
        "reproduce": "py scripts/run_logos_track_b_themed_deep_push_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": summary["all_ok"],
                "out": str(out_path.relative_to(ROOT)),
                "themes": [r["theme_id"] for r in results],
            },
            ensure_ascii=False,
        )
    )
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
