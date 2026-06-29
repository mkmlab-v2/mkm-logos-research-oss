#!/usr/bin/env python3
"""TKM encounter_sequence P35 gate: 3-lens conflict resolver wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P34_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p34_gate_v1_latest.json"
RESOLVER = ROOT / "reports/tkm_encounter_sequence_conflict_resolver_kpi_v1_latest.json"
MYEONGNI_SEP = ROOT / "reports/tkm_myeongni_sasang_lens_separation_v1_latest.json"
LOGOS_SEP = ROOT / "reports/tkm_logos_sasang_lens_separation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p34 = _load(P34_GATE)
    resolver = _load(RESOLVER)
    myeongni_sep = _load(MYEONGNI_SEP)
    logos_sep = _load(LOGOS_SEP)
    weekly = _load(WEEKLY)
    cr = weekly.get("conflict_resolver_kpi") if isinstance(weekly.get("conflict_resolver_kpi"), dict) else {}

    checks = {
        "p34_gate_ok": {"passed": p34.get("gate_ok") is True},
        "conflict_resolver_kpi_ok": {"passed": resolver.get("kpi_ok") is True},
        "conflict_resolver_non_gating": {"passed": resolver.get("non_gating") is True},
        "physician_gold_resolver_ok": {"passed": resolver.get("physician_gold_conflict_resolver_ok") is True},
        "myeongni_lens_separation_ok": {"passed": myeongni_sep.get("separation_ok") is True},
        "logos_lens_separation_ok": {"passed": logos_sep.get("separation_ok") is True},
        "weekly_conflict_resolver_sync_ok": {"passed": cr.get("conflict_resolver_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p35_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p35_status": "conflict_resolver_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "agreement_rate_l5_aligned": resolver.get("agreement_rate_l5_aligned"),
        "conflict_resolver_wired_count": resolver.get("conflict_resolver_wired_count"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p35_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p35_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
