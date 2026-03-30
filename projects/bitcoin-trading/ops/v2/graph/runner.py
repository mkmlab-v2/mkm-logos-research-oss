from __future__ import annotations

import json
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ops.v2.core.global_state import default_state
from ops.v2.core.ide_capability import save_capability
from ops.v2.connectors.cost_governor import evaluate_cost_governor
from ops.v2.connectors.policy_drift_bot import evaluate_policy_drift_bot
from ops.v2.connectors.risk_mode_guardrail import evaluate_risk_mode_guardrail
from ops.v2.connectors.strategy_ingest import ingest_strategy
from ops.v2.connectors.vault_sync import save_manifest
from ops.v2.graph.nodes.athena import athena_node
from ops.v2.graph.nodes.brain_sync import brain_sync_node
from ops.v2.graph.nodes.sentinel import sentinel_node
from ops.v2.graph.nodes.watchdog import watchdog_node
from ops.v2.memory.decision_ledger import append_decision_ledger
from ops.v2.memory.external_memory_adapter import ExternalMemoryAdapter
from ops.v2.reports.incident_archivist import archive_incident_if_needed

OUT_DIR = PROJECT_ROOT / "memory" / "v2"
STOP_FILE = PROJECT_ROOT / "memory" / "STOP.txt"
POLICY_PATH = PROJECT_ROOT / "ops" / "v2" / "policies" / "risk_policy.yaml"
STATE_LATEST_PATH = OUT_DIR / "latest_state.json"
STATE_JOURNAL_PATH_TEMPLATE = "state_{ymd}.jsonl"


def _load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _apply_sentinel_kill_switch(result: dict[str, Any]) -> None:
    loaded = _load_policy()
    policy = loaded.get("risk_policy", {}) if isinstance(loaded, dict) else {}
    auto_kill_on_block = bool(policy.get("auto_kill_switch_on_sentinel_block", False))
    if not auto_kill_on_block:
        return
    if result.get("execution_mode") != "execute":
        return
    if result.get("sentinel_approval") is not False:
        return
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(
        "AUTO STOP: sentinel blocked execute mode. Remove manually after review.",
        encoding="utf-8",
    )
    result["kill_switch_triggered"] = True
    result["kill_switch_path"] = str(STOP_FILE)


def _apply_cost_guardrail(result: dict[str, Any]) -> None:
    cg = result.get("cost_governor") or {}
    if result.get("execution_mode") != "execute":
        return
    if not cg.get("budget_ok", True) and bool(cg.get("block_execute_on_breach", True)):
        result["sentinel_approval"] = False
        result["sentinel_message"] = "blocked: cost governor budget breach"
        result.setdefault("incidents", []).append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "cost_governor",
                "severity": "warning",
                "message": "execute blocked by budget breach",
                "details": {"breaches": cg.get("breaches", [])},
            }
        )


def _apply_risk_mode_guardrail(result: dict[str, Any]) -> None:
    rg = result.get("risk_mode_guardrail") or {}
    mode = result.get("execution_mode")
    proposed = rg.get("proposed_mode", "read-only")
    attach_incident = bool(((rg.get("mode_guardrail") or {}).get("attach_incident_on_override", True)))

    if mode != "execute" and proposed == "shadow":
        result["effective_execution_mode"] = "shadow"
        result["mode_override_reason"] = f"risk_score={rg.get('risk_score')}>=force_shadow_threshold"
        if attach_incident:
            result.setdefault("incidents", []).append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "risk_mode_guardrail",
                    "severity": "info",
                    "message": "mode override to shadow",
                    "details": {
                        "risk_score": rg.get("risk_score"),
                        "triggers": rg.get("triggers", []),
                    },
                }
            )

    if mode == "execute" and bool(rg.get("block_execute", False)):
        result["sentinel_approval"] = False
        result["sentinel_message"] = "blocked: risk score guardrail"
        if attach_incident:
            result.setdefault("incidents", []).append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "risk_mode_guardrail",
                    "severity": "warning",
                    "message": "execute blocked by risk score",
                    "details": {
                        "risk_score": rg.get("risk_score"),
                        "triggers": rg.get("triggers", []),
                    },
                }
            )


def run_fallback_chain(state: dict[str, Any]) -> dict[str, Any]:
    state = watchdog_node(state)
    state = brain_sync_node(state)
    state = athena_node(state)
    state = sentinel_node(state)
    return state


def run_graph(execution_mode: str = "read-only", execute_approved: bool = False) -> dict[str, Any]:
    state = default_state(execution_mode=execution_mode)
    state["execute_approval_valid"] = bool(execute_approved)
    state["strategy"] = ingest_strategy(PROJECT_ROOT)
    cap_path = OUT_DIR / "ide_capability.json"
    state["ide_capability"] = save_capability(cap_path)

    try:
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(dict)
        graph.add_node("watchdog", watchdog_node)
        graph.add_node("brain_sync", brain_sync_node)
        graph.add_node("athena", athena_node)
        graph.add_node("sentinel", sentinel_node)

        graph.add_edge(START, "watchdog")
        graph.add_edge("watchdog", "brain_sync")
        graph.add_edge("brain_sync", "athena")
        graph.add_edge("athena", "sentinel")
        graph.add_edge("sentinel", END)

        app = graph.compile()
        result = app.invoke(state)
    except Exception:
        result = run_fallback_chain(state)

    result["policy_drift"] = evaluate_policy_drift_bot(PROJECT_ROOT, result)
    result["cost_governor"] = evaluate_cost_governor(PROJECT_ROOT)
    result["incident_status"] = "healthy" if result.get("sentinel_approval") else "alert"
    result["risk_mode_guardrail"] = evaluate_risk_mode_guardrail(PROJECT_ROOT, result)
    _apply_risk_mode_guardrail(result)
    _apply_cost_guardrail(result)
    manifest_path = save_manifest(PROJECT_ROOT)
    result["vault_sync_manifest_path"] = str(manifest_path)
    ledger_path = append_decision_ledger(PROJECT_ROOT, result)
    result["decision_ledger_path"] = str(ledger_path)
    incident_md = archive_incident_if_needed(PROJECT_ROOT, result)
    result["incident_report_path"] = str(incident_md) if incident_md else None
    _apply_sentinel_kill_switch(result)

    now = datetime.now(timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    journal = OUT_DIR / STATE_JOURNAL_PATH_TEMPLATE.format(ymd=now.strftime("%Y%m%d"))

    STATE_LATEST_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    with journal.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # Best-effort external memory sync; never block core file-based SSOT flow.
    memory_adapter = ExternalMemoryAdapter(PROJECT_ROOT)
    incidents = result.get("incidents") or []
    if not isinstance(incidents, list):
        incidents = []
    critical_incident_count = sum(
        1
        for item in incidents
        if isinstance(item, dict)
        and str(item.get("severity", "")).lower() in {"warning", "error", "critical"}
    )
    memory_store_ok = memory_adapter.store_event(
        {
            "schema_version": "v1",
            "event_type": "v2_cycle_result",
            "run_id": result.get("run_id"),
            "ts_utc": result.get("timestamp") or now.isoformat(),
            "execution_mode": result.get("execution_mode"),
            "sentinel_approval": result.get("sentinel_approval"),
            "sentinel_message": result.get("sentinel_message"),
            "risk_score": (result.get("risk_mode_guardrail") or {}).get("risk_score"),
            "proposed_mode": (result.get("risk_mode_guardrail") or {}).get("proposed_mode"),
            "policy_drift_count": (result.get("policy_drift") or {}).get("drift_count"),
            "incident_count": len(incidents),
            "critical_incident_count": critical_incident_count,
            "budget_ok": (result.get("cost_governor") or {}).get("budget_ok"),
            "estimated_cost_usd": (result.get("cost_governor") or {}).get("estimated_cost_usd"),
            "strategy_hash": (result.get("strategy") or {}).get("strategy_hash"),
        }
    )
    result["external_memory"] = {
        "enabled": memory_adapter.enabled,
        "backend": memory_adapter.backend,
        "last_store_ok": memory_store_ok,
        "health": memory_adapter.health(),
    }
    STATE_LATEST_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MKM Auto-Ops v2 graph cycle")
    parser.add_argument(
        "--mode",
        choices=["read-only", "shadow", "execute"],
        default="read-only",
        help="Execution mode",
    )
    parser.add_argument(
        "--execute-approved",
        action="store_true",
        help="Mark execute run as explicitly approved",
    )
    args = parser.parse_args()
    output = run_graph(execution_mode=args.mode, execute_approved=args.execute_approved)
    print(json.dumps(output, indent=2, ensure_ascii=False))
