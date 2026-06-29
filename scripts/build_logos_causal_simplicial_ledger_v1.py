#!/usr/bin/env python3
"""Seed logic-layer simplicial ledger from cross-theme hubs + B2B demo chain [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_LEDGER = ROOT / "reports/logos_track_b_research_v1_latest.json"
OUT_SNAPSHOT = ROOT / "reports/logos_causal_simplicial_snapshot_v1_latest.json"

import sys

sys.path.insert(0, str(ROOT))
from scripts.logos_causal_simplicial_engine_v1 import (  # noqa: E402
    LogosSimplicialEngine,
    load_ledger,
    replace_ledger_records_by_type,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _seed_from_bridge(engine: LogosSimplicialEngine, bridge: dict[str, Any]) -> int:
    count = 0
    for i, hub in enumerate((bridge.get("shared_hubs") or [])[:5]):
        hub_id = f"HUB_{i}"
        dan_id = f"L_DAN_{i}"
        john_id = f"L_JHN_{i}"
        score = float(hub.get("bridge_score") or 50) / 100.0
        engine.register_node(hub_id, f"SharedHub_{i}", "Hub")
        engine.register_node(dan_id, f"ThemeA_Anchor_{i}", "LogicRole")
        engine.register_node(john_id, f"ThemeB_Anchor_{i}", "LogicRole")
        engine.register_edge(f"E_D_{i}", dan_id, hub_id, weight=score)
        engine.register_edge(f"E_J_{i}", hub_id, john_id, weight=score)
        engine.register_triangle(f"T_{i}", dan_id, hub_id, john_id, weight=score)
        count += 1
    return count


def _seed_b2b_demo(engine: LogosSimplicialEngine) -> None:
    engine.register_node("N0", "Resource_Initial_State", "Antecedent")
    engine.register_node("N1", "Process_Bottleneck", "Intermediary")
    engine.register_node("N2", "Outcome_Risk_State", "Consequent")
    engine.register_node("NC", "Regulatory_Constraint", "Constraints")
    engine.register_edge("E_N0_N1", "N0", "N1", weight=0.95)
    engine.register_edge("E_N1_N2", "N1", "N2", weight=0.90)
    engine.register_edge("E_NC_N1", "NC", "N1", polarity=-1, weight=0.88)
    engine.register_triangle("T_B2B", "N0", "N1", "N2", weight=0.97)


def build(*, ledger_path: Path) -> dict[str, Any]:
    bridge = _load(ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json") or {}
    engine = LogosSimplicialEngine()
    hub_seeded = _seed_from_bridge(engine, bridge)
    _seed_b2b_demo(engine)

    evaluations: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    for start, end in (("N0", "N2"), ("L_DAN_0", "L_JHN_0")):
        ev = engine.evaluate_path(start, end)
        evaluations.append({"query": {"start": start, "end": end}, "evaluation": ev})
        ledger_rows.append(
            {
                "source_node": start,
                "target_node": end,
                "evaluation": ev,
                "technique": "democritus_inspired_simplicial_v1",
            }
        )

    replace_ledger_records_by_type(ledger_path, "dependency_path_eval", ledger_rows)

    snapshot = engine.snapshot()
    doc = {
        "schema": "logos_causal_simplicial_snapshot_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "content_layer_isolated": True,
        "hub_triangles_seeded": hub_seeded,
        "evaluations": evaluations,
        "engine_snapshot": snapshot,
        "ledger_path": str(ledger_path.relative_to(ROOT)).replace("\\", "/"),
        "reproduce": "py scripts/build_logos_causal_simplicial_ledger_v1.py",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", type=Path, default=OUT_LEDGER)
    ap.add_argument("--out", type=Path, default=OUT_SNAPSHOT)
    args = ap.parse_args()

    doc = build(ledger_path=args.ledger)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ledger = load_ledger(args.ledger)
    ok = int(ledger.get("record_count") or len(ledger.get("records") or [])) >= 2
    print(
        json.dumps(
            {
                "ok": ok,
                "hub_triangles": doc["hub_triangles_seeded"],
                "ledger_records": ledger.get("record_count"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
