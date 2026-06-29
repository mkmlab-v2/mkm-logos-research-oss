#!/usr/bin/env python3
"""Build TKM encounter_sequence L0 safety KPI rollup [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/tkm_encounter_sequence_l0_kpi_v1_latest.json"
SUMMARY = ROOT / "reports/encounter_sequence_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    l0_mod = _load_mod("scripts/tkm_encounter_sequence_l0_router_v1.py")
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    router = _load_mod("scripts/l0_red_flag_router_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = l0_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    summary = _load_json(SUMMARY)

    wired = 0
    triggered = 0
    gold_wired = 0
    gold_total = 0

    for row in records:
        if l0_mod.is_l0_wired(row):
            wired += 1
        state = router.collect_l0_state_from_sequence(row)
        if state.get("triggered") is True:
            triggered += 1
        if not clf_mod.is_dummy_encounter_sequence(row):
            gold_total += 1
            if l0_mod.is_l0_wired(row):
                gold_wired += 1

    def _rate(num: int, den: int) -> float | None:
        if not den:
            return None
        return round(num / den, 4)

    template_ok = (ROOT / "docs/final/templates/l0_red_flag_escalation_ko_v1.json").is_file()
    kpi_ok = (
        template_ok
        and wired >= 1
        and _rate(wired, len(records)) is not None
        and (wired / max(len(records), 1)) >= 0.5
        and int(summary.get("l0_red_flag_trigger_events") or 0) >= 1
    )

    return {
        "schema": "tkm_encounter_sequence_l0_kpi_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "kpi_ok": kpi_ok,
        "all_ledger": {
            "sequence_count": len(records),
            "l0_router_wired_count": wired,
            "l0_router_wired_rate": _rate(wired, len(records)),
            "l0_trigger_count": triggered,
            "l0_summary_trigger_events": int(summary.get("l0_red_flag_trigger_events") or 0),
        },
        "physician_gold_only": {
            "sequence_count": gold_total,
            "l0_router_wired_count": gold_wired,
            "l0_router_wired_rate": _rate(gold_wired, gold_total) if gold_total else None,
        },
        "note_ko": "L0는 non_gating 안전층; 사상 ai_hypothesis·헤드라인 KPI 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_l0_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("kpi_ok"),
                "wired_rate": (doc.get("all_ledger") or {}).get("l0_router_wired_rate"),
            }
        )
    )
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
