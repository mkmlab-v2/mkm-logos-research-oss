#!/usr/bin/env python3
"""W2 bible_full stack — 35% slice, bloom-primary UI data, kNN spike ingest.

  py scripts/run_logos_bible_full_w2_stack_chain_v1.py
  py scripts/run_logos_bible_full_w2_stack_chain_v1.py --skip-knn-spike
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
OUT = ROOT / "reports/logos_bible_full_w2_stack_chain_v1_latest.json"


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
    out["bloom_primary_ui"] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-canon-pct", type=float, default=35.0)
    ap.add_argument("--skip-corpus-batch", action="store_true")
    ap.add_argument("--skip-bloom-merge", action="store_true")
    ap.add_argument("--skip-knn-spike", action="store_true")
    ap.add_argument("--knn-max-verses", type=int, default=2000)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_corpus_batch:
        steps.append(
            _run(
                "corpus_batch_expand_35",
                [
                    PY,
                    "scripts/expand_logos_bible_full_corpus_batch_v1.py",
                    "--target-canon-pct",
                    str(args.target_canon_pct),
                    "--books",
                    ",".join(
                        [
                            "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth",
                            "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh",
                            "Esth", "Job", "Ps", "Prov", "Eccl", "Song", "Isa", "Jer",
                        ]
                    ),
                ],
                timeout=3600,
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
                    str(args.target_canon_pct),
                ],
                timeout=1800,
            )
        )

    if not args.skip_knn_spike:
        steps.append(
            _run(
                "knn_full_corpus_spike",
                [
                    PY,
                    "scripts/run_logos_candidate_edges_offline_knn_full_corpus_spike_v1.py",
                    "--max-verses",
                    str(args.knn_max_verses),
                    "--max-candidates",
                    "8000",
                    "--survivor-top-n",
                    "200",
                ],
                timeout=3600,
            )
        )
        steps.append(
            _run(
                "knn_spike_w2_ingest",
                [PY, "scripts/ingest_logos_knn_spike_edges_w2_batch_v1.py", "--max-edges", "400"],
                timeout=600,
            )
        )

    steps.extend(
        [
            _run(
                "lemma_edges_w2",
                [
                    PY,
                    "scripts/build_logos_lemma_verse_edges_v1.py",
                    "--graph-max-edges",
                    "12000",
                    "--graph-tokens-per-verse",
                    "2",
                ],
            ),
            _run(
                "preset_expansion",
                [PY, "scripts/run_logos_studio_preset_expansion_chain_v1.py", "--target-count", "90"],
                timeout=900,
            ),
            _run("chapter_presets_merge", [PY, "scripts/merge_logos_studio_graph_chapter_presets_v1.py"]),
            _run("embed_router_merge", [PY, "scripts/merge_logos_studio_embed_router_sidecar_v1.py"]),
            _run(
                "router_stub_patch_all",
                [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py", "--all-presets"],
            ),
            _run("router_stub_coverage", [PY, "scripts/check_logos_studio_graph_slice_router_coverage_v1.py"]),
            _run("bloom_31k_secondary", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]),
            _run("dynamic_subgraph_router", [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"]),
            _run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]),
            _run("governance_hold_gate", [PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"]),
            _run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ]
    )

    failed = [s["step"] for s in steps if not s.get("ok")]
    summary = _audit_summary()
    slice_pct = float(summary.get("studio_graph_slice_pct") or 0)
    w2_gate_ok = slice_pct >= args.target_canon_pct and not failed

    doc = {
        "schema": "logos_bible_full_w2_stack_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": w2_gate_ok,
        "failed_steps": failed,
        "target_canon_pct": args.target_canon_pct,
        "audit_summary": summary,
        "w2_slice_gate": slice_pct >= args.target_canon_pct,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_w2_stack_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "audit_summary": summary}, ensure_ascii=False))
    return 0 if w2_gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
