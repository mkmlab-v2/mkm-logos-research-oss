#!/usr/bin/env python3
"""DeepNSM HF 1B vs gematria shadow — research-only A/B stub manifest [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json"
DISTORTION_CHAIN = ROOT / "reports/deepnsm_shadow_distortion_chain_v1_latest.json"
HF_CHAIN = ROOT / "reports/deepnsm_hf_explication_chain_v1_latest.json"
HF_OLLAMA_CHAIN = ROOT / "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
HF_OLLAMA_500 = ROOT / "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json"
NSM_SHADOW = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
NSM_RAW = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"
EXPLICATION = ROOT / "reports/deepnsm_shadow_explication_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_stub() -> dict[str, Any]:
    distortion = _read(DISTORTION_CHAIN)
    shadow_audit = _read(NSM_SHADOW)
    raw_audit = _read(NSM_RAW)
    expl = _read(EXPLICATION)
    shadow_base = (shadow_audit.get("baseline") or {})
    raw_base = (raw_audit.get("baseline") or {})
    hf_ollama_500 = _read(HF_OLLAMA_500)
    hf_ollama = _read(HF_OLLAMA_CHAIN)
    if (
        hf_ollama_500.get("implementation_status") == "ollama_local_weights_v1"
        and int(hf_ollama_500.get("pair_count") or 0) >= 500
    ):
        hf_chain = hf_ollama_500
    elif hf_ollama.get("implementation_status") == "ollama_local_weights_v1":
        hf_chain = hf_ollama
    else:
        hf_chain = _read(HF_CHAIN)
    hf_audit = hf_chain.get("hf_ollama_audit") or hf_chain.get("hf_stub_audit") or {}
    impl = hf_chain.get("implementation_status") or "offline_gloss_stub_v1"
    is_ollama = impl == "ollama_local_weights_v1"
    sidecar = (
        "docs/final/artifacts/deepnsm_hf_explication_ollama_500_v1.jsonl"
        if is_ollama and int(hf_chain.get("pair_count") or 0) >= 500
        else (
            "docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl"
            if is_ollama
            else "docs/final/artifacts/deepnsm_hf_explication_stub_v1.jsonl"
        )
    )
    chain_report = (
        "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json"
        if is_ollama and int(hf_chain.get("pair_count") or 0) >= 500
        else (
            "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
            if is_ollama
            else "reports/deepnsm_hf_explication_chain_v1_latest.json"
        )
    )
    note = (
        "Ollama local weights gloss-assist + gematria index — not arXiv DeepNSM HF 1B checkpoint"
        if is_ollama
        else "Offline gloss-overlap stub — not HF 1B weight inference"
    )
    ab_status_label = (
        "paired_ollama_500"
        if is_ollama and int(hf_chain.get("pair_count") or 0) >= 500
        else ("paired_ollama_pilot" if is_ollama else "paired_offline_stub")
    )
    gematria_arm = {
        "arm_id": "gematria_translit_index",
        "implementation_status": "implemented",
        "sidecar": "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl",
        "explication_summary": expl.get("summary") or {},
        "distortion_metrics": {
            "prime_hit_rate": shadow_base.get("prime_hit_rate"),
            "english_only_distortion_rate": shadow_base.get("english_only_distortion_rate"),
            "gate_ok": (shadow_audit.get("gates") or {}).get("gate_ok"),
        },
    }
    hf_arm = {
        "arm_id": "deepnsm_hf_1b",
        "implementation_status": impl,
        "model_reference": "arXiv:2505.11764 (Towards Universal Semantics With LLMs)",
        "ollama_model": (hf_chain.get("ollama_meta") or {}).get("ollama_model") if is_ollama else None,
        "sidecar": sidecar,
        "chain_report": chain_report,
        "distortion_metrics": hf_audit if hf_audit else None,
        "note": note,
    }
    comparison_ready = bool(hf_audit and gematria_arm.get("distortion_metrics"))
    delta = hf_chain.get("delta_hf_ollama_minus_gematria") or hf_chain.get("delta_hf_stub_minus_gematria") or {}
    return {
        "schema": "deepnsm_hf_ab_research_stub_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track_a_promotion_forbidden": True,
        "ab_status": ab_status_label if comparison_ready else "stub_only",
        "comparison_ready": comparison_ready,
        "fixture": "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
        "raw_latin_baseline": {
            "prime_hit_rate": raw_base.get("prime_hit_rate"),
            "english_only_distortion_rate": raw_base.get("english_only_distortion_rate"),
            "gate_ok": (raw_audit.get("gates") or {}).get("gate_ok"),
        },
        "arms": {
            "gematria_shadow": gematria_arm,
            "deepnsm_hf_1b": hf_arm,
        },
        "delta_hf_minus_gematria": delta if delta else {
            "status": "not_computed",
            "reason": "HF chain not run",
        },
        "next_work": [
            "Scale Ollama pilot to full 500-pair fixture when GPU/time budget allows",
            "Optional: swap Ollama model for upstream DeepNSM HF 1B checkpoint when hosted",
            "Report raw vs shadow dual metrics per raw-repair-dual-reporting-v1",
        ] if is_ollama else [
            "Replace gloss stub with Ollama/HF DeepNSM 1B inference path when GPU lane ready",
            "Re-run paired 500-pair audit on same fixture with both arms",
            "Report raw vs shadow dual metrics per raw-repair-dual-reporting-v1",
        ],
        "pointers": {
            "distortion_chain_latest": "reports/deepnsm_shadow_distortion_chain_v1_latest.json",
            "hf_explication_chain_latest": "reports/deepnsm_hf_explication_chain_v1_latest.json",
            "gematria_sidecar": "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl",
            "hf_stub_sidecar": "docs/final/artifacts/deepnsm_hf_explication_stub_v1.jsonl",
        },
        "reproduce": "py scripts/build_deepnsm_hf_ab_research_stub_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_stub()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool((doc.get("arms") or {}).get("gematria_shadow", {}).get("distortion_metrics"))
    print(json.dumps({"ok": ok, "out": str(args.out), "ab_status": doc.get("ab_status")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
