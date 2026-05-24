#!/usr/bin/env python3
"""Outer-ring lens RAG dry-run gate: compression core frozen vs 3-lens advisory only.

Read-only by default. Optional --run-coordinator rebuilds B-track fusion JSON only.
Does NOT touch master codebook, Track A promotion, or gematria bridge policy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = ART / "outer_lens_rag_dryrun_gate_v1_latest.json"

ACTIVE_REPORT = ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
ATOMS_SUMMARY = PILOT / "original_language_master_atoms_summary_latest.json"
THREE_LENS_OUT = ART / "three_lens_fusion_coordinator_v1_latest.json"
LOGOS_GATE_OUT = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
CONFLICT_RESOLVER = ART / "conflict_resolver_v1.json"

# Paths that must not be modified during a dry-run (existence check only).
FORBIDDEN_WRITE_HINTS = (
    "master_codebook_lexicon",
    "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    "golden_40",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_track_a_isolation(active: dict[str, Any]) -> dict[str, Any]:
    cm = active.get("compression_metrics") if isinstance(active.get("compression_metrics"), dict) else {}
    ap = active.get("active_profile") if isinstance(active.get("active_profile"), dict) else {}
    qg = active.get("quality_gate") if isinstance(active.get("quality_gate"), dict) else {}
    sp = cm.get("semantic_pointer_channel") if isinstance(cm.get("semantic_pointer_channel"), dict) else {}
    bridge_off = ap.get("apply_gematria_4d_bridge_policy") is False
    pointer_off = sp.get("enabled") is False
    saving = float(cm.get("global_token_saving_rate") or 0.0)
    jaccard = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0.0)
    ms_floor_jaccard = 0.890
    policy_floor_saving = float(qg.get("ultra_saving_policy_min") or 0.47)
    ms_headline_ok = jaccard >= ms_floor_jaccard
    checks = {
        "active_report_exists": bool(active),
        "bridge_policy_off": bridge_off,
        "semantic_pointer_off": pointer_off,
        "saving_ge_policy_floor": saving >= policy_floor_saving,
    }
    isolation_passed = all(checks.values())
    return {
        "checks": checks,
        "ms_headline": {
            "jaccard_ge_0_890": ms_headline_ok,
            "ms_paste_promotion_blocked": not ms_headline_ok,
            "policy": "FAIL-COMP-004 — disk ACTIVE may differ from MS frozen headline",
        },
        "metrics": {
            "global_token_saving_rate": round(saving, 6),
            "avg_reconstruction_fidelity_jaccard": round(jaccard, 6),
            "ms_headline_policy_saving_pct": 47.5,
            "ms_headline_policy_jaccard": ms_floor_jaccard,
            "disk_active_label": "49.1%/0.873 (2026-05-23 MISSION_LOG; do not paste as MS KPI without signoff)",
        },
        "passed": isolation_passed,
        "note": "Isolation pass does not imply MS headline promotion; see ms_headline block.",
    }


def _check_codebook_freeze(summary: dict[str, Any]) -> dict[str, Any]:
    stats = summary.get("stats") if isinstance(summary.get("stats"), dict) else {}
    unique = int(stats.get("unique_master_atoms") or 0)
    checks = {
        "atoms_summary_exists": bool(summary),
        "unique_atoms_41658": unique == 41_658,
        "unique_atoms_ge_41600": unique >= 41_600,
    }
    return {
        "checks": checks,
        "unique_master_atoms": unique,
        "passed": checks["atoms_summary_exists"] and checks["unique_atoms_ge_41600"],
    }


def _check_lens_contracts(three_lens: dict[str, Any], conflict: dict[str, Any]) -> dict[str, Any]:
    coord = three_lens.get("coordinator") if isinstance(three_lens.get("coordinator"), dict) else {}
    contract = three_lens.get("lens_contract") if isinstance(three_lens.get("lens_contract"), dict) else {}
    policy = conflict.get("policy") if isinstance(conflict.get("policy"), dict) else {}
    checks = {
        "three_lens_exists": bool(three_lens),
        "track_b_track": str(three_lens.get("track") or "").upper() == "B_TRACK",
        "coordinator_research_only": coord.get("research_only") is True,
        "coordinator_human_signoff": coord.get("human_signoff_required") is True,
        "field_primary_in_contract": "field gate" in str(contract.get("final_policy") or "").lower(),
        "logos_non_gating_in_contract": "non_gating" in str(contract.get("logos_role") or "").lower(),
        "conflict_resolver_conservative": policy.get("conservative_override") is True,
        "conflict_resolver_logos_non_gating": policy.get("logos_non_gating") is True,
    }
    return {"checks": checks, "passed": all(checks.values())}


def _check_logos_track_wall(gate: dict[str, Any]) -> dict[str, Any]:
    wall = gate.get("track_wall") if isinstance(gate.get("track_wall"), dict) else {}
    checks = {
        "gate_json_exists": bool(gate),
        "research_only": gate.get("research_only") is True,
        "track_a_compression_touch_false": wall.get("track_a_compression_touch") is False,
        "use_gematria_4d_bridge_false": wall.get("use_gematria_4d_bridge") is False,
        "a_track_auto_promotion_false": wall.get("a_track_auto_promotion") is False,
    }
    return {"checks": checks, "passed": all(checks.values())}


def _run_coordinator() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_three_lens_fusion_coordinator_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "step": "build_three_lens_fusion_coordinator_v1",
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or proc.stdout or "")[-400:] if proc.returncode else None,
    }


def _run_logos_gate() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "step": "check_logos_rag_btrack_promotion_gate_v1",
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or proc.stdout or "")[-400:] if proc.returncode else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-coordinator", action="store_true", help="Rebuild three_lens_fusion_coordinator JSON (B-track)")
    ap.add_argument("--run-logos-gate", action="store_true", help="Refresh logos_rag_btrack_promotion_gate JSON")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.run_coordinator:
        steps.append(_run_coordinator())
    if args.run_logos_gate:
        steps.append(_run_logos_gate())

    active = _load(ACTIVE_REPORT)
    summary = _load(ATOMS_SUMMARY)
    three_lens = _load(THREE_LENS_OUT)
    conflict = _load(CONFLICT_RESOLVER)
    logos_gate = _load(LOGOS_GATE_OUT)

    track_a = _check_track_a_isolation(active)
    codebook = _check_codebook_freeze(summary)
    lens = _check_lens_contracts(three_lens, conflict)
    logos = _check_logos_track_wall(logos_gate)

    sections = [track_a, codebook, lens, logos]
    isolation_ok = all(s.get("passed") for s in sections) and all(s.get("exit_code", 0) == 0 for s in steps)
    ms_headline = track_a.get("ms_headline") if isinstance(track_a.get("ms_headline"), dict) else {}
    ok = isolation_ok

    payload: dict[str, Any] = {
        "schema": "outer_lens_rag_dryrun_gate_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "ok": ok,
        "isolation_ok": isolation_ok,
        "ms_headline_promotion_ok": bool(ms_headline.get("jaccard_ge_0_890")),
        "forbidden_during_dryrun": list(FORBIDDEN_WRITE_HINTS),
        "recommended_routines": {
            "logos_btrack": "py scripts/run_logos_rag_recommended_routine_v1.py",
            "logos_r6": "powershell -File scripts/Run-LogosRagR6_v1.ps1",
            "three_lens": "py scripts/build_three_lens_fusion_coordinator_v1.py",
            "compression_hardening": "py scripts/compression_hardening_milestone_status_v1.py (if present) or reports artifact",
        },
        "kpi_labels": {
            "ms_paste_frozen": "47.5% saving / 0.890 jaccard (FAIL-COMP-004; no ACTIVE overwrite)",
            "disk_active_measurement": track_a.get("metrics", {}),
            "logos_rag": "[HYPO] B-track; not prophecy hit-rate or Track A",
        },
        "coordinator_contract_summary": {
            "naming": "4AI core + Absolute Balance Coordinator Mode (state, not 5th AI)",
            "final_action_ssot": "1차 regime_map Field + ops gates; 3 lenses advisory",
            "three_lens_final_policy": (three_lens.get("lens_contract") or {}).get("final_policy"),
            "not_verified_in_repo": ["most_conservative_wins", "direction_override_allowed"],
        },
        "sections": {
            "track_a_isolation": track_a,
            "codebook_freeze": codebook,
            "lens_advisory_contract": lens,
            "logos_outer_ring": logos,
        },
        "optional_steps": steps,
    }

    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
