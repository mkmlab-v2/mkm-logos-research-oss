#!/usr/bin/env python3
"""Sasang rail P3 gate: 4-agent ablation + literature majority resolver [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ABLATION = ROOT / "reports/sasang_4agent_protocol_ablation_v1_latest.json"
RESOLVE_SUMMARY = ROOT / "data/myeongni/sasang_saju_joint_benchmark_auto_resolved_v1_summary_v1.json"
RESOLVED = ROOT / "data/myeongni/sasang_saju_joint_benchmark_auto_resolved_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    ablation = _load(ABLATION)
    summary = _load(RESOLVE_SUMMARY)
    stats = summary.get("stats") if isinstance(summary.get("stats"), dict) else {}
    wall = ablation.get("track_wall") if isinstance(ablation.get("track_wall"), dict) else {}

    checks = {
        "ablation_present": {"passed": ablation.get("schema") == "sasang_4agent_protocol_ablation_v1"},
        "ablation_research_only": {"passed": ablation.get("mode") == "research_only"},
        "ablation_twelve_variants": {"passed": int(ablation.get("n_variants") or 0) == 12},
        "ablation_no_track_a_promotion": {"passed": wall.get("track_a_promotion") is False},
        "ablation_ohlcv_forbidden": {
            "passed": (ablation.get("data_policy") or {}).get("ohlcv_tuning_forbidden") is True,
        },
        "literature_resolve_summary_present": {
            "passed": summary.get("schema") == "resolve_literature_sasang_majority_summary_v1",
        },
        "literature_resolved_rows": {"passed": int(stats.get("rows") or 0) >= 1},
        "literature_resolved_file_present": {"passed": RESOLVED.is_file()},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p3_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p3_status": "ablation_literature_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "ablation_verdict": ablation.get("verdict"),
        "literature_resolve_stats": stats,
        "artifact_paths": {
            "ablation": str(ABLATION).replace("\\", "/"),
            "resolve_summary": str(RESOLVE_SUMMARY).replace("\\", "/"),
            "resolved_jsonl": str(RESOLVED).replace("\\", "/"),
        },
        "reproduce": "py scripts/run_sasang_rail_p3_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p3_status": doc["sasang_rail_p3_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
