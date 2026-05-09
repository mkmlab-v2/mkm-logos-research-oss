#!/usr/bin/env python3
"""Append latest darkflow ops truth panel status to history log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    panel_path = ART / "darkflow_ops_truth_panel_latest.json"
    if not panel_path.exists():
        raise FileNotFoundError(f"Missing panel json: {panel_path}")
    panel = _load(panel_path)

    entry = {
        "generated_at_utc": panel.get("generated_at_utc"),
        "overall_status": panel.get("overall_status"),
        "single_policy": (panel.get("decisions") or {}).get("single_policy"),
        "conservative_policy": (panel.get("decisions") or {}).get("conservative_policy"),
        "exploratory_policy": (panel.get("decisions") or {}).get("exploratory_policy"),
        "top_hypothesis": (panel.get("decisions") or {}).get("top_hypothesis"),
        "freshness_passed": (panel.get("freshness") or {}).get("freshness_passed"),
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    log_path = REPORTS / "darkflow_ops_history_log.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(str(log_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
