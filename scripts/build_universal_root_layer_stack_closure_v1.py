#!/usr/bin/env python3
"""Aggregate Universal Root Layer A/B/C + 6 metric planes into closure signoff [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json"
GATE_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
GATE_EVAL = ROOT / "reports/universal_root_gate_eval_v1_latest.json"
HF_AB = ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json"
PHASE11S = ROOT / "reports/logos_graphrag_phase11s_evidence_nl_sync_chain_v1_latest.json"
EVIDENCE = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_closure(*, strict: bool = True) -> dict[str, Any]:
    spec = _read(GATE_SPEC)
    gate_eval_doc = _read(GATE_EVAL)
    ev = gate_eval_doc.get("evaluation") or {}
    planes = ev.get("planes") or []
    enabled = [p for p in planes if p.get("enabled")]
    all_enabled_ok = bool(ev.get("all_enabled_planes_ok"))
    layers = spec.get("layers") if isinstance(spec.get("layers"), dict) else {}
    baseline = spec.get("baseline_observed") if isinstance(spec.get("baseline_observed"), dict) else {}
    hf_ab = _read(HF_AB)
    phase11s = _read(PHASE11S)
    evidence = _read(EVIDENCE)
    phase11_cov = (evidence.get("phase_coverage") or {}).get("phase_11_universal_root_layer_stack") or {}

    plane_checks = {
        str(p.get("plane")): {"enabled": p.get("enabled"), "ok": p.get("ok")}
        for p in planes
        if isinstance(p, dict) and p.get("plane")
    }
    layer_checks = {
        lid: (cfg.get("implementation_status") if isinstance(cfg, dict) else None)
        for lid, cfg in layers.items()
    }
    required_planes = {"distortion", "retrieve", "route", "cost", "compress", "layer_c_mdl"}
    planes_present = {p.get("plane") for p in enabled}
    planes_complete = required_planes.issubset(planes_present)
    layers_ok = (
        layer_checks.get("layer_b") == "production_rail"
        and layer_checks.get("layer_c") in {"poc", "poc_complete"}
        and layer_checks.get("layer_a") in {"partial", "poc"}
    )
    hf_ok = bool(hf_ab.get("comparison_ready"))
    evidence_ok = bool(phase11_cov.get("gate_eval", {}).get("all_enabled_planes_ok") or all_enabled_ok)
    phase11s_ok = phase11s.get("all_ok") if phase11s else None

    checks = {
        "all_six_planes_enabled": planes_complete,
        "all_enabled_planes_ok": all_enabled_ok,
        "layers_status_ok": layers_ok,
        "deepnsm_hf_ab_paired": hf_ok,
        "evidence_pack_aligned": evidence_ok,
        "phase11s_chain_ok": phase11s_ok,
    }
    if strict:
        closure_ok = all(v is True for v in checks.values() if v is not None)
    else:
        closure_ok = all_enabled_ok and planes_complete

    return {
        "schema": "universal_root_layer_stack_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track_a_promotion_forbidden": True,
        "closure_ok": closure_ok,
        "gate_spec_phase_input": baseline.get("phase"),
        "research_ready_decision": ev.get("research_ready_decision"),
        "enabled_plane_count": len(enabled),
        "plane_checks": plane_checks,
        "layer_checks": layer_checks,
        "checks": checks,
        "compress_parity_saving_pct": (
            (baseline.get("compress_golden40") or {}).get("gate_metrics") or {}
        ).get("global_token_saving_rate"),
        "cost_cloud_skip_ratio": (baseline.get("route_stress_live_32") or {}).get("cloud_skip_ratio"),
        "deepnsm_hf_ab_status": hf_ab.get("ab_status"),
        "forbidden_promotion_note": (
            "closure_ok is B-track research stack only — not Track A promotion or live trading SEND"
        ),
        "reproduce": "py scripts/build_universal_root_layer_stack_closure_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--relaxed", action="store_true", help="Skip phase11s/evidence/hf pairing requirements")
    ap.add_argument("--enforce", action="store_true", help="Exit 1 when closure_ok is false")
    args = ap.parse_args()
    doc = build_closure(strict=not args.relaxed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool(doc.get("closure_ok"))
    print(json.dumps({"ok": ok, "out": str(args.out), "closure_ok": ok}, ensure_ascii=False))
    if args.enforce and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
