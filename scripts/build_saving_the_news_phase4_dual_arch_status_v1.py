#!/usr/bin/env python3
"""Phase 4 dual-architecture status — §11 common evo vs §10 personal [HYPO]."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
FIXTURE = ART / "fixtures/news_evo_bench_contract_v1.example.json"
PHASE3B = ART / "saving_the_news_phase3b_poc_status_v1_latest.json"
EVO_BENCH = ART / "saving_the_news_news_evo_bench_result_v1_latest.json"
OUT_JSON = ART / "saving_the_news_phase4_dual_arch_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_status() -> dict[str, Any]:
    fixture = _read(FIXTURE)
    p3b = _read(PHASE3B)
    evo = _read(EVO_BENCH)
    p3b_ok = p3b.get("status") == "POC_COMPLETE"
    evo_measured = evo.get("measurement_status") in ("COMPLETE", "COMPLETE_PARTIAL")
    fixture_ok = FIXTURE.is_file() and fixture.get("schema") == "news_evo_bench_contract_v1"
    evo_mode = (fixture.get("evolution") or {}).get("mode")
    cms_blocked = (fixture.get("final") or {}).get("cms_publish_allowed") is False

    exit_criteria = {
        "P4-S1_section11_fixture": fixture_ok,
        "P4-S2_dual_regime_field": (fixture.get("field") or {}).get("regime_id")
        == "regime_saving_the_news_dual_architecture_hypo",
        "P4-S3_personal_rail_frozen_ref": p3b_ok,
        "P4-S4_evo_suggest_only": evo_mode == "suggest_only_offline",
        "P4-S5_loss_four_axes": all(
            k in (fixture.get("loss_axes") or {})
            for k in ("L_price", "L_general", "L_compression_raw", "L_calibration")
        ),
        "P4-S6_cms_publish_blocked": cms_blocked,
        "P4-S7_news_evo_bench_measured": evo_measured and EVO_BENCH.is_file(),
        "shadow_observation_only": True,
    }
    complete = all(exit_criteria.values())

    return {
        "schema": "saving_the_news_phase4_dual_arch_status_v1",
        "phase": "Phase 4 — Dual architecture §11 common evo vs §10 personal [HYPO]",
        "status": "POC_COMPLETE" if complete else "POC_IN_PROGRESS",
        "lane": "research_only",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "dual_rail_snapshot": {
            "common_bench_id": (fixture.get("evolution") or {}).get("bench_id"),
            "personal_regime": (fixture.get("field") or {}).get("personal_rail_id"),
            "decision_label": (fixture.get("final") or {}).get("decision_label"),
            "L_total_hypo": (evo.get("composite_hypo") or {}).get("L_total_hypo"),
            "news_evo_bench_status": evo.get("measurement_status"),
        },
        "explicit_gaps": [
            "DSPy/GEPA runtime not wired — evolve_pre_news suggest-only only.",
            "mkmlife 6–9 card viewer join not implemented.",
            "Walkforward join artifact optional — calibration may use general_prophecy ECE proxy.",
            "B→A·live trading·CMS auto-publish forbidden.",
        ],
        "refs": {
            "blueprint_section_11": "docs/research/saving_the_news_blueprint_v1.md",
            "contract_fixture": "docs/final/artifacts/fixtures/news_evo_bench_contract_v1.example.json",
            "phase3b_status": "docs/final/artifacts/saving_the_news_phase3b_poc_status_v1_latest.json",
            "news_evo_bench": "docs/final/artifacts/saving_the_news_news_evo_bench_result_v1_latest.json",
        },
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
