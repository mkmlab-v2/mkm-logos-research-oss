#!/usr/bin/env python3
"""W3 bible_full stack — 70% slice, 50% meaning, 30% lemma, 66-book presets.

  py scripts/run_logos_bible_full_w3_stack_chain_v1.py
  py scripts/run_logos_bible_full_w3_stack_chain_v1.py --skip-knn-spike
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
OUT = ROOT / "reports/logos_bible_full_w3_stack_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 7200) -> dict[str, Any]:
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
    infra = audit.get("infrastructure") or {}
    out["preset_count"] = (
        next(
            (ly.get("preset_count") for ly in audit.get("layers") or [] if ly.get("id") == "studio_qa_presets"),
            None,
        )
    )
    out["dynamic_router_routes"] = infra.get("dynamic_subgraph_route_count")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice-pct", type=float, default=70.0)
    ap.add_argument("--meaning-pct", type=float, default=50.0)
    ap.add_argument("--lemma-graph-max-edges", type=int, default=25000)
    ap.add_argument("--preset-target", type=int, default=120)
    ap.add_argument("--skip-corpus-batch", action="store_true")
    ap.add_argument("--skip-bloom-merge", action="store_true")
    ap.add_argument("--skip-knn-spike", action="store_true")
    ap.add_argument("--knn-max-verses", type=int, default=3000)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_corpus_batch:
        steps.append(
            _run(
                "corpus_batch_expand_70",
                [
                    PY,
                    "scripts/expand_logos_bible_full_corpus_batch_v1.py",
                    "--target-canon-pct",
                    str(args.slice_pct),
                ],
                timeout=7200,
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

    if not args.skip_knn_spike:
        steps.append(
            _run(
                "knn_spike",
                [
                    PY,
                    "scripts/run_logos_candidate_edges_offline_knn_full_corpus_spike_v1.py",
                    "--max-verses",
                    str(args.knn_max_verses),
                    "--max-candidates",
                    "12000",
                    "--survivor-top-n",
                    "300",
                ],
                timeout=7200,
            )
        )
        steps.append(
            _run(
                "knn_ingest",
                [PY, "scripts/ingest_logos_knn_spike_edges_w2_batch_v1.py", "--max-edges", "600"],
                timeout=600,
            )
        )

    steps.extend(
        [
            _run(
                "lemma_edges_w3",
                [
                    PY,
                    "scripts/build_logos_lemma_verse_edges_v1.py",
                    "--graph-max-edges",
                    str(args.lemma_graph_max_edges),
                    "--graph-tokens-per-verse",
                    "2",
                ],
            ),
            _run(
                "preset_expansion",
                [
                    PY,
                    "scripts/run_logos_studio_preset_expansion_chain_v1.py",
                    "--target-count",
                    str(args.preset_target),
                ],
                timeout=900,
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
                [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py", "--max-presets", "200"],
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
        "slice_ge_70": slice_pct >= args.slice_pct,
        "meaning_ge_50": meaning_pct >= args.meaning_pct - 5.0,
        "lemma_ge_25": lemma_pct >= 25.0,
        "no_failed_steps": not failed,
    }
    ok = all(gates.values())

    doc = {
        "schema": "logos_bible_full_w3_stack_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "failed_steps": failed,
        "gates": gates,
        "audit_summary": summary,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_w3_stack_chain_v1.py --skip-knn-spike",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "failed": failed, "gates": gates, "audit_summary": summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
