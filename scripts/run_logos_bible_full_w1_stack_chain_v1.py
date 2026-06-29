#!/usr/bin/env python3
"""W1 bible_full stack — corpus batch ≥10% slice, lemma scale, presets, audit.

  py scripts/run_logos_bible_full_w1_stack_chain_v1.py
  py scripts/run_logos_bible_full_w1_stack_chain_v1.py --skip-corpus-batch
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
OUT = ROOT / "reports/logos_bible_full_w1_stack_chain_v1_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-corpus-batch", action="store_true")
    ap.add_argument("--target-canon-pct", type=float, default=10.0)
    ap.add_argument("--preset-target", type=int, default=70)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_corpus_batch:
        steps.append(
            _run(
                "graph_slice_base",
                [
                    PY,
                    "scripts/build_showroom_meaning_topology_graph_slice_v1.py",
                    "--seed-count",
                    "48",
                    "--max-nodes",
                    "420",
                    "--max-edges",
                    "900",
                ],
            )
        )
        steps.append(
            _run(
                "corpus_batch_expand",
                [
                    PY,
                    "scripts/expand_logos_bible_full_corpus_batch_v1.py",
                    "--target-canon-pct",
                    str(args.target_canon_pct),
                ],
                timeout=3600,
            )
        )

    steps.extend(
        [
            _run(
                "lemma_edges_w1",
                [
                    PY,
                    "scripts/build_logos_lemma_verse_edges_v1.py",
                    "--graph-max-edges",
                    "3500",
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
            _run("chapter_presets_merge", [PY, "scripts/merge_logos_studio_graph_chapter_presets_v1.py"]),
            _run("embed_router_merge", [PY, "scripts/merge_logos_studio_embed_router_sidecar_v1.py"]),
            _run("router_stub_patch_all", [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py", "--all-presets"]),
            _run("router_stub_coverage", [PY, "scripts/check_logos_studio_graph_slice_router_coverage_v1.py"]),
            _run("bloom_31k_secondary", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]),
            _run("dynamic_subgraph_router", [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"]),
            _run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]),
            _run("governance_hold_gate", [PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"]),
            _run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ]
    )

    failed = [s["step"] for s in steps if not s.get("ok")]
    audit_path = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
    audit_summary: dict[str, Any] = {}
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
        layers = audit.get("layers") or []
        if isinstance(layers, dict):
            layer_iter = layers.items()
        else:
            layer_iter = ((ly.get("id"), ly) for ly in layers if isinstance(ly, dict))
        for lid, ly in layer_iter:
            if not isinstance(ly, dict):
                continue
            audit_summary[f"{lid}_pct"] = ly.get("canon_coverage_pct") or ly.get("coverage_pct")

    doc = {
        "schema": "logos_bible_full_w1_stack_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(failed) == 0,
        "failed_steps": failed,
        "target_canon_pct": args.target_canon_pct,
        "audit_summary": audit_summary,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_w1_stack_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "audit_summary": audit_summary}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
