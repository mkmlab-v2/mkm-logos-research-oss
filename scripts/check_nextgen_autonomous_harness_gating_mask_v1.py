#!/usr/bin/env python3
"""[HYPO] NG-40 autonomous harness gating mask — static contract check (dry-run only).

Validates AUTONOMOUS_HARNESS_GATING_MASK_STUB_V1.json alignment with charter, topology,
and SYMBOLIC_ARCHETYPE stub. Does NOT wire sandbox chain or touch Track A / live trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MASK_STUB = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/AUTONOMOUS_HARNESS_GATING_MASK_STUB_V1.json"
)
SYMBOLIC_STUB = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
)
TOPOLOGY = ROOT / "experiments/nextgen_clean_slate_cpu_v1/topology_spec_v1_latest.json"
CHARTER = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
OUT_JSON = ROOT / "reports/ng40_autonomous_harness_gating_mask_check_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate(gate_id: str, passed: bool, *, reason: str | None = None, observed: dict | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "passed": passed,
        "reason": reason,
        "observed": observed or {},
    }


def evaluate(
    *,
    mask: dict[str, Any],
    symbolic: dict[str, Any] | None,
    topology: dict[str, Any] | None,
    charter: dict[str, Any] | None,
) -> dict[str, Any]:
    gates: list[dict[str, Any]] = []

    gates.append(
        _gate(
            "mask_research_only",
            mask.get("research_only") is True and mask.get("track_a_active_write") is False,
            reason="mask must be research_only with track_a_active_write false",
            observed={
                "research_only": mask.get("research_only"),
                "track_a_active_write": mask.get("track_a_active_write"),
            },
        )
    )

    briefings = mask.get("reference_briefings") or []
    brief_ok = (
        len(briefings) >= 2
        and all(b.get("promotion_weight") == 0 for b in briefings)
        and all(b.get("role") == "manual_reference_only" for b in briefings)
    )
    gates.append(
        _gate(
            "reference_briefings_isolated",
            brief_ok,
            reason="each reference_briefing needs role=manual_reference_only and promotion_weight=0",
            observed={"count": len(briefings)},
        )
    )

    layers = mask.get("context_layers") or {}
    layer_ids = {"bench_raw_text", "agent_context_raw", "distilled_spec", "runtime_latest"}
    gates.append(
        _gate(
            "context_layers_complete",
            layer_ids.issubset(set(layers.keys())),
            reason="context_layers must define bench_raw_text, agent_context_raw, distilled_spec, runtime_latest",
            observed={"keys": sorted(layers.keys())},
        )
    )

    bench_role = ((layers.get("bench_raw_text") or {}).get("role"))
    gates.append(
        _gate(
            "bench_raw_not_agent_context",
            bench_role == "compression_eval_corpus_input",
            reason="bench_raw_text role must distinguish eval corpus from agent context",
            observed={"bench_raw_text_role": bench_role},
        )
    )

    commander = mask.get("commander_gates") or {}
    required_before = set(commander.get("commander_signoff_required_before") or [])
    gates.append(
        _gate(
            "commander_gates_present",
            {"apply-active", "track_a_active_write", "live_trading"}.issubset(required_before),
            reason="commander_signoff_required_before must include apply-active, track_a_active_write, live_trading",
            observed={"required_before": sorted(required_before)},
        )
    )

    eval_block = mask.get("eval_before_promote") or {}
    gates.append(
        _gate(
            "eval_before_promote",
            eval_block.get("pytest_gate_required") is True
            and bool(eval_block.get("dual_kpi_harness_script")),
            reason="eval_before_promote requires pytest_gate_required and dual_kpi_harness_script",
            observed={
                "pytest_gate_required": eval_block.get("pytest_gate_required"),
                "dual_kpi_harness_script": eval_block.get("dual_kpi_harness_script"),
            },
        )
    )

    sandbox = mask.get("sandbox_integration") or {}
    wire_status = str(sandbox.get("chain_wire_status") or "")
    commander_approval = sandbox.get("commander_wire_approval") or {}
    wire_ok = wire_status == "not_wired" or (
        wire_status == "wired_v1"
        and bool(commander_approval.get("approved_by"))
        and bool(sandbox.get("step_id"))
    )
    gates.append(
        _gate(
            "sandbox_wire_policy",
            wire_ok,
            reason="wire_status must be not_wired, or wired_v1 with commander_wire_approval and step_id",
            observed={
                "chain_wire_status": wire_status,
                "default_mode": sandbox.get("default_mode"),
                "step_id": sandbox.get("step_id"),
                "commander_approved_by": commander_approval.get("approved_by"),
            },
        )
    )

    if symbolic is not None:
        hg = symbolic.get("harness_gating_mask") or {}
        ptr = str(hg.get("mask_pointer") or "")
        gates.append(
            _gate(
                "symbolic_stub_pointer",
                ptr.endswith("AUTONOMOUS_HARNESS_GATING_MASK_STUB_V1.json"),
                reason="SYMBOLIC_ARCHETYPE stub must point to this mask stub",
                observed={"mask_pointer": ptr},
            )
        )
        promo_forbidden = bool((symbolic.get("last_auto_parallel_ops") or {}).get("promotion_apply_forbidden"))
        gates.append(
            _gate(
                "symbolic_promotion_apply_forbidden",
                promo_forbidden or symbolic.get("track_a_promotion_signoff") is False,
                reason="symbolic stub should keep promotion_apply_forbidden or track_a_promotion_signoff false",
                observed={
                    "promotion_apply_forbidden": promo_forbidden,
                    "track_a_promotion_signoff": symbolic.get("track_a_promotion_signoff"),
                },
            )
        )
    else:
        gates.append(_gate("symbolic_stub_pointer", False, reason="SYMBOLIC_ARCHETYPE stub missing"))

    if topology is not None:
        gates.append(
            _gate(
                "topology_aligned",
                topology.get("research_only") is True
                and topology.get("track_a_active_write") is False,
                reason="topology must match research_only sandbox",
            ),
        )
    else:
        gates.append(_gate("topology_aligned", False, reason="topology_spec missing"))

    if charter is not None:
        gates.append(
            _gate(
                "charter_aligned",
                charter.get("research_only") is True
                and charter.get("track_a_active_write") is False,
                reason="charter must match research_only sandbox",
            ),
        )
    else:
        gates.append(_gate("charter_aligned", False, reason="charter missing"))

    forbidden = mask.get("forbidden") or {}
    gates.append(
        _gate(
            "forbidden_hard_locks",
            forbidden.get("live_trading_auto_trigger") is True
            and forbidden.get("anthropic_metrics_as_track_a_headline") is True,
            reason="forbidden block must hard-lock live trading and anthropic headline paste",
        )
    )

    combined = all(g["passed"] for g in gates)
    return {
        "schema": "ng40_autonomous_harness_gating_mask_check_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "mask_stub_pointer": str(MASK_STUB.relative_to(ROOT)).replace("\\", "/"),
        "gates": gates,
        "combined_all_passed": combined,
        "human_signoff_required_for_promotion": True,
        "track_a_active_write": False,
        "outcome_class": "pass_candidate" if combined else "reject",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check NG-40 autonomous harness gating mask stub")
    ap.add_argument("--mask-json", type=Path, default=MASK_STUB)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    if not args.mask_json.is_file():
        print(f"mask stub missing: {args.mask_json}", file=sys.stderr)
        return 1

    mask = _read_json(args.mask_json)
    symbolic = _read_json(SYMBOLIC_STUB) if SYMBOLIC_STUB.is_file() else None
    topology = _read_json(TOPOLOGY) if TOPOLOGY.is_file() else None
    charter = _read_json(CHARTER) if CHARTER.is_file() else None

    doc = evaluate(mask=mask, symbolic=symbolic, topology=topology, charter=charter)

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc["combined_all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
