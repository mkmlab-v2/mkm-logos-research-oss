#!/usr/bin/env python3
"""Phase 3b PoC status — hyper-personal intake + NEWS-HP-RT shadow."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
INTAKE = ART / "hyper_personal_news_intake_v1_latest.json"
HP_BENCH = ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json"
PHASE3 = ART / "saving_the_news_phase3_poc_status_v1_latest.json"
FIXTURE = ART / "fixtures/hyper_personal_news_intake_stub_v1.example.json"
OUT_JSON = ART / "saving_the_news_phase3b_poc_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_status() -> dict[str, Any]:
    intake = _read(INTAKE)
    hp_bench = _read(HP_BENCH)
    phase3 = _read(PHASE3)
    p3_ok = bool((phase3.get("exit_criteria") or {}).get("roadmap_complete_internal"))
    hp_measured = hp_bench.get("measurement_status") == "COMPLETE"
    logos_ok = (intake.get("lenses") or {}).get("logos", {}).get("role") == "NON_GATING"
    cms_blocked = (intake.get("final") or {}).get("cms_publish_allowed") is False
    decision_ok = (intake.get("final") or {}).get("decision_label") in ("WATCH", "HOLD")

    exit_criteria = {
        "phase3_promote_gate": p3_ok,
        "P3b-S1_intake_latest": INTAKE.is_file(),
        "P3b-S2_fixture_present": FIXTURE.is_file(),
        "P3b-S3_news_hp_rt_measured": hp_measured,
        "P3b-S4_cms_publish_blocked": cms_blocked,
        "P3b-S5_logos_non_gating": logos_ok,
        "P3b-S6_decision_label_bounded": decision_ok,
        "shadow_observation_only": True,
    }
    complete = all(
        [
            INTAKE.is_file(),
            FIXTURE.is_file(),
            cms_blocked,
            logos_ok,
            decision_ok,
            p3_ok,
        ]
    )

    return {
        "schema": "saving_the_news_phase3b_poc_status_v1",
        "phase": "Phase 3b — Hyper-Personal weight slots [HYPO]",
        "status": "POC_COMPLETE" if complete and hp_measured else "POC_IN_PROGRESS",
        "lane": "research_only",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "intake_snapshot": {
            "decision_label": (intake.get("final") or {}).get("decision_label"),
            "regime_id": (intake.get("field") or {}).get("regime_id"),
            "priors": (intake.get("field") or {}).get("priors"),
        },
        "hp_bench_snapshot": {
            "measurement_status": hp_bench.get("measurement_status"),
            "delta_token_saving": (
                (hp_bench.get("delta_vs_news_rt_baseline") or {}).get(
                    "token_saving_ratio_delta_hp_minus_baseline"
                )
            ),
        },
        "explicit_gaps": [
            "Not a consumer news terminal or ad-free public feed.",
            "Daily shadow: intake-only; full NEWS-HP-RT via weekly refresh gate (2026-06-08+).",
            "Commander briefing: MKM_HYPER_PERSONAL_INTAKE_SHADOW default on.",
            "CMS publish lock product not shipped.",
            "Priors do not single-anchor override news ranking.",
        ],
        "refresh_gate_ref": "docs/final/artifacts/saving_the_news_news_hp_rt_refresh_gate_v1_latest.json",
        "refs": {
            "blueprint_section": "docs/research/saving_the_news_blueprint_v1.md#§10",
            "intake_json": "docs/final/artifacts/hyper_personal_news_intake_v1_latest.json",
            "hp_bench_json": "docs/final/artifacts/saving_the_news_news_hp_rt_bench_result_v1_latest.json",
            "fixture": "docs/final/artifacts/fixtures/hyper_personal_news_intake_stub_v1.example.json",
        },
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
