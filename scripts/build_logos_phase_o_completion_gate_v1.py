#!/usr/bin/env python3
"""Phase O completion gate — hot-reload quality score [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_phase_o_completion_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    phase_o = _load(ROOT / "reports/logos_track_b_phase_o_v1_latest.json")
    mapping = _load(ROOT / "reports/logos_b2b_logic_mapping_audit_v1_latest.json")
    path_gate = _load(ROOT / "reports/logos_path_verification_gate_v1_latest.json")
    chain = _load(ROOT / "reports/logos_b2b_deterministic_chain_v1_latest.json")
    psi = _load(ROOT / "reports/logos_psi_logic_extraction_v1_latest.json")
    simplicial = _load(ROOT / "reports/logos_causal_simplicial_snapshot_v1_latest.json")
    closure = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")

    checks: list[dict[str, Any]] = []

    def _add(cid: str, ok: bool, weight: int, note: str = "") -> None:
        checks.append({"check_id": cid, "pass": bool(ok), "weight": weight, "note": note})

    _add("phase_o_ok", phase_o.get("ok") is True, 15)
    _add("mapping_7_7", (mapping.get("summary") or {}).get("mapping_pass") == "7/7", 15)
    _add(
        "path_gate_085",
        (path_gate.get("summary") or {}).get("gate_pass") is True,
        15,
        f"pass_rate={(path_gate.get('summary') or {}).get('pass_rate')}",
    )
    _add(
        "beta_resolved",
        (chain.get("summary") or {}).get("beta_resolved") is True,
        10,
    )
    _add(
        "psi_nodes_ge_4",
        len(((psi.get("logic_graph") or {}).get("nodes") or [])) >= 4,
        10,
        f"nodes={len(((psi.get('logic_graph') or {}).get('nodes') or []))}",
    )
    _add(
        "simplicial_triangles",
        int(simplicial.get("hub_triangles_seeded") or 0) >= 1,
        10,
    )
    _add(
        "ledger_eval_rows",
        int(phase_o.get("ledger_records") or 0) >= 2,
        10,
    )
    _add("integration_closure", closure.get("ok") is True, 10)
    _add("phase_o_in_closure", (closure.get("gates") or {}).get("phase_o_ok") is True, 5)

    earned = sum(c["weight"] for c in checks if c["pass"])
    total = sum(c["weight"] for c in checks)
    score = round(100.0 * earned / total, 1) if total else 0.0
    target = 90.0

    return {
        "schema": "logos_phase_o_completion_gate_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "completion_score": score,
        "completion_target": target,
        "completion_pass": score >= target,
        "checks": checks,
        "summary": {
            "earned_weight": earned,
            "total_weight": total,
            "failed_checks": [c["check_id"] for c in checks if not c["pass"]],
        },
        "reproduce": "py scripts/build_logos_phase_o_completion_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--min-score", type=float, default=90.0)
    args = ap.parse_args()
    doc = build()
    doc["completion_target"] = args.min_score
    doc["completion_pass"] = float(doc["completion_score"]) >= args.min_score
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["completion_pass"],
                "completion_score": doc["completion_score"],
                "failed": doc["summary"]["failed_checks"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["completion_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
