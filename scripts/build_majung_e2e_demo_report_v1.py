#!/usr/bin/env python3
"""Assemble Majung / K-Startup E2E demo evidence bundle (Fact-Lock, artifact-bound)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

OUT_JSON = ROOT / "docs/final/artifacts/majung_e2e_demo_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/majung_e2e_demo_latest.md"

FROZEN_BENCH = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
KPI_SUMMARY = ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"
FINANCE_INPUT = ROOT / "docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json"
FINANCE_REPORT = ROOT / "docs/final/artifacts/finance_macro_b2b_compression_active_report_v1.json"
MACRO_SMOKE = ROOT / "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json"
OPENAPI = ROOT / "docs/final/openapi_macro_risk_warning_api_v1.yaml"
EXEC_SUMMARY = ROOT / "docs/final/artifacts/compression_enterprise_executive_summary_v1.md"
FORWARD_HEALTH = ROOT / "docs/final/artifacts/macro_risk_forward_pipeline_health_gate_latest.json"
DASHBOARD = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _frozen_bench_block() -> dict[str, Any]:
    active = _read_json(FROZEN_BENCH)
    kpi = _read_json(KPI_SUMMARY)
    block: dict[str, Any] = {
        "label": "Track A frozen bench (generic enterprise eval set)",
        "artifact_paths": [_rel(FROZEN_BENCH), _rel(KPI_SUMMARY) if KPI_SUMMARY.is_file() else None],
        "disclaimer": "Internal bench only; not production SLA or customer-wide generalization.",
        "forbidden_claims": ["unconditional_47_percent", "ms_token_causality", "hallucination_eradication"],
    }
    block["artifact_paths"] = [p for p in block["artifact_paths"] if p]
    if active:
        m = active.get("compression_metrics") or {}
        block["case_count"] = m.get("case_count")
        block["global_token_saving_rate"] = m.get("global_token_saving_rate")
        block["avg_reconstruction_fidelity_jaccard"] = m.get("avg_reconstruction_fidelity_jaccard")
        block["min_reconstruction_fidelity_jaccard"] = m.get("min_reconstruction_fidelity_jaccard")
        block["sensitive_violation_count"] = m.get("sensitive_violation_count")
    if kpi:
        active_kpi = kpi.get("active_kpi") or {}
        block["active_kpi"] = {
            "global_token_saving_rate": active_kpi.get("global_token_saving_rate"),
            "bench_saving_floor_ok": active_kpi.get("bench_saving_floor_ok"),
            "ultra_saving_policy_ok": active_kpi.get("ultra_saving_policy_ok"),
            "policy_floor": active_kpi.get("policy_floor") or active_kpi.get("saving_floor"),
        }
    return block


def _finance_workload_block() -> dict[str, Any]:
    block: dict[str, Any] = {
        "label": "Finance/macro B2B target workload (Track C corpus)",
        "artifact_paths": [_rel(FINANCE_INPUT), _rel(FINANCE_REPORT)],
        "disclaimer": "Domain-specific experimental eval; separate from frozen 40-case Track A bench.",
    }
    inp = _read_json(FINANCE_INPUT)
    rep = _read_json(FINANCE_REPORT)
    if inp:
        cases = inp.get("compression_cases") or inp.get("cases") or []
        block["eval_input_case_count"] = len(cases)
        if cases and isinstance(cases[0], dict):
            sample = cases[0]
            block["sample_case"] = {
                "id": sample.get("id"),
                "source_path": sample.get("source_path"),
                "raw_text_preview": (sample.get("raw_text") or "")[:280],
            }
    if rep:
        m = rep.get("compression_metrics") or {}
        block["experimental_metrics"] = {
            "case_count": m.get("case_count"),
            "global_token_saving_rate": m.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
            "min_reconstruction_fidelity_jaccard": m.get("min_reconstruction_fidelity_jaccard"),
        }
        cases = m.get("cases") or []
        if cases and isinstance(cases[0], dict):
            c0 = cases[0]
            block["sample_case_metrics"] = {
                "id": c0.get("id"),
                "raw_tokens": c0.get("raw_tokens"),
                "compressed_tokens": c0.get("compressed_tokens"),
                "token_saving_rate": c0.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": c0.get("reconstruction_fidelity_jaccard"),
            }
    return block


def _macro_api_block() -> dict[str, Any]:
    smoke = _read_json(MACRO_SMOKE)
    block: dict[str, Any] = {
        "label": "Macro risk observation API (read-only stub contract)",
        "openapi_path": _rel(OPENAPI),
        "smoke_artifact": _rel(MACRO_SMOKE),
        "disclaimer": "Not investment advice; no trade execution; observation labels only.",
    }
    if smoke:
        block["decision_state"] = smoke.get("decision_state")
        block["risk_warning_level"] = smoke.get("risk_warning_level")
        block["recommended_operator_posture"] = smoke.get("recommended_operator_posture")
        disc = smoke.get("disclaimer") or {}
        block["not_investment_advice"] = disc.get("not_investment_advice")
        ev = smoke.get("evidence_ref") or {}
        block["evidence_artifact_path"] = ev.get("artifact_path")
        block["timestamp_utc"] = smoke.get("timestamp_utc")
    else:
        block["status"] = "missing_smoke_artifact"
    return block


def _governance_block(chain_steps: list[dict[str, Any]]) -> dict[str, Any]:
    forward = _read_json(FORWARD_HEALTH)
    dash = _read_json(DASHBOARD)
    return {
        "label": "Governance / gates (audit trail posture)",
        "chain_steps": chain_steps,
        "forward_pipeline_health": _rel(FORWARD_HEALTH) if forward else None,
        "forward_health_pass": forward.get("pass") if forward else None,
        "trackc_dashboard": _rel(DASHBOARD) if dash else None,
        "disclaimer": "Gate pass = path/existence/contract smoke; not prediction quality or selection odds.",
    }


def _render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# Majung E2E demo bundle (Fact-Safe)",
        "",
        f"- **generated_at_utc:** {doc.get('generated_at_utc')}",
        f"- **schema:** {doc.get('schema')}",
        f"- **chain_ok:** {doc.get('chain_ok')}",
        "",
        "## One-line (demo script)",
        "",
        doc.get("demo_narrative_one_liner", ""),
        "",
        "## Frozen bench (Track A)",
        "",
    ]
    fb = doc.get("frozen_bench") or {}
    lines.append(f"- Cases: {fb.get('case_count')} · saving: {fb.get('global_token_saving_rate')}")
    ak = fb.get("active_kpi") or {}
    if ak:
        lines.append(
            f"- Policy floor: {ak.get('policy_floor')} · floor_ok: {ak.get('bench_saving_floor_ok')}"
        )
    lines.append(f"- *{fb.get('disclaimer')}*")
    lines.append("")
    lines.append("## Finance/macro workload sample")
    lines.append("")
    fw = doc.get("finance_workload") or {}
    em = fw.get("experimental_metrics") or {}
    lines.append(f"- Eval cases: {fw.get('eval_input_case_count')} · domain saving: {em.get('global_token_saving_rate')}")
    scm = fw.get("sample_case_metrics") or {}
    if scm:
        lines.append(
            f"- Sample `{scm.get('id')}`: {scm.get('raw_tokens')}→{scm.get('compressed_tokens')} tokens "
            f"({scm.get('token_saving_rate')}); Jaccard {scm.get('reconstruction_fidelity_jaccard')}"
        )
    lines.append(f"- *{fw.get('disclaimer')}*")
    lines.append("")
    lines.append("## Macro API")
    lines.append("")
    ma = doc.get("macro_api") or {}
    lines.append(
        f"- `decision_state={ma.get('decision_state')}` · `risk_warning_level={ma.get('risk_warning_level')}`"
    )
    lines.append(f"- *{ma.get('disclaimer')}*")
    lines.append("")
    lines.append("## Chain steps")
    lines.append("")
    for step in doc.get("chain_steps") or []:
        ok = "PASS" if step.get("exit_code") == 0 else "FAIL"
        lines.append(f"- [{ok}] {step.get('name')} (exit {step.get('exit_code')})")
    lines.append("")
    lines.append("## Submission boundaries")
    lines.append("")
    for line in doc.get("submission_boundaries") or []:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Majung E2E demo JSON/MD from artifacts.")
    ap.add_argument("--chain-log", type=Path, help="JSON file with list of chain step results")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    chain_steps: list[dict[str, Any]] = []
    if args.chain_log and args.chain_log.is_file():
        raw = json.loads(args.chain_log.read_text(encoding="utf-8-sig"))
        chain_steps = raw if isinstance(raw, list) else raw.get("steps") or []

    chain_ok = all(s.get("exit_code") == 0 for s in chain_steps) if chain_steps else None

    doc: dict[str, Any] = {
        "schema": "majung_e2e_demo_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "program_ref": "k_startup_majung_microsoft_pbancSn_177575",
        "hypothesis_tier": "N/A",
        "ready_for_external_send": False,
        "chain_ok": chain_ok,
        "chain_steps": chain_steps,
        "demo_narrative_one_liner": (
            "Finance/macro text workload → governed compression metrics → read-only macro WATCH API "
            "→ audit/gate artifacts (bench & PoC disclaimers apply)."
        ),
        "frozen_bench": _frozen_bench_block(),
        "finance_workload": _finance_workload_block(),
        "macro_api": _macro_api_block(),
        "governance": _governance_block(chain_steps),
        "evidence_pointers": [
            _rel(EXEC_SUMMARY),
            _rel(OPENAPI),
            "docs/final/artifacts/k_startup_majung_submission_playbook_v1.md",
        ],
        "submission_boundaries": [
            "No selection guarantee; no trading alpha; no Prophecy Sandbox branding.",
            "47% only with 40-case floor 0.47 qualifier; finance_macro % is separate experimental corpus.",
            "B-track / live trading not auto-wired to this demo.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_render_md(doc), encoding="utf-8")
    print(f"majung_e2e_demo: wrote {args.out_json}")
    print(f"majung_e2e_demo: wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
