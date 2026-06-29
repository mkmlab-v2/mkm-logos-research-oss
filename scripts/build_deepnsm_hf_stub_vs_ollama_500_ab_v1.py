#!/usr/bin/env python3
"""500-pair gloss-stub vs Ollama local-weights A/B compare [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/deepnsm_hf_stub_vs_ollama_500_ab_v1_latest.json"
STUB_CHAIN = ROOT / "reports/deepnsm_hf_explication_chain_v1_latest.json"
OLLAMA_500 = ROOT / "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json"
GEMATRIA_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metrics(chain: dict[str, Any]) -> dict[str, Any]:
    return chain.get("hf_ollama_audit") or chain.get("hf_stub_audit") or {}


def _delta(a: dict[str, Any], b: dict[str, Any], prefix: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in ("prime_hit_rate", "english_only_distortion_rate"):
        av = a.get(key)
        bv = b.get(key)
        if av is not None and bv is not None:
            out[f"{key}_{prefix}"] = round(float(av) - float(bv), 4)
    return out


def build_ab() -> dict[str, Any]:
    stub = _read(STUB_CHAIN)
    ollama = _read(OLLAMA_500)
    gematria = _read(GEMATRIA_AUDIT)
    gem_base = (gematria.get("baseline") or {})

    stub_m = _metrics(stub)
    ollama_m = _metrics(ollama)
    ready = (
        stub.get("implementation_status") == "offline_gloss_stub_v1"
        and ollama.get("implementation_status") == "ollama_local_weights_v1"
        and int(stub.get("pair_count") or 0) >= 500
        and int(ollama.get("pair_count") or 0) >= 500
        and bool(stub_m)
        and bool(ollama_m)
    )

    return {
        "schema": "deepnsm_hf_stub_vs_ollama_500_ab_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track_a_promotion_forbidden": True,
        "fixture": "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
        "comparison_ready": ready,
        "arms": {
            "gloss_stub": {
                "implementation_status": stub.get("implementation_status"),
                "pair_count": stub.get("pair_count"),
                "metrics": stub_m,
                "chain_report": "reports/deepnsm_hf_explication_chain_v1_latest.json",
            },
            "ollama_local_weights": {
                "implementation_status": ollama.get("implementation_status"),
                "pair_count": ollama.get("pair_count"),
                "ollama_model": (ollama.get("ollama_meta") or {}).get("ollama_model"),
                "metrics": ollama_m,
                "chain_report": "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json",
            },
            "gematria_shadow_reference": {
                "metrics": {
                    "prime_hit_rate": gem_base.get("prime_hit_rate"),
                    "english_only_distortion_rate": gem_base.get("english_only_distortion_rate"),
                    "gate_ok": (gematria.get("gates") or {}).get("gate_ok"),
                },
            },
        },
        "delta_ollama_minus_stub": _delta(ollama_m, stub_m, "ollama_minus_stub") if ready else {},
        "delta_ollama_minus_gematria": ollama.get("delta_hf_ollama_minus_gematria") or {},
        "delta_stub_minus_gematria": stub.get("delta_hf_stub_minus_gematria") or {},
        "reproduce": "py scripts/build_deepnsm_hf_stub_vs_ollama_500_ab_v1.py",
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
