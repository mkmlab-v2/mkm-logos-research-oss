#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REP = ROOT / "reports"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    gate = _read_json(ART / "companion_ecosystem_go_readiness_gate_latest.json")
    n8n = _read_json(ART / "n8n_latency_probe_latest.json")
    runtime = _read_json(REP / "myeongni_conflict_arbitration_runtime_mode_latest.json")
    orch = _read_json(ART / "mkm_global_orchestrator_latest.json")

    cond1 = bool(((gate.get("metrics") or {}).get("drift_pass")))
    cond2 = bool(((n8n.get("gate") or {}).get("pass_p99_le_500")))
    cond3 = bool(runtime.get("verification_pass") and str(runtime.get("mode", "")).lower() == "aggressive")
    overall = bool(cond1 and cond2 and cond3)

    packet = {
        "schema": "companion_ecosystem_go_approval_packet_v1",
        "generated_at_utc": _utc_now(),
        "conditions": {
            "memory_drift_lt_0_05_3loops": cond1,
            "external_latency_p99_le_500ms": cond2,
            "manual_signoff_aggressive_verified": cond3,
        },
        "evidence": {
            "drift_gate": "docs/final/artifacts/companion_ecosystem_go_readiness_gate_latest.json",
            "latency_probe": "docs/final/artifacts/n8n_latency_probe_latest.json",
            "runtime_mode": "reports/myeongni_conflict_arbitration_runtime_mode_latest.json",
            "orchestrator": "docs/final/artifacts/mkm_global_orchestrator_latest.json",
        },
        "orchestrator_result": (orch.get("result") or {}),
        "approval_recommendation": "CONDITIONAL_GO_READY" if overall else "WATCH_HOLD",
        "note": "Even when conditions pass, live promotion remains human-gated and policy-bound.",
    }

    out_json = ART / "companion_ecosystem_go_approval_packet_latest.json"
    out_md = ART / "companion_ecosystem_go_approval_packet_latest.md"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Companion Ecosystem Conditional GO Packet",
        "",
        f"- generated_at_utc: `{packet['generated_at_utc']}`",
        f"- approval_recommendation: `{packet['approval_recommendation']}`",
        "",
        "## Conditions",
        f"- memory_drift_lt_0_05_3loops: `{cond1}`",
        f"- external_latency_p99_le_500ms: `{cond2}`",
        f"- manual_signoff_aggressive_verified: `{cond3}`",
        "",
        "## Runtime State",
        f"- orchestrator_decision: `{(orch.get('result') or {}).get('decision')}`",
        f"- orchestrator_reason: `{(orch.get('result') or {}).get('reason')}`",
        f"- effective_mode: `{runtime.get('mode')}`",
        f"- verification_pass: `{runtime.get('verification_pass')}`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "overall": overall, "recommendation": packet["approval_recommendation"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
