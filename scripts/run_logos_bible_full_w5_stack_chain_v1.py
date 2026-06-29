#!/usr/bin/env python3
"""W5 bible_full stack — 100% slice/meaning verification, governance HOLD.

  py scripts/run_logos_bible_full_w5_stack_chain_v1.py
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
OUT = ROOT / "reports/logos_bible_full_w5_stack_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 14400) -> dict[str, Any]:
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", timeout=timeout
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
    ap.add_argument("--skip-corpus-batch", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_corpus_batch:
        steps.append(
            _run(
                "corpus_batch_expand_100",
                [PY, "scripts/expand_logos_bible_full_corpus_batch_v1.py", "--target-canon-pct", "100"],
                timeout=14400,
            )
        )
    steps.extend(
        [
            _run(
                "lemma_edges_w5",
                [
                    PY,
                    "scripts/build_logos_lemma_verse_edges_v1.py",
                    "--graph-max-edges",
                    "62000",
                    "--meaning-node-stub-edges",
                ],
            ),
            _run("book_anchor_presets", [PY, "scripts/merge_logos_studio_book_anchor_presets_v1.py"]),
            _run(
                "router_stub_patch_all",
                [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py", "--all-presets"],
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
    citation_pct = float(summary.get("studio_citation_shard_krv_pct") or 0)

    gates = {
        "citation_100": citation_pct >= 99.9,
        "slice_ge_99": slice_pct >= 99.0,
        "meaning_ge_99": meaning_pct >= 99.0,
        "lemma_ge_95": lemma_pct >= 95.0,
        "no_failed_steps": not failed,
    }
    ok = all(gates.values())

    doc = {
        "schema": "logos_bible_full_w5_stack_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "gates": gates,
        "failed_steps": failed,
        "audit_summary": summary,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_w5_stack_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "gates": gates, "audit_summary": summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
