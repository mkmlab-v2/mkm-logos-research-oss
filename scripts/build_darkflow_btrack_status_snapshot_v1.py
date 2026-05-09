#!/usr/bin/env python3
"""Build a compact status snapshot for Dark Flow B-track outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _load(path)
    except Exception:
        return {}


def main() -> int:
    gate = _safe_load(ART / "darkflow_btrack_gate_latest.json")
    dual = _safe_load(ART / "darkflow_btrack_dual_policy_report_latest.json")
    eval_latest = _safe_load(ART / "darkflow_btrack_eval_latest.json")

    snapshot = {
        "schema": "darkflow_btrack_status_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "RESEARCH_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "single_policy_decision": gate.get("decision", "n/a"),
        "single_policy_best_composite_score": gate.get("best_composite_score", "n/a"),
        "single_policy_top_hypothesis": (
            (gate.get("ranked_hypotheses") or [{}])[0].get("label", "n/a")
            if isinstance(gate.get("ranked_hypotheses"), list)
            else "n/a"
        ),
        "dual_policy": {
            "conservative_decision": (dual.get("conservative") or {}).get("decision", "n/a"),
            "exploratory_decision": (dual.get("exploratory") or {}).get("decision", "n/a"),
            "top_hypothesis_aligned": dual.get("top_hypothesis_aligned", "n/a"),
        },
        "eval_latest_hypotheses_count": len(eval_latest.get("hypotheses", []))
        if isinstance(eval_latest.get("hypotheses"), list)
        else 0,
        "evidence_paths": {
            "eval_latest_json": str(ART / "darkflow_btrack_eval_latest.json"),
            "single_gate_json": str(ART / "darkflow_btrack_gate_latest.json"),
            "dual_report_json": str(ART / "darkflow_btrack_dual_policy_report_latest.json"),
            "brief_md": str(ART / "darkflow_btrack_brief_latest.md"),
            "dual_md": str(ART / "darkflow_btrack_dual_policy_report_latest.md"),
        },
    }

    out_json = ART / "darkflow_btrack_status_snapshot_latest.json"
    out_json.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
