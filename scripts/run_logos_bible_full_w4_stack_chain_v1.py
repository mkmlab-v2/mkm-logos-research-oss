#!/usr/bin/env python3
"""W4 bible_full stack — 95% slice, 90% meaning, 80% lemma, quality pass.

  py scripts/run_logos_bible_full_w4_stack_chain_v1.py --skip-knn-spike
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_bible_full_w4_stack_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 10800) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if len(tail) > 2000:
        tail = tail[-2000:]
    return {"step": name, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail}


def _audit_summary() -> dict[str, Any]:
    audit_path = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
    if not audit_path.is_file():
        return {}
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    out: dict[str, Any] = {}
    for ly in audit.get("layers") or []:
        if isinstance(ly, dict) and ly.get("id"):
            out[f"{ly['id']}_pct"] = ly.get("canon_coverage_pct")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice-pct", type=float, default=95.0)
    ap.add_argument("--lemma-graph-max-edges", type=int, default=45000)
    ap.add_argument("--skip-corpus-batch", action="store_true")
    ap.add_argument("--skip-bloom-merge", action="store_true")
    ap.add_argument("--skip-knn-spike", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_corpus_batch:
        steps.append(
            _run(
                "corpus_batch_expand_95",
                [
                    PY,
                    "scripts/expand_logos_bible_full_corpus_batch_v1.py",
                    "--target-canon-pct",
                    str(args.slice_pct),
                ],
                timeout=10800,
            )
        )

    if not args.skip_bloom_merge:
        steps.append(
            _run(
                "bloom_chapter_stub_merge",
                [
                    PY,
                    "scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py",
                    "--target-canon-pct",
                    str(args.slice_pct),
                ],
                timeout=3600,
            )
        )

    steps.extend(
        [
            _run(
                "lemma_edges_w4",
                [
                    PY,
                    "scripts/build_logos_lemma_verse_edges_v1.py",
                    "--graph-max-edges",
                    str(args.lemma_graph_max_edges),
                ],
            ),
            _run("book_anchor_presets", [PY, "scripts/merge_logos_studio_book_anchor_presets_v1.py"]),
            _run("chapter_presets_merge", [PY, "scripts/merge_logos_studio_graph_chapter_presets_v1.py"]),
            _run("embed_router_merge", [PY, "scripts/merge_logos_studio_embed_router_sidecar_v1.py"]),
            _run(
                "router_stub_patch_all",
                [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py", "--all-presets"],
            ),
            _run("router_stub_coverage", [PY, "scripts/check_logos_studio_graph_slice_router_coverage_v1.py"]),
            _run("bloom_31k_secondary", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]),
            _run(
                "dynamic_subgraph_router",
                [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py", "--max-presets", "220"],
            ),
            _run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]),
            _run("governance_hold_gate", [PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"]),
            _run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ]
    )

    failed = [s["step"] for s in steps if not s.get("ok")]
    summary = _audit_summary()
    slice_pct = float(summary.get("studio_graph_slice_pct") or 0)
    meaning_pct = float(summary.get("bible_meaning_graph_nodes_pct") or 0)
    lemma_pct = float(summary.get("lemma_verse_edges_pct") or 0)

    gates = {
        "slice_ge_90": slice_pct >= 90.0,
        "meaning_ge_85": meaning_pct >= 85.0,
        "lemma_ge_70": lemma_pct >= 70.0,
        "no_failed_steps": not failed,
    }
    ok = gates["no_failed_steps"] and slice_pct >= 90.0

    doc = {
        "schema": "logos_bible_full_w4_stack_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "failed_steps": failed,
        "gates": gates,
        "audit_summary": summary,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_w4_stack_chain_v1.py --skip-knn-spike",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "failed": failed, "gates": gates, "audit_summary": summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
