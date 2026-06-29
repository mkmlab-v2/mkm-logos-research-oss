#!/usr/bin/env python3
"""Logos bible_full AUTO chain — KRV ingest, graph scale, presets, audit (no CSS/design).

  py scripts/run_logos_bible_full_auto_chain_v1.py
  py scripts/run_logos_bible_full_auto_chain_v1.py --skip-krv-fetch
  py scripts/run_logos_bible_full_auto_chain_v1.py --krv-only
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
OUT = ROOT / "reports/logos_bible_full_auto_chain_v1_latest.json"
KRV_JSONL = ROOT / "data/logos/krv_verses_v1.jsonl"


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
    if len(tail) > 1500:
        tail = tail[-1500:]
    return {"step": name, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail}


def _krv_verse_count() -> int:
    if not KRV_JSONL.is_file():
        return 0
    n = 0
    for line in KRV_JSONL.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-krv-fetch", action="store_true")
    ap.add_argument("--krv-only", action="store_true")
    ap.add_argument("--min-krv-verses", type=int, default=30000)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_krv_fetch:
        existing = _krv_verse_count()
        if existing < args.min_krv_verses:
            steps.append(
                _run(
                    "krv_fetch_bskorea",
                    [PY, "scripts/fetch_logos_krv_corpus_from_bskorea_v1.py", "--sleep-ms", "280"],
                    timeout=7200,
                )
            )
        else:
            steps.append({"step": "krv_fetch_bskorea", "exit_code": 0, "ok": True, "tail": f"skip_existing_{existing}"})

        steps.append(_run("krv_citation_shard", [PY, "scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py"]))
        steps.append(_run("krv_gap_backfill", [PY, "scripts/backfill_logos_krv_corpus_gaps_v1.py"], timeout=7200))
        steps.append(
            _run(
                "krv_versification_sidecar",
                [PY, "scripts/build_logos_krv_versification_sidecar_v1.py", "--apply-to-corpus"],
            )
        )
        steps.append(_run("krv_citation_shard_post_proxy", [PY, "scripts/build_logos_studio_verse_citation_shard_from_krv_corpus_v1.py"]))

    if args.krv_only:
        doc = {"schema": "logos_bible_full_auto_chain_v1", "generated_at_utc": _utc(), "steps": steps}
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        failed = [s["step"] for s in steps if not s.get("ok")]
        print(json.dumps({"ok": not failed, "failed": failed, "krv_verses": _krv_verse_count()}))
        return 0 if not failed else 1

    steps.extend(
        [
            _run("graph_slice_scale", [PY, "scripts/build_showroom_meaning_topology_graph_slice_v1.py", "--seed-count", "40", "--max-nodes", "400", "--max-edges", "800"]),
            _run("lemma_edges", [PY, "scripts/build_logos_lemma_verse_edges_v1.py", "--graph-max-edges", "500"]),
            _run("preset_expansion", [PY, "scripts/run_logos_studio_preset_expansion_chain_v1.py"], timeout=900),
            _run("embed_router_merge", [PY, "scripts/merge_logos_studio_embed_router_sidecar_v1.py"]),
            _run("isaiah_youtube_presets", [PY, "scripts/merge_logos_studio_isaiah_youtube_presets_v1.py"]),
            _run("router_stub_patch", [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py"]),
            _run("router_stub_coverage", [PY, "scripts/check_logos_studio_graph_slice_router_coverage_v1.py"]),
            _run("job_reading_pack", [PY, "scripts/build_showroom_logos_job_reading_pack_slice_v1.py"]),
            _run("a4_synthesis_bundle", [PY, "scripts/build_logos_studio_a4_synthesis_bundle_v1.py"]),
            _run("bloom_31k_secondary", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]),
            _run("dynamic_subgraph_router", [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"]),
            _run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]),
            _run("governance_hold_gate", [PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"]),
            _run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ]
    )

    failed = [s["step"] for s in steps if not s.get("ok")]
    krv_n = _krv_verse_count()
    doc = {
        "schema": "logos_bible_full_auto_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(failed) == 0,
        "failed_steps": failed,
        "krv_verse_count": krv_n,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_auto_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "krv_verses": krv_n, "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
