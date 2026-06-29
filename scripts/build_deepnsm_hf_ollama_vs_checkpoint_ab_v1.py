#!/usr/bin/env python3
"""DeepNSM HF Ollama vs upstream checkpoint A/B on same pilot fixture [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/deepnsm_hf_ollama_vs_checkpoint_ab_v1_latest.json"
OLLAMA_CHAIN = ROOT / "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
CHECKPOINT_CHAIN = ROOT / "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json"
NSM_SHADOW = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
NSM_RAW = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_ab() -> dict[str, Any]:
    ollama = _read(OLLAMA_CHAIN)
    checkpoint = _read(CHECKPOINT_CHAIN)
    shadow = _read(NSM_SHADOW)
    raw = _read(NSM_RAW)
    shadow_base = shadow.get("baseline") or {}
    raw_base = raw.get("baseline") or {}
    ollama_audit = ollama.get("hf_ollama_audit") or {}
    checkpoint_audit = checkpoint.get("hf_checkpoint_audit") or {}

    ollama_ok = (
        ollama.get("implementation_status") == "ollama_local_weights_v1"
        and bool(ollama.get("ok"))
        and int(ollama.get("pair_count") or 0) >= 1
    )
    checkpoint_ok = (
        checkpoint.get("implementation_status") == "deepnsm_hf_checkpoint_v1"
        and bool(checkpoint.get("ok"))
        and int(checkpoint.get("pair_count") or 0) >= 1
    )
    comparison_ready = bool(ollama_ok and checkpoint_ok and ollama_audit and checkpoint_audit)

    delta: dict[str, Any] = {}
    if comparison_ready:
        for key in ("prime_hit_rate", "english_only_distortion_rate"):
            ov = ollama_audit.get(key)
            cv = checkpoint_audit.get(key)
            if ov is not None and cv is not None:
                delta[f"{key}_checkpoint_minus_ollama"] = round(float(cv) - float(ov), 4)

    return {
        "schema": "deepnsm_hf_ollama_vs_checkpoint_ab_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track_a_promotion_forbidden": True,
        "comparison_ready": comparison_ready,
        "fixture": checkpoint.get("fixture") or ollama.get("fixture"),
        "raw_latin_baseline": {
            "prime_hit_rate": raw_base.get("prime_hit_rate"),
            "english_only_distortion_rate": raw_base.get("english_only_distortion_rate"),
            "gate_ok": (raw.get("gates") or {}).get("gate_ok"),
        },
        "arms": {
            "ollama_local_weights": {
                "implementation_status": ollama.get("implementation_status"),
                "pair_count": ollama.get("pair_count"),
                "ollama_model": (ollama.get("ollama_meta") or {}).get("ollama_model"),
                "metrics": ollama_audit,
                "chain_report": "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json",
                "sidecar": "docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl",
            },
            "deepnsm_hf_checkpoint": {
                "implementation_status": checkpoint.get("implementation_status"),
                "pair_count": checkpoint.get("pair_count"),
                "checkpoint_model": (checkpoint.get("checkpoint_meta") or {}).get("checkpoint_model"),
                "base_model": (checkpoint.get("checkpoint_meta") or {}).get("base_model"),
                "metrics": checkpoint_audit,
                "chain_report": "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json",
                "sidecar": "docs/final/artifacts/deepnsm_hf_explication_checkpoint_v1.jsonl",
            },
            "gematria_shadow_reference": {
                "metrics": {
                    "prime_hit_rate": shadow_base.get("prime_hit_rate"),
                    "english_only_distortion_rate": shadow_base.get("english_only_distortion_rate"),
                    "gate_ok": (shadow.get("gates") or {}).get("gate_ok"),
                }
            },
        },
        "delta_checkpoint_minus_ollama": delta if delta else None,
        "reproduce": "py scripts/build_deepnsm_hf_ollama_vs_checkpoint_ab_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_ab()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": bool(doc.get("comparison_ready")), "out": str(args.out)},
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("comparison_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
