#!/usr/bin/env python3
"""Post-T0 cheonyucho fill — reproducible rerun bench checklist ([HYPO] planning)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_post_t0_rerun_bench_checklist_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict:
    return {
        "schema": "cheonyucho_post_t0_rerun_bench_checklist_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "trigger": "hanja_canon_status=acquired AND physical_verified=true (human gate)",
        "precondition_artifacts": [
            "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_v1.json",
            "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json",
        ],
        "steps": [
            {
                "order": 1,
                "id": "bind_physical",
                "action": "bind scan/paste + --set-physical-verified (commander)",
                "command": "py scripts/bind_cheonyucho_physical_anchor_v1.py --scan <path> --call-no 199.1-이617ㄱ --set-physical-verified",
                "gate": "probe.physical_verified=true",
            },
            {
                "order": 2,
                "id": "physical_chain",
                "action": "physical anchor chain",
                "command": "py scripts/run_cheonyucho_physical_anchor_chain_v1.py",
                "artifacts": [
                    "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_chain_v1_latest.json",
                    "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json",
                ],
            },
            {
                "order": 3,
                "id": "fragment_mine",
                "action": "re-mine ledger (expect primary_hanja_chunk if policy enabled)",
                "command": "py scripts/run_cheonyucho_fragment_mine_v1.py",
                "metrics": ["summary.primary_hanja_chunk_count", "summary.cheonyucho_chunks"],
                "artifact": "docs/research/raw/CHEONYUCHO_FRAGMENT_LEDGER_v1.json",
            },
            {
                "order": 4,
                "id": "acquisition_gate",
                "action": "gate re-eval (promotion_allowed may flip after human canon review)",
                "command": "py scripts/check_cheonyucho_acquisition_gate_v1.py",
                "artifact": "reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json",
            },
            {
                "order": 5,
                "id": "secondary_proxy_merge",
                "action": "merge T0 fragments into secondary proxy + ledger",
                "command": "py scripts/merge_ijeoma_secondary_proxy_to_fragment_ledger_v1.py",
                "note": "run after build_ijeoma_secondary_proxy if new SP rows added",
            },
            {
                "order": 6,
                "id": "dr_matrix",
                "action": "refresh DR vs T0 question matrix",
                "command": "py scripts/build_cheonyucho_dr_vs_t0_question_matrix_v1.py",
                "artifact": "reports/constitution/btrack_pilot/cheonyucho_dr_vs_t0_question_matrix_v1_latest.json",
            },
            {
                "order": 7,
                "id": "nl_packs",
                "action": "rebuild NotebookLM IJEOMA_BTRACK pack (T0 upload separate)",
                "command": "py scripts/build_notebooklm_lens_source_packs_v1.py",
                "human": "Upload new primary nl_proxy/scan digest to IJEOMA_BTRACK notebook",
            },
            {
                "order": 8,
                "id": "ijeoma_query_set",
                "action": "re-run ijeoma QUERY_SET cheonyucho rows",
                "command": "py scripts/run_ijeoma_query_set_batch_v1.py",
                "artifact": "reports/constitution/btrack_pilot/ijeoma_query_set_run_v1.jsonl",
                "note": "confirm script path exists before run",
            },
            {
                "order": 9,
                "id": "pytest_smoke",
                "action": "cheonyucho + secondary proxy regression",
                "command": "py -m pytest tests/test_bind_cheonyucho_physical_anchor_v1.py tests/test_ijeoma_secondary_proxy_v1.py tests/test_merge_ijeoma_secondary_proxy_v1.py tests/test_build_cheonyucho_dr_vs_t0_question_matrix_v1.py -q",
            },
        ],
        "expected_deltas": {
            "primary_hanja_chunk_count": "0 → >0 (requires fragment_mine policy + T0 ingest)",
            "canon_status": "not_acquired → acquired (human gate only)",
            "nl_cite_tier": "UNVERIFIED/HYPO → CANON-eligible for anchored passages",
            "does_not_auto_change": [
                "track_a_trading",
                "compression_repair_v2_headline",
                "prophecy_vote_merge",
                "sasang_clinical_dssbw_primary",
                "patient_care_bundle_gating",
            ],
        },
        "reproduce": "py scripts/build_cheonyucho_post_t0_rerun_bench_checklist_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "steps": len(doc["steps"]), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
