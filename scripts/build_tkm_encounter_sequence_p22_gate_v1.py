#!/usr/bin/env python3
"""TKM encounter_sequence P22 gate: live HTTP + weekly multiturn churn [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P21_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p21_gate_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
HTTP = ROOT / "reports/no1kmedi_encounter_sequence_api_http_smoke_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p22_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p21 = _load(P21_GATE)
    weekly = _load(WEEKLY)
    http = _load(HTTP)
    churn = weekly.get("multiturn_churn_kpi") if isinstance(weekly.get("multiturn_churn_kpi"), dict) else {}

    checks = {
        "p21_gate_ok": {"passed": p21.get("gate_ok") is True},
        "http_smoke_ok": {"passed": http.get("http_smoke_ok") is True},
        "weekly_report_ok": {"passed": weekly.get("weekly_ok") is True},
        "multiturn_churn_ok": {"passed": churn.get("multiturn_churn_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p22_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p22_status": "live_api_weekly_churn_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "multiturn_churn_kpi": churn,
        "http_smoke_ref": str(HTTP).replace("\\", "/"),
        "weekly_report_ref": str(WEEKLY).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p22_chain_v1.py --with-p21-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p22_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
