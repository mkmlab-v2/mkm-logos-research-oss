#!/usr/bin/env python3
"""[HYPO] Gen AI (DE) + NG-40 local research handoff — no codec auto-merge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
BILLING = ROOT / "reports/gcp_genai_app_builder_billing_probe_latest.json"
BURN = ROOT / "reports/discovery_engine_app_builder_credit_burn_v1_latest.json"
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
HYBRID = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
)
HYBRID_B2B = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_b2b_design_bundle_v1_latest.json"
)
PACKET = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
AZURE_SYNTH = ROOT / "reports/ng40_de_probe_azure_openai_synthesis_v1_latest.json"
NIM_SYNTH = ROOT / "reports/ng40_de_probe_nim_synthesis_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/ng40_genai_de_research_handoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None


def _run(script: str, args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "").strip().splitlines()
    parsed: dict[str, Any] = {}
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:300]}
    return {"script": script, "exit_code": proc.returncode, "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--run-local-refresh",
        action="store_true",
        help="LUT de staging merge + hybrid stack (no DE API)",
    )
    ap.add_argument(
        "--run-de-probe",
        action="store_true",
        help="Live Discovery Engine probe (needs ADC)",
    )
    ap.add_argument(
        "--run-azure-synthesis",
        action="store_true",
        help="Path A: Azure OpenAI on existing DE probe JSON (Startup credits)",
    )
    args = ap.parse_args()
    steps: list[dict[str, Any]] = []

    if args.run_de_probe:
        steps.append(_run("scripts/run_ng40_de_logos_anchor_probe_v1.py", []))
        if steps[-1]["exit_code"] != 0:
            return steps[-1]["exit_code"]

    if args.run_local_refresh:
        lut_args = ["--de-probe-json", str(PROBE)]
        if AZURE_SYNTH.is_file():
            lut_args.extend(["--azure-synthesis-json", str(AZURE_SYNTH)])
        if NIM_SYNTH.is_file():
            lut_args.extend(["--nim-synthesis-json", str(NIM_SYNTH)])
        steps.append(
            _run("scripts/build_archetype_prior_lut_draft_v1.py", lut_args)
        )
        if steps[-1]["exit_code"] != 0:
            return steps[-1]["exit_code"]
        steps.append(_run("scripts/run_nextgen_hybrid_spine_logos_stack_v1.py", []))

    if args.run_azure_synthesis:
        steps.append(
            _run("scripts/run_ng40_de_probe_azure_openai_synthesis_v1.py", [])
        )
        if steps[-1]["exit_code"] != 0:
            return steps[-1]["exit_code"]

    probe = _load(PROBE)
    billing = _load(BILLING)
    burn = _load(BURN)
    lut = _load(LUT)
    hybrid = _load(HYBRID)
    b2b = _load(HYBRID_B2B)
    packet = _load(PACKET)
    azure_synth = _load(AZURE_SYNTH)

    probe_hits = sum((p.get("hit_count") or 0) for p in (probe or {}).get("probes") or [])
    credit_ui = (billing or {}).get("console_credit_ui") or {}
    burn_note = (burn or {}).get("genai_app_builder_credit_consumed") or (
        (billing or {}).get("live_probes_2026_06_03") or {}
    ).get("discovery_engine_credit_burn", {}).get("note")

    out = {
        "schema": "ng40_genai_de_research_handoff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "genai_achievements": {
            "de_rag_operational": probe is not None and (probe.get("probe_count") or 0) > 0,
            "probe_count": probe.get("probe_count") if probe else None,
            "total_hits": probe_hits,
            "engine_id": probe.get("engine_id") if probe else None,
            "lut_commander_status": (lut or {}).get("status"),
            "phase5_signoff_wired": True,
        },
        "genai_not_proven": {
            "credit_percent_consumed": credit_ui.get("remaining_percent_reported_by_commander"),
            "credit_consumed_status": burn_note or "pending_console_recheck",
            "generative_answerquery": "not_in_scope_search_only_valid",
            "azure_openai_synthesis_ok": (azure_synth or {}).get("summary", {}).get(
                "all_azure_ok"
            ),
            "de_did_not_raise_ng40_saving_jaccard": True,
            "export_prep_ready": (packet or {}).get("export_prep_ready"),
            "apply_forbidden": (packet or {}).get("apply_forbidden"),
        },
        "local_ng40_evidence": {
            "hybrid_byte_exact": (hybrid or {}).get("aggregate", {}).get(
                "byte_exact_subset_parity"
            ),
            "hybrid_sidecar_jaccard": (hybrid or {}).get("aggregate", {}).get(
                "avg_logos_sidecar_jaccard"
            ),
            "b2b_design_contract_met": (b2b or {}).get("guarded_b2b", {}).get("contract_met"),
            "frozen_track_a_note": "47.5% saving / J~0.890 — independent of Gen AI",
        },
        "wired_chain": [
            "scripts/run_ng40_de_logos_anchor_probe_v1.py",
            "scripts/run_ng40_de_probe_azure_openai_synthesis_v1.py (Path A · Azure Startup)",
            "scripts/build_archetype_prior_lut_draft_v1.py --de-probe-json (staging only)",
            "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
            "scripts/run_vertex_gemini_vertex_ai_search_grounding_smoke_v1.py (GCP generative alt)",
            "reports/gcp_genai_app_builder_billing_probe_latest.json",
        ],
        "forbidden": [
            "auto_merge_de_hits_into_ng40_codec",
            "track_a_active_write_from_genai_or_de_alone",
        ],
        "next_roi_steps": [
            "Path A (recommended): --run-azure-synthesis on handoff or standalone synthesis script",
            "Console Credits/Reports: Discovery Engine SKU vs Azure OpenAI burn",
            "Path B (later): Azure AI Search index migration from GCS corpus",
            "NG: dual-axis beat or export_prep_ready — local spine/LUT only",
        ],
        "pointers": {
            "de_probe": str(PROBE.relative_to(ROOT)).replace("\\", "/"),
            "billing_probe": str(BILLING.relative_to(ROOT)).replace("\\", "/"),
            "lut_draft": str(LUT.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_b2b_bundle": str(HYBRID_B2B.relative_to(ROOT)).replace("\\", "/"),
            "promotion_packet": str(PACKET.relative_to(ROOT)).replace("\\", "/"),
            "azure_synthesis": str(AZURE_SYNTH.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "probe_hits": probe_hits,
                "lut_status": (lut or {}).get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
