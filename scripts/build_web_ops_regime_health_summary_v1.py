#!/usr/bin/env python3
"""Aggregate web_ops_regime gate/CDP/baseline artifacts into one health summary JSON."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports/web_ops_regime_health_summary_v1_latest.json"
GATE = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
CDP = ROOT / "reports/web_ops_regime_cdp_probe_v1_latest.json"
BASELINES = ROOT / "reports/web_ops_regime_pointer_baselines_v1.json"
LIVE_OBS = ROOT / "reports/web_ops_regime_live_observation_v1_latest.json"
GPU_DOD = ROOT / "reports/nvidia_gpu_smoke_dod_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_summary() -> dict[str, Any]:
    gate = _read(GATE)
    cdp = _read(CDP)
    baselines = _read(BASELINES)
    live_obs = _read(LIVE_OBS)
    gpu_dod = _read(GPU_DOD)
    probe = cdp.get("probe") if isinstance(cdp.get("probe"), dict) else {}
    dual = probe.get("dual_observation") if isinstance(probe.get("dual_observation"), dict) else {}
    drift = probe.get("pointer_drift") if isinstance(probe.get("pointer_drift"), dict) else {}
    rows = baselines.get("baselines") if isinstance(baselines.get("baselines"), dict) else {}

    health_ok = bool(gate.get("gate_pass"))
    if dual and dual.get("alignment_pass") is False:
        health_ok = False
    if drift.get("drift_detected"):
        health_ok = False

    return {
        "schema": "web_ops_regime_health_summary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research",
        "health_ok": health_ok,
        "gate_pass": gate.get("gate_pass"),
        "worst_final_action": (gate.get("conflict_resolver") or {}).get("worst_final_action"),
        "probe_count": (gate.get("conflict_resolver") or {}).get("probe_count"),
        "observation_source": cdp.get("observation_source"),
        "dual_alignment_pass": dual.get("alignment_pass"),
        "pointer_drift_detected": drift.get("drift_detected"),
        "baseline_count": len(rows),
        "live_observation_present": LIVE_OBS.is_file(),
        "live_observation_url": live_obs.get("url"),
        "nebius_balance_usd": (probe.get("raw") or {}).get("balance_usd"),
        "cost_policy": gate.get("cost_policy"),
        "gpu_smoke_dod_decision": gpu_dod.get("decision"),
        "evidence_paths": {
            "gate": str(GATE),
            "cdp_probe": str(CDP),
            "baselines": str(BASELINES),
            "live_observation": str(LIVE_OBS),
            "gpu_smoke_dod": str(GPU_DOD),
        },
        "operator_hint_ko": gate.get("operator_hint_ko"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--require-health-ok", action="store_true")
    args = ap.parse_args()

    doc = build_summary()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "health_ok": doc["health_ok"]}, ensure_ascii=False))
    if args.require_health_ok and not doc["health_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
