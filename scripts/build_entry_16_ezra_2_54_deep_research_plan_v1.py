#!/usr/bin/env python3
"""ENTRY_16 Ezra.2.54 waiting-queue deep-research plan (NOT Ps.5) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
E16_SUM = ROOT / "docs/final/artifacts/entry16_source_hunt_summary.json"
E16_GATE = ROOT / "docs/final/artifacts/entry16_promotion_gate.json"
E16_LOCK = ROOT / "docs/final/artifacts/entry16_manual_promotion_decision_lock_latest.json"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
OUT_JSON = ROOT / "reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.json"
OUT_MD = ROOT / "reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


STEPS = [
    {
        "step": 1,
        "action": "Confirm 4Q117 extant verse range (Esr 4:2-6, 4:9-11, 5:17, 6:1-6) via QD transcription.",
        "primary_ref": "https://lexicon.qumran-digital.org/transcriptions/4Q117/2024-07-30/index.html",
        "outcome": "verified_fact_or_missing_anchor",
    },
    {
        "step": 2,
        "action": "Re-scan local etcbc align logs for Ezra ch.2 mapping (`('Ezra', '2'`).",
        "primary_ref": "data/etcbc-dss/log/align-*.txt",
        "outcome": "if found → human gate to update ENTRY_16; else keep locked",
    },
    {
        "step": 3,
        "action": "Classify non-DSS LXX/Swete witnesses at chapter/verse level only (proxy, not DSS line).",
        "primary_ref": "entry16_source_hunt_log.jsonl",
        "outcome": "proxy_candidate_manual_review",
    },
    {
        "step": 4,
        "action": "Document physical evidence (PAM/IAA plate, fragment sigla) without verse-level claim unless DJD line cite exists.",
        "outcome": "metadata_only_rows",
    },
    {
        "step": 5,
        "action": "Separate scholarly reconstruction from extant ink (Fact vs [HYPO]).",
        "outcome": "dual_report_block",
    },
    {
        "step": 6,
        "action": "Mark logical gaps as status=missing_anchor_until_source_update.",
        "outcome": "no CROSS_REF mutation without commander apply",
    },
    {
        "step": 7,
        "action": "Isolate disputed cohort/name-list harmonizations as shadow_data.",
        "outcome": "shadow_data_json_block",
    },
    {
        "step": 8,
        "action": "Emit plan JSON + MD; run evaluate_entry16_promotion_gate.py; pytest test_cross_ref_dss_schema ENTRY_16 gates.",
        "outcome": "exit 0 documented_hold",
    },
]


def build() -> dict[str, Any]:
    summ = _load(E16_SUM)
    gate = _load(E16_GATE)
    lock = _load(E16_LOCK)
    cross = _load(CROSS)
    e16 = next((e for e in cross.get("entries") or [] if e.get("entry_id") == "ENTRY_16"), {})
    sat = str(e16.get("satellite_ref") or "")

    return {
        "schema": "entry_16_ezra_deep_research_plan_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "writes_canon": False,
        "cross_ref_entry_id": "ENTRY_16",
        "canonical_ref": "Ezra.2.54",
        "not_psalm_5": True,
        "satellite_status": "missing_anchor_until_source_update"
        if "status=missing_anchor_until_source_update" in sat
        else "unknown",
        "waiting_queue": True,
        "source_hunt_summary": {
            "total_sources": summ.get("total_sources"),
            "has_direct_witness": summ.get("has_direct_witness"),
            "action_recommendation": summ.get("action_recommendation"),
        },
        "promotion_gate": {
            "decision": gate.get("decision"),
            "status": gate.get("status"),
        },
        "manual_lock": {
            "final_decision": lock.get("final_decision"),
            "dss_missing_anchor_fact_lock": (lock.get("constraints") or {}).get(
                "dss_missing_anchor_fact_lock"
            ),
        },
        "research_steps": STEPS,
        "forbidden": [
            "Map Ps.5.8-9 DSS witnesses to ENTRY_16",
            "Auto-apply CROSS_REF satellite_ref without commander approval",
            "Claim verified_anchor for Ezra.2.54 DSS line",
        ],
        "reproduce": "py scripts/build_entry_16_ezra_2_54_deep_research_plan_v1.py",
    }


def _md(doc: dict[str, Any]) -> str:
    lines = [
        "# [TRACK B / HYPO] ENTRY_16 — Ezra.2.54 waiting-queue research plan",
        "",
        f"- Generated: {doc['generated_at_utc']}",
        f"- **ENTRY_16** `Ezra.2.54` · **NOT Ps.5**",
        f"- Satellite: `{doc.get('satellite_status')}` · promotion: `{doc.get('promotion_gate', {}).get('status')}`",
        f"- Manual lock DSS missing-anchor: **{doc.get('manual_lock', {}).get('dss_missing_anchor_fact_lock')}**",
        "",
        "## 8-step plan",
        "",
    ]
    for s in doc.get("research_steps") or []:
        lines.append(f"{s['step']}. {s['action']}")
        lines.append(f"   - Ref: {s.get('primary_ref', '—')}")
        lines.append(f"   - Outcome: `{s.get('outcome')}`")
        lines.append("")
    lines.extend(
        [
            "## Forbidden",
            "",
        ]
    )
    for f in doc.get("forbidden") or []:
        lines.append(f"- {f}")
    lines.extend(
        [
            "",
            "Reproduce: `py scripts/build_entry_16_ezra_2_54_deep_research_plan_v1.py`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "entry_id": "ENTRY_16", "steps": len(doc["research_steps"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
