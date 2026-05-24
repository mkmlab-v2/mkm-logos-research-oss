#!/usr/bin/env python3
"""B-track Round 17: wire gloss lexicon alignment remediation chain."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/btrack_wire_gloss_remediation_round17_v1_latest.json"
ALIGNED_POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_lexicon_aligned_v1_latest.json"
SIGNOFF = ROOT / "reports/btrack_wire_gloss_lane_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    tail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, tail[-2500:]


def _audit_with_poc_env(poc_path: Path) -> dict[str, Any]:
    """Audit using aligned POC as wire source (temp env override via inline import)."""
    import scripts.mkm_graph_wire_bridge_influence_v1 as wire

    orig_poc = wire.POC
    try:
        wire.POC = poc_path
        from scripts.audit_wire_atom_gloss_index_alignment_v1 import _collect_wire_atom_ids, _load_atom_index

        lex = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
        lex_ids = _load_atom_index(lex)
        wire_ids = _collect_wire_atom_ids()
        known = [aid for aid in wire_ids if aid in lex_ids]
        unknown = [aid for aid in wire_ids if aid not in lex_ids]
        return {
            "wire_atom_id_count": len(wire_ids),
            "known_in_lexicon_count": len(known),
            "unknown_count": len(unknown),
            "match_ratio": round(len(known) / max(1, len(wire_ids)), 4),
            "hard_unknown_sample": unknown[:16],
            "proceed_gloss_decompress": len(unknown) == 0 and len(known) >= 3,
        }
    finally:
        wire.POC = orig_poc


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track wire gloss remediation round 17")
    ap.add_argument("--skip-rebuild", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec0, tail0 = _run([sys.executable, "scripts/audit_wire_atom_gloss_index_alignment_v1.py"])
    before = json.loads((ROOT / "reports/wire_atom_gloss_index_alignment_v1_latest.json").read_text(encoding="utf-8"))
    steps.append({"step": "audit_before", "exit_code": ec0, "match_ratio": before.get("match_ratio")})

    if not args.skip_rebuild:
        ec1, tail1 = _run(
            [
                sys.executable,
                "scripts/rebuild_logos_wire_poc_lexicon_aligned_v1.py",
                "--strategy",
                "anchor07_primary",
            ]
        )
        steps.append({"step": "rebuild_lexicon_aligned_poc", "exit_code": ec1, "tail": tail1})

    after_inline = _audit_with_poc_env(ALIGNED_POC) if ALIGNED_POC.is_file() else {}

    from scripts.core.master_codebook_lexicon_v1_bridge import gloss_rows_for_atom_ids

    lex = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
    aligned_ids = []
    if ALIGNED_POC.is_file():
        aligned_ids = list(
            json.loads(ALIGNED_POC.read_text(encoding="utf-8"))
            .get("graph_rag", {})
            .get("reasoning_path_node_ids")
            or []
        )
    gloss_rows, gloss_meta = gloss_rows_for_atom_ids(aligned_ids, lex)

    doc: dict[str, Any] = {
        "schema": "btrack_wire_gloss_remediation_round17_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "would_change_active": False,
        "commander_new_btrack_lane": True,
        "lane_id": "wire_gloss_lexicon_aligned_v1",
        "audit_before": {
            "match_ratio": before.get("match_ratio"),
            "hard_unknown": before.get("hard_unknown_sample"),
            "proceed_gloss_decompress": before.get("proceed_gloss_decompress"),
        },
        "audit_after_aligned_poc": after_inline,
        "aligned_poc_path": str(ALIGNED_POC.relative_to(ROOT)).replace("\\", "/") if ALIGNED_POC.is_file() else None,
        "gloss_meta": gloss_meta,
        "gloss_sample": gloss_rows[:8],
        "remediation_ok": bool(after_inline.get("proceed_gloss_decompress")),
        "jaccard_impact_expected": "0pp — wire is non-gating semantic channel; cap 0.15 logos KPI unchanged",
        "steps": steps,
        "next": "Use logos_graph_wire_rag_poc_lexicon_aligned_v1 for gloss/decompress B-track hooks; keep cap sunday closure frozen.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "btrack_wire_gloss_lane_signoff_v1",
        "signoff_utc": _utc(),
        "commander_approved_new_btrack": True,
        "lane_id": "wire_gloss_lexicon_aligned_v1",
        "remediation_ok": doc["remediation_ok"],
        "explicit_hold": {
            "active_report_kpi_update": False,
            "ms_paste_hwpx_kpi_body": False,
            "n400_cap_sweep_reopen": False,
        },
        "artifacts": {
            "round17": str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "aligned_poc": doc.get("aligned_poc_path"),
        },
    }
    SIGNOFF.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": doc["remediation_ok"],
                "out": str(OUT),
                "match_before": before.get("match_ratio"),
                "match_after": after_inline.get("match_ratio"),
                "known_gloss_count": gloss_meta.get("known_gloss_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["remediation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
