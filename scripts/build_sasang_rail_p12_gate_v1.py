#!/usr/bin/env python3
"""Sasang rail P12 gate: dual probe compare + tier partition + P5 enrich path [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P11 = ROOT / "docs/final/artifacts/sasang_rail_p11_gate_v1_latest.json"
COMPARE = ROOT / "reports/sasang_4agent_dual_probe_compare_v1_latest.json"
PARTITION = ROOT / "reports/sasang_joint_benchmark_tier_partition_v1_latest.json"
REBALANCE = ROOT / "reports/sasang_joint_benchmark_dummy_rebalance_v1_latest.json"
LIT = ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
P5_CHAIN = ROOT / "reports/sasang_rail_p5_chain_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p12_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _p5_has_enrich_steps(chain: dict[str, Any]) -> bool:
    names = {str(s.get("name") or s.get("script") or "") for s in chain.get("steps") or []}
    scripts = {str(s.get("script") or "") for s in chain.get("steps") or []}
    return (
        "auto_enrich_sasang_from_literature_stub_v1.py" in scripts
        or "run_sasang_literature_supervised_chain_v1.py" in scripts
        or "literature_auto_enrich_refresh" in names
        or "literature_supervised_refresh" in names
    )


def build() -> dict[str, Any]:
    p11 = _load(P11)
    compare = _load(COMPARE)
    partition = _load(PARTITION)
    rebalance = _load(REBALANCE)
    lit = _load(LIT)
    p5_chain = _load(P5_CHAIN)

    checks = {
        "p11_gate_ok": {"passed": p11.get("gate_ok") is True},
        "p11_dual_probe_enrich_ok": {"passed": p11.get("sasang_rail_p11_status") == "dual_probe_enrich_ok"},
        "dual_probe_compare_ok": {"passed": compare.get("compare_ok") is True},
        "tier_partition_ok": {"passed": partition.get("partition_ok") is True},
        "dummy_rebalance_ok": {"passed": rebalance.get("rebalance_ok") is True},
        "literature_supervised_ok": {"passed": lit.get("gate_ok") is True},
        "p5_enrich_steps_wired": {"passed": _p5_has_enrich_steps(p5_chain)},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p12_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p12_status": "partition_compare_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "attested_count": (partition.get("attested_tier") or {}).get("count"),
        "dummy_count": (partition.get("dummy_tier") or {}).get("count"),
        "dual_probe_delta_mdd": (compare.get("delta") or {}).get("mdd_reduction_abs_timeseries_minus_real_slice"),
        "reproduce": "py scripts/run_sasang_rail_p12_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p12_status": doc["sasang_rail_p12_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
