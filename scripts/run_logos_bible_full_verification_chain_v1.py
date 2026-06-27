#!/usr/bin/env python3
"""Logos bible_full — ordered verification + completion chain (W5 SSOT).

Runs gap fill → lemma → presets → router → ui-lite → audit → gates → sync → smokes.

  py scripts/run_logos_bible_full_verification_chain_v1.py
  py scripts/run_logos_bible_full_verification_chain_v1.py --skip-live-smoke
  py scripts/run_logos_bible_full_verification_chain_v1.py --run-playwright-smoke
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
OUT = ROOT / "reports/logos_bible_full_verification_chain_v1_latest.json"
AUDIT = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
LIVE_BASE = "https://logos.jema-ai.com"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(name: str, cmd: list[str], *, timeout: int = 14400) -> dict[str, Any]:
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


def _audit_layers() -> dict[str, float]:
    if not AUDIT.is_file():
        return {}
    audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
    return {str(ly["id"]): float(ly.get("canon_coverage_pct") or 0) for ly in audit.get("layers") or [] if ly.get("id")}


def _gate_from_audit(layers: dict[str, float]) -> dict[str, bool]:
    return {
        "citation_100": layers.get("studio_citation_shard_krv", 0) >= 99.9,
        "meaning_100": layers.get("bible_meaning_graph_nodes", 0) >= 99.9,
        "slice_100": layers.get("studio_graph_slice", 0) >= 99.9,
        "lemma_95": layers.get("lemma_verse_edges", 0) >= 95.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-live-smoke", action="store_true")
    ap.add_argument("--run-playwright-smoke", action="store_true")
    ap.add_argument("--live-base", default=LIVE_BASE)
    ap.add_argument("--skip-sync", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    # 1–2: idempotent gap fill
    steps.append(_run("meaning_gap_fill", [PY, "scripts/expand_logos_bible_full_corpus_batch_v1.py", "--fill-meaning-gaps-only"]))
    steps.append(_run("slice_gap_fill", [PY, "scripts/expand_logos_bible_full_corpus_batch_v1.py", "--fill-slice-gaps-only"]))

    # 3: lemma + book presets + router
    steps.append(
        _run(
            "lemma_edges_stub",
            [PY, "scripts/build_logos_lemma_verse_edges_v1.py", "--graph-max-edges", "62000", "--meaning-node-stub-edges"],
        )
    )
    steps.append(_run("book_anchor_presets", [PY, "scripts/merge_logos_studio_book_anchor_presets_v1.py"]))
    steps.append(
        _run(
            "router_stub_patch",
            [PY, "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py", "--all-presets"],
        )
    )
    steps.append(_run("router_coverage_gate", [PY, "scripts/check_logos_studio_graph_slice_router_coverage_v1.py"]))

    # 4: ui-lite + bloom + dynamic router
    steps.append(_run("ui_lite_graph", [PY, "scripts/build_logos_studio_graph_slice_ui_lite_v1.py"]))
    steps.append(_run("bloom_31k", [PY, "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"]))
    steps.append(_run("dynamic_router", [PY, "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"]))
    steps.append(_run("conflict_sidecar", [PY, "scripts/build_bigset_studio_conflict_sidecar_v1.py"]))
    steps.append(_run("oss_premarket_smoke", [PY, "scripts/run_logos_oss_premarket_smoke_v1.py"], timeout=180))

    # 5: audit + governance
    steps.append(_run("coverage_audit", [PY, "scripts/build_logos_bible_full_coverage_audit_v1.py"]))
    layers = _audit_layers()
    gates = _gate_from_audit(layers)
    steps.append(_run("governance_hold_gate", [PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"]))
    steps.append(_run("w6_prep_gate", [PY, "scripts/check_logos_bible_full_w6_prep_gate_v1.py"]))

    # 6: sync + design gate
    if not args.skip_sync:
        steps.append(_run("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]))

    design_cmd = [PY, "scripts/check_logos_studio_design_gate_v1.py"]
    if args.run_playwright_smoke:
        design_cmd.extend(["--run-playwright-smoke", "--smoke-base", args.live_base.rstrip("/")])
    steps.append(_run("design_gate", design_cmd, timeout=600))

    # 7: pytest spot checks
    steps.append(
        _run(
            "pytest_coverage_audit",
            [
                PY,
                "-m",
                "pytest",
                "tests/test_build_logos_bible_full_coverage_audit_v1.py",
                "tests/test_logos_verse_ref_canonical_v1.py",
                "tests/test_logos_studio_dynamic_synthesis_v1.py",
                "-q",
            ],
            timeout=120,
        )
    )

    # 8: live API smokes
    if not args.skip_live_smoke:
        steps.append(
            _run(
                "live_jhn_query",
                [
                    PY,
                    "scripts/smoke_logos_studio_66book_matrix_v1.py",
                    "--base",
                    args.live_base.rstrip("/"),
                    "--books",
                    "Jhn",
                ],
                timeout=90,
            )
        )
        steps.append(
            _run(
                "live_66book_matrix",
                [PY, "scripts/smoke_logos_studio_66book_matrix_v1.py", "--base", args.live_base.rstrip("/")],
                timeout=3600,
            )
        )

    failed = [s["step"] for s in steps if not s.get("ok")]
    gates_ok = all(gates.values())
    ok = not failed and gates_ok

    doc = {
        "schema": "logos_bible_full_verification_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "failed_steps": failed,
        "audit_layers_pct": layers,
        "gates": gates,
        "steps": steps,
        "reproduce": "py scripts/run_logos_bible_full_verification_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "gates": gates, "failed": failed, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
