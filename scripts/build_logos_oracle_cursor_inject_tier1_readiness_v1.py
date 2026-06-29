#!/usr/bin/env python3
"""Build Oracle Logos Cursor-inject Tier-1 module readiness gate ([HYPO] / B-track).

Tier-1 = module SSOT (paths + reproducible chains). NOT full CONSTITUTION/Cursor rewrite.

  py scripts/build_logos_oracle_cursor_inject_tier1_readiness_v1.py
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
OUT = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
OVERLAY_CHAIN = ROOT / "reports/mkm_ops_memory_logos_math_overlay_chain_v1_latest.json"
INDEX = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
UPGRADE = ROOT / "reports/mkm_cursor_session_upgrade_v1_latest.json"
DRIFT = ROOT / "docs/final/artifacts/logos_lemma_spike_drift_check_v1_latest.json"
P21 = ROOT / "reports/logos_router_regression_bundle_v1_latest.json"
HD_MISSION = ROOT / "docs/final/artifacts/logos_oracle_lemma_60_hd_mission_v1_latest.json"
VOC_CLOSURE = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"
WIRING = ROOT / "docs/final/artifacts/logos_theory_implementation_wiring_v1.json"
CONSTITUTION_POINTER = (
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    " — Logos ops memory Cursor inject 보강 (2026-06-19)"
)
TIER2_PROTOCOL_REL = (
    "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"
)
TIER1_CHECK_IDS = frozenset(
    {
        "logos_math_overlay_chain",
        "ops_index_logos_math_pins",
        "cursor_session_upgrade_oracle",
        "lemma_spike_drift_compare",
        "router_regression_bundle_p21",
        "logos_theory_wiring_registry",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _check(name: str, ok: bool, *, path: str = "", detail: str = "") -> dict[str, Any]:
    return {"check_id": name, "pass": ok, "path": path, "detail": detail}


def _load_ops_index_with_oracle_logos_heal(root: Path) -> dict[str, Any]:
    """Heal stale index when bare rebuild dropped logos_math_v1 overlay nodes."""
    index_path = root / INDEX.relative_to(ROOT)
    index = _read_json(index_path)
    nodes = index.get("nodes") or {}
    ok = "logos_math_v1" in (index.get("overlays") or []) and (
        "prism_ops_logos_cosmic_anchor_bridge" in nodes
    )
    if ok:
        return index
    try:
        from mkm_ops_memory_index_lib_v1 import ensure_lane_pack_index

        healed = ensure_lane_pack_index(root, index, "oracle")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            json.dumps(healed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            "OK: healed ops index logos_math overlay for tier1 readiness",
            file=sys.stderr,
        )
        return healed
    except (ImportError, KeyError, ValueError) as exc:
        print(f"WARN: logos index heal skipped: {exc}", file=sys.stderr)
        return index


def build_readiness(root: Path, *, skip_wiring_check: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    overlay = _read_json(root / OVERLAY_CHAIN.relative_to(ROOT))
    overlay_ok = overlay.get("chain_pass") is True and "logos_math_v1" in (overlay.get("overlays") or [])
    checks.append(
        _check(
            "logos_math_overlay_chain",
            overlay_ok,
            path=str(OVERLAY_CHAIN.relative_to(ROOT)),
            detail=f"overlays={overlay.get('overlays')}",
        )
    )

    index = _load_ops_index_with_oracle_logos_heal(root)
    nodes = index.get("nodes") or {}
    index_ok = "logos_math_v1" in (index.get("overlays") or []) and (
        "prism_ops_logos_cosmic_anchor_bridge" in nodes
    )
    checks.append(
        _check(
            "ops_index_logos_math_pins",
            index_ok,
            path=str(INDEX.relative_to(ROOT)),
            detail=f"logos_nodes={sum(1 for k in nodes if str(k).startswith('prism_ops_logos_'))}",
        )
    )

    upgrade = _read_json(root / UPGRADE.relative_to(ROOT))
    upgrade_ok = upgrade.get("ok") is True and upgrade.get("lane") == "oracle"
    checks.append(
        _check(
            "cursor_session_upgrade_oracle",
            upgrade_ok,
            path=str(UPGRADE.relative_to(ROOT)),
            detail=f"pins={upgrade.get('resume_pack_pins')}",
        )
    )

    drift = _read_json(root / DRIFT.relative_to(ROOT))
    drift_ok = drift.get("pass") is True and (drift.get("drift_flags") or []) == []
    checks.append(
        _check(
            "lemma_spike_drift_compare",
            drift_ok,
            path=str(DRIFT.relative_to(ROOT)),
            detail=f"drift_flags={drift.get('drift_flags')}",
        )
    )

    p21 = _read_json(root / P21.relative_to(ROOT))
    p21_ok = p21.get("chain_pass") is True and p21.get("send_gate") == "HOLD"
    checks.append(
        _check(
            "router_regression_bundle_p21",
            p21_ok,
            path=str(P21.relative_to(ROOT)),
            detail=f"bloom_cap={p21.get('bloom_cap')}",
        )
    )

    proc = subprocess.run(
        [sys.executable, "scripts/check_logos_theory_implementation_wiring_v1.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    wiring_ok = proc.returncode == 0
    if skip_wiring_check:
        checks.append(
            _check(
                "logos_theory_wiring_registry",
                True,
                path=str(WIRING.relative_to(ROOT)),
                detail="deferred until readiness artifact written",
            )
        )
    else:
        checks.append(
            _check(
                "logos_theory_wiring_registry",
                wiring_ok,
                path=str(WIRING.relative_to(ROOT)),
                detail=proc.stdout.strip()[:120] if wiring_ok else proc.stderr.strip()[:200],
            )
        )

    tier1_ready = all(c["pass"] for c in checks)

    hd = _read_json(root / HD_MISSION.relative_to(ROOT))
    baseline = hd.get("baseline_facts") or {}
    hd_cap = baseline.get("resonance_cap")
    p21_cap = (p21.get("bloom_cap") or {}).get("artifact")
    pin_aligned = (
        hd_cap is not None
        and p21_cap is not None
        and int(hd_cap) == int(p21_cap)
        and p21.get("chain_pass") is True
    )
    checks.append(
        _check(
            "hd_mission_pin_snapshot",
            bool(hd.get("version")) and hd_cap is not None,
            path=str(HD_MISSION.relative_to(ROOT)),
            detail=f"version={hd.get('version')} resonance_cap={hd_cap}",
        )
    )
    checks.append(
        _check(
            "resonance_cap_cross_ssot",
            pin_aligned,
            path=str(P21.relative_to(ROOT)),
            detail=f"p21_artifact={p21_cap} hd_mission={hd_cap}",
        )
    )

    closure = _read_json(root / VOC_CLOSURE.relative_to(ROOT))
    voc_ok = closure.get("ok") is True and closure.get("send_gate") == "HOLD"
    checks.append(
        _check(
            "han_vocology_pilot_closure",
            voc_ok,
            path=str(VOC_CLOSURE.relative_to(ROOT)),
            detail=f"cohorts={closure.get('cohort_count')} rows={closure.get('row_count')}",
        )
    )

    tier2_prep_ready = tier1_ready and pin_aligned and voc_ok

    tier2_unlock_ready = False
    tier2_protocol_pointer = TIER2_PROTOCOL_REL
    tier3_unlock_ready = False
    tier3_protocol_pointer = (
        "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
    )
    send_gate = "HOLD"
    full_upgrade_blockers = [
        "send_gate: HOLD — human release required for external narrative",
        "promotion_cascade_forbidden — Logos structural gates ≠ Track A",
        "tier2_full_rules_upgrade blocked until send_gate OPEN + pin schema freeze sign-off",
        "CONSTITUTION full rewrite requires D1 commander intent + PUBLIC_FACING audit",
    ]
    try:
        from logos_oracle_tier2_incremental_append_lib_v1 import evaluate_blocker_gates

        gate_eval = evaluate_blocker_gates(root=root)
        tier2_unlock_ready = bool(gate_eval.get("tier2_cursor_rules_full_upgrade_ready"))
        send_gate = str(gate_eval.get("send_gate") or "HOLD").upper()
        if tier2_unlock_ready:
            full_upgrade_blockers = [
                "promotion_cascade_forbidden — Logos structural gates ≠ Track A (permanent wall)",
                "Track A·live trading auto-merge forbidden (permanent wall)",
                "tier3_constitution_narrative_full_upgrade blocked — separate commander + legal review",
                "canonical merge / cap bump / offline_4d bulk inject still forbidden",
            ]
        from logos_oracle_tier3_narrative_upgrade_lib_v1 import evaluate_tier3_gates

        tier3_eval = evaluate_tier3_gates(root=root)
        tier3_unlock_ready = bool(tier3_eval.get("tier3_constitution_narrative_full_upgrade_ready"))
        if tier3_unlock_ready:
            full_upgrade_blockers = [
                "promotion_cascade_forbidden — Logos structural gates ≠ Track A (permanent wall)",
                "Track A·live trading auto-merge forbidden (permanent wall)",
                "canonical merge / cap bump / offline_4d bulk inject still forbidden",
                "CONSTITUTION full body rewrite still forbidden — narrative append slices only",
            ]
    except ImportError:
        tier2_protocol_pointer = TIER2_PROTOCOL_REL + " (lib import pending)"

    return {
        "schema": "logos_oracle_cursor_inject_tier1_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": send_gate,
        "hypothesis_class": "HYPO",
        "tier1_module_ssot_ready": tier1_ready,
        "tier2_pin_schema_snapshot": {
            "hd_mission_version": hd.get("version"),
            "hd_mission_path": str(HD_MISSION.relative_to(ROOT)).replace("\\", "/"),
            "resonance_cap": hd_cap,
            "p21_bloom_cap_artifact": p21_cap,
            "router_hit_rate": baseline.get("router_hit_rate"),
            "gold_required_all_pass": baseline.get("gold_required_all_pass"),
            "narrative_samples_current": baseline.get("narrative_samples_current"),
            "lemma_hit_anchors_current": baseline.get("lemma_hit_anchors_current"),
            "pytest_oracle_lane_last": baseline.get("pytest_oracle_lane_last"),
            "read_only": True,
        },
        "tier2_pin_schema_aligned": pin_aligned,
        "tier2_prep_ready": tier2_prep_ready,
        "tier2_cursor_rules_full_upgrade_ready": tier2_unlock_ready,
        "tier3_constitution_narrative_full_upgrade_ready": tier3_unlock_ready,
        "tier2_incremental_append_protocol": tier2_protocol_pointer,
        "tier3_narrative_upgrade_protocol": tier3_protocol_pointer,
        "full_upgrade_blockers": full_upgrade_blockers,
        "checks": checks,
        "checks_pass_count": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "constitution_pointer": CONSTITUTION_POINTER,
        "repro_one_shot": "py scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
        "boundary_ack": (
            "Tier-1 = Oracle Logos Cursor coordinate inject module SSOT only. "
            "NOT prophecy accuracy, NOT Track A, NOT 「성경 AI 진화 완료」."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    doc = build_readiness(root, skip_wiring_check=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "scripts/check_logos_theory_implementation_wiring_v1.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    wiring_ok = proc.returncode == 0
    for row in doc["checks"]:
        if row["check_id"] == "logos_theory_wiring_registry":
            row["pass"] = wiring_ok
            row["detail"] = (
                proc.stdout.strip()[:120]
                if wiring_ok
                else (proc.stderr.strip() or proc.stdout.strip())[:200]
            )
    doc["tier1_module_ssot_ready"] = all(
        c["pass"] for c in doc["checks"] if c["check_id"] in TIER1_CHECK_IDS
    )
    doc["tier2_prep_ready"] = doc["tier1_module_ssot_ready"] and doc.get("tier2_pin_schema_aligned") and any(
        c["pass"] for c in doc["checks"] if c["check_id"] == "han_vocology_pilot_closure"
    )
    try:
        from logos_oracle_tier2_incremental_append_lib_v1 import evaluate_blocker_gates
        from logos_oracle_tier3_narrative_upgrade_lib_v1 import evaluate_tier3_gates

        gate_eval = evaluate_blocker_gates(root=root)
        tier3_eval = evaluate_tier3_gates(root=root)
        doc["tier2_cursor_rules_full_upgrade_ready"] = bool(
            gate_eval.get("tier2_cursor_rules_full_upgrade_ready")
        )
        doc["tier3_constitution_narrative_full_upgrade_ready"] = bool(
            tier3_eval.get("tier3_constitution_narrative_full_upgrade_ready")
        )
        doc["send_gate"] = str(gate_eval.get("send_gate") or doc.get("send_gate") or "HOLD").upper()
    except ImportError:
        pass
    doc["checks_pass_count"] = sum(1 for c in doc["checks"] if c["pass"])
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"tier1_module_ssot_ready={doc['tier1_module_ssot_ready']} "
        f"tier2_prep_ready={doc.get('tier2_prep_ready')} "
        f"checks={doc['checks_pass_count']}/{doc['checks_total']}"
    )
    return 0 if doc["tier1_module_ssot_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
