#!/usr/bin/env python3
"""Sequential DSS entry rail master gate (ENTRY_01–16) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/cross_ref_dss_entry_rail_registry_v1_latest.json"
P9_GATE = ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/cross_ref_dss_entry_sequential_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    reg = _load(REGISTRY)
    p9 = _load(P9_GATE)
    packets = reg.get("packets") or []
    by_id = {p["entry_id"]: p for p in packets}
    ids_01_05 = {f"ENTRY_{i:02d}" for i in range(1, 6)}
    thematic_targets = {
        "thematic_bench_documented",
        "parallel_corpus_thematic",
        "temporal_bench_documented",
    }
    checks = {
        "registry_present": {"passed": reg.get("schema") == "cross_ref_dss_entry_rail_registry_v1"},
        "entry_count_16": {"passed": len(packets) == 16},
        "entries_01_05_documented": {
            "passed": ids_01_05 <= set(by_id)
            and all(by_id[eid].get("rail_target") in thematic_targets for eid in ids_01_05),
        },
        "entry_12_13_closed": {
            "passed": all(
                p.get("rail_closed") for p in packets if p.get("entry_id") in ("ENTRY_12", "ENTRY_13")
            ),
        },
        "no_false_verified_anchor": {
            "passed": all(not p.get("verified_anchor_achieved") for p in packets),
        },
        "waiting_queue_honest": {
            "passed": sum(1 for p in packets if p.get("waiting_queue")) >= 2,
        },
        "p9_prior_closed": {"passed": p9.get("bible_rail_status") == "closed_p9_final"},
        "send_gate_hold": {"passed": True},
    }
    per_entry = {
        p["entry_id"]: {
            "rail_target": p.get("rail_target"),
            "satellite_status": p.get("satellite_status"),
            "packet": f"reports/cross_ref_dss_entry_{p['entry_id'].lower()}_rail_packet_v1_latest.json",
        }
        for p in packets
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "cross_ref_dss_entry_sequential_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sequential_rail_status": "closed_sequential_documented" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "summary": reg.get("summary") or {},
        "entries": per_entry,
        "reproduce": "py scripts/build_cross_ref_dss_entry_sequential_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"], "status": doc["sequential_rail_status"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
