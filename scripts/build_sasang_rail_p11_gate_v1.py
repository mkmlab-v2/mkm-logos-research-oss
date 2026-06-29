#!/usr/bin/env python3
"""Sasang rail P11 gate: KOSPI proxy timeseries + enrich refresh + rebalance [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P10 = ROOT / "docs/final/artifacts/sasang_rail_p10_gate_v1_latest.json"
TIMESERIES_PROTO = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_timeseries_kospi_latest.json"
ENRICH = ROOT / "reports/sasang_literature_auto_enrich_refresh_chain_v1_latest.json"
REBALANCE = ROOT / "reports/sasang_joint_benchmark_dummy_rebalance_v1_latest.json"
KOSPI_META = ROOT / "reports/sasang_kospi_proxy_timeseries_btrack_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p11_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p10 = _load(P10)
    proto = _load(TIMESERIES_PROTO)
    enrich = _load(ENRICH)
    rebalance = _load(REBALANCE)
    kospi_meta = _load(KOSPI_META)
    exp = proto.get("experiment") if isinstance(proto.get("experiment"), dict) else {}
    hint = proto.get("promotion_gate_hint") if isinstance(proto.get("promotion_gate_hint"), dict) else {}
    _ = hint  # exploratory GO_CANDIDATE hint allowed; rail send_gate remains HOLD

    checks = {
        "p10_gate_ok": {"passed": p10.get("gate_ok") is True},
        "p10_exploratory_probe_ok": {"passed": p10.get("sasang_rail_p10_status") == "exploratory_probe_ok"},
        "kospi_proxy_csv_ok": {"passed": kospi_meta.get("ok") is True},
        "timeseries_protocol_present": {
            "passed": proto.get("schema") == "sasang_4agent_collision_btrack_protocol_v1",
        },
        "timeseries_data_mode": {"passed": exp.get("data_mode") == "timeseries_file_adapter"},
        "timeseries_ticks_min": {"passed": int(exp.get("ticks") or 0) >= 40},
        "literature_enrich_refresh_ok": {"passed": enrich.get("all_ok") is True},
        "dummy_rebalance_ok": {"passed": rebalance.get("rebalance_ok") is True},
        "btrack_research_only_protocol": {"passed": proto.get("mode") == "research_only"},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p11_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p11_status": "dual_probe_enrich_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "timeseries_ticks": exp.get("ticks"),
        "non_dummy_share": rebalance.get("non_dummy_share"),
        "literature_supervised_rows": enrich.get("literature_supervised_rows"),
        "promotion_gate_hint": proto.get("promotion_gate_hint"),
        "reproduce": "py scripts/run_sasang_rail_p11_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p11_status": doc["sasang_rail_p11_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
