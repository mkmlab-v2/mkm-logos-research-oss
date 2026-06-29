#!/usr/bin/env python3
"""Aggregate Oracle narrative + closure observability (read-only SSOT) [HYPO].

Does NOT bump resonance_cap, deploy mkmlife, or rewrite CONSTITUTION.

  py scripts/build_logos_oracle_narrative_closure_observability_v1.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"

BIBLE_CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"
DRIFT = ROOT / "docs/final/artifacts/logos_lemma_spike_drift_check_v1_latest.json"
P21 = ROOT / "reports/logos_router_regression_bundle_v1_latest.json"
HD_MISSION = ROOT / "docs/final/artifacts/logos_oracle_lemma_60_hd_mission_v1_latest.json"
READINESS = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
VOC_CLOSURE = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"
PASSIVE_GOV = ROOT / "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _obs(name: str, ok: bool, *, path: str = "", detail: str = "") -> dict[str, Any]:
    return {"observation_id": name, "pass": ok, "path": path, "detail": detail}


def build_observability(root: Path) -> dict[str, Any]:
    bible = _read(root / BIBLE_CLOSURE.relative_to(ROOT))
    drift = _read(root / DRIFT.relative_to(ROOT))
    p21 = _read(root / P21.relative_to(ROOT))
    hd = _read(root / HD_MISSION.relative_to(ROOT))
    readiness = _read(root / READINESS.relative_to(ROOT))
    voc = _read(root / VOC_CLOSURE.relative_to(ROOT))
    passive = _read(root / PASSIVE_GOV.relative_to(ROOT))

    baseline = hd.get("baseline_facts") or {}
    p21_cap = (p21.get("bloom_cap") or {}).get("artifact")
    hd_cap = baseline.get("resonance_cap")
    narrative_eval = bible.get("narrative_path_eval") or {}

    observations: list[dict[str, Any]] = []

    observations.append(
        _obs(
            "bible_advancement_closure_hold",
            bible.get("send_gate") == "HOLD" and bible.get("research_only") is True,
            path=str(BIBLE_CLOSURE.relative_to(ROOT)),
            detail=f"narratives={bible.get('narrative_sample_count')} lemma={bible.get('lemma_hit_anchors')}",
        )
    )
    observations.append(
        _obs(
            "narrative_path_eval_rates",
            narrative_eval.get("sample_pass_rate") == 1.0
            and narrative_eval.get("router_hit_rate") == 1.0,
            path=str(BIBLE_CLOSURE.relative_to(ROOT)),
            detail=str(narrative_eval),
        )
    )
    observations.append(
        _obs(
            "lemma_spike_drift_compare",
            drift.get("pass") is True and (drift.get("drift_flags") or []) == [],
            path=str(DRIFT.relative_to(ROOT)),
            detail=f"drift_flags={drift.get('drift_flags')}",
        )
    )
    observations.append(
        _obs(
            "router_regression_p21",
            p21.get("chain_pass") is True and p21.get("send_gate") == "HOLD",
            path=str(P21.relative_to(ROOT)),
            detail=f"bloom_cap={p21.get('bloom_cap')}",
        )
    )
    observations.append(
        _obs(
            "resonance_cap_cross_ssot",
            p21_cap is not None
            and hd_cap is not None
            and int(p21_cap) == int(hd_cap),
            path=str(HD_MISSION.relative_to(ROOT)),
            detail=f"p21={p21_cap} hd={hd_cap} version={hd.get('version')}",
        )
    )
    observations.append(
        _obs(
            "tier2_module_prep",
            readiness.get("tier2_prep_ready") is True,
            path=str(READINESS.relative_to(ROOT)),
            detail=(
                f"tier2_prep={readiness.get('tier2_prep_ready')} "
                f"tier1={readiness.get('tier1_module_ssot_ready')}"
            ),
        )
    )
    observations.append(
        _obs(
            "tier2_incremental_append_unlock",
            readiness.get("tier2_cursor_rules_full_upgrade_ready") is True,
            path=str(READINESS.relative_to(ROOT)),
            detail=(
                f"tier2_unlock={readiness.get('tier2_cursor_rules_full_upgrade_ready')} "
                f"send_gate={readiness.get('send_gate')}"
            ),
        )
    )
    observations.append(
        _obs(
            "tier3_narrative_upgrade_unlock",
            readiness.get("tier3_constitution_narrative_full_upgrade_ready") is True,
            path=str(READINESS.relative_to(ROOT)),
            detail=(
                f"tier3_unlock={readiness.get('tier3_constitution_narrative_full_upgrade_ready')} "
                f"tier3_protocol={readiness.get('tier3_narrative_upgrade_protocol')}"
            ),
        )
    )
    observations.append(
        _obs(
            "han_vocology_pilot_closure",
            voc.get("ok") is True and voc.get("send_gate") == "HOLD",
            path=str(VOC_CLOSURE.relative_to(ROOT)),
            detail=f"cohorts={voc.get('cohort_count')} rows={voc.get('row_count')}",
        )
    )
    passive_ok = (
        (passive.get("lexicon_rail") or {}).get("ok") is True
        and (passive.get("drift") or {}).get("drift_flags") in ([], None)
    ) if passive else True
    observations.append(
        _obs(
            "passive_drift_governance_digest",
            passive_ok,
            path=str(PASSIVE_GOV.relative_to(ROOT)),
            detail="missing_ok" if not passive else f"lexicon_ok={(passive.get('lexicon_rail') or {}).get('ok')}",
        )
    )

    all_pass = all(o["pass"] for o in observations)

    return {
        "schema": "logos_oracle_narrative_closure_observability_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "observation_pass": all_pass,
        "observations_pass_count": sum(1 for o in observations if o["pass"]),
        "observations_total": len(observations),
        "observations": observations,
        "snapshot": {
            "resonance_cap": hd_cap,
            "hd_mission_version": hd.get("version"),
            "narrative_samples": bible.get("narrative_sample_count"),
            "lemma_hit_anchors": bible.get("lemma_hit_anchors"),
            "router_hit_rate": narrative_eval.get("router_hit_rate"),
            "gold_required_all_pass": baseline.get("gold_required_all_pass"),
            "han_vocology_cohorts": voc.get("cohort_count"),
            "narrative_lane_send_gate": readiness.get("send_gate"),
            "tier2_cursor_rules_full_upgrade_ready": readiness.get(
                "tier2_cursor_rules_full_upgrade_ready"
            ),
            "tier3_constitution_narrative_full_upgrade_ready": readiness.get(
                "tier3_constitution_narrative_full_upgrade_ready"
            ),
            "read_only": True,
        },
        "repro_one_shot": "py scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
        "boundary_ack": (
            "Observability aggregate only — NOT cap bump, NOT mkmlife deploy, "
            "NOT Track A, NOT 「성경 AI 진화 완료」."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build_observability(args.workspace_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.out} observation_pass={doc['observation_pass']} "
        f"{doc['observations_pass_count']}/{doc['observations_total']}"
    )
    return 0 if doc["observation_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
