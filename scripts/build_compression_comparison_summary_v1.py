#!/usr/bin/env python3
"""Aggregate compression lane headlines into comparison_summary_latest.json.

research_only pointers — does not replace Track A ACTIVE report or pilot proxies.
Genesis v3 multimap PoC fields are included only when source artifacts exist on disk.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/comparison_summary_latest.json"

PATHS = {
    "track_a_active": ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    "general_ab_summary": ROOT / "docs/final/artifacts/general_compression_ab_result_summary_v1.json",
    "general_kpi_gate": ROOT / "docs/final/artifacts/general_compression_kpi_gate_v2.json",
    "tracka_vs_zstd": ROOT / "docs/final/artifacts/tracka_vs_zstd_native_bench_latest.json",
    "hybrid_codec_research": ROOT / "docs/final/artifacts/hybrid_codec_v0_two_stage_gate_research_paper_latest.json",
    "genesis_pointer_guarded": ROOT / "docs/final/artifacts/genesis_pointer_routing_decision_guarded_latest.json",
    "evidence_pack_index": ROOT / "docs/final/artifacts/compression_public_evidence_pack_v0_index_latest.json",
    "rnd_master_index": ROOT / "docs/final/artifacts/compression_rnd_master_index_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _track_a_section(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    m = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "source": str(PATHS["track_a_active"]),
        "case_count": m.get("case_count"),
        "global_token_saving_rate": m.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        "sensitive_violation_count": m.get("sensitive_violation_count"),
        "integrity_guarantee_flag": (m.get("sensitive_violation_count") or 0) == 0,
    }


def _general_ab_section(summary: dict[str, Any] | None, gate: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"present": False}
    treatment = next((r for r in summary.get("runs") or [] if r.get("label") == "treatment"), None)
    baseline = next((r for r in summary.get("runs") or [] if r.get("label") == "baseline"), None)
    return {
        "present": True,
        "source_summary": str(PATHS["general_ab_summary"]),
        "source_gate": str(PATHS["general_kpi_gate"]) if gate else None,
        "gate_decision": (gate or {}).get("decision"),
        "baseline_global_token_saving_rate": (baseline or {}).get("global_token_saving_rate"),
        "treatment_global_token_saving_rate": (treatment or {}).get("global_token_saving_rate"),
        "treatment_avg_jaccard": (treatment or {}).get("avg_reconstruction_fidelity_jaccard"),
    }


def _backend_codec_section(bench: dict[str, Any] | None) -> dict[str, Any]:
    if not bench:
        return {"present": False}
    native = {row.get("name"): row for row in bench.get("native_codecs") or [] if row.get("name")}
    return {
        "present": True,
        "source": str(PATHS["tracka_vs_zstd"]),
        "payload_raw_bytes": bench.get("payload_raw_bytes"),
        "tracka_proxy_mean_saving_rate": (bench.get("tracka_proxy") or {}).get("mean_saving_rate"),
        "zstd_native_no_dict_ratio": (native.get("zstd_level3_no_dict") or {}).get("ratio"),
        "zstd_native_with_dict_ratio": (native.get("zstd_level3_with_trained_dict") or {}).get("ratio"),
        "zlib_level3_ratio": (native.get("zlib_level3") or {}).get("ratio"),
        "note": "Byte-level codec bench on synthetic 10MB payload; not token billing KPI.",
    }


def _hybrid_section(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    s2 = doc.get("stage2_holdout") or {}
    return {
        "present": True,
        "source": str(PATHS["hybrid_codec_research"]),
        "research_only": doc.get("research_only", True),
        "holdout_avg_saving_rate_chars": s2.get("avg_saving_rate_chars"),
        "exact_restore_rate": s2.get("exact_restore_rate"),
    }


def _genesis_routing_section(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    return {
        "present": True,
        "source": str(PATHS["genesis_pointer_guarded"]),
        "decision": doc.get("decision"),
        "route_mode": doc.get("route_mode"),
        "go_ratio": (doc.get("stats") or {}).get("go_ratio"),
        "note": "Control-plane routing; not compression ratio KPI.",
    }


def build_summary() -> dict[str, Any]:
    track_a = _load(PATHS["track_a_active"])
    general_summary = _load(PATHS["general_ab_summary"])
    general_gate = _load(PATHS["general_kpi_gate"])
    zstd_bench = _load(PATHS["tracka_vs_zstd"])
    hybrid = _load(PATHS["hybrid_codec_research"])
    genesis = _load(PATHS["genesis_pointer_guarded"])
    evidence = _load(PATHS["evidence_pack_index"])

    missing = [k for k, p in PATHS.items() if k not in ("rnd_master_index",) and not p.is_file()]

    return {
        "schema": "comparison_summary_v1",
        "generated_at_utc": _utc(),
        "labels": ["research_only", "internal_ops"],
        "integrity_guarantee_flag": _track_a_section(track_a).get("integrity_guarantee_flag"),
        "premises": "Aggregated pointers from on-disk artifacts; genesis v3 multimap theology cross-map PoC not regenerated in this build.",
        "track_a_frozen": _track_a_section(track_a),
        "general_compression_ab": _general_ab_section(general_summary, general_gate),
        "backend_codec_bench": _backend_codec_section(zstd_bench),
        "hybrid_codec_v0_research": _hybrid_section(hybrid),
        "genesis_pointer_routing": _genesis_routing_section(genesis),
        "public_evidence_pack": {
            "present": evidence is not None,
            "source": str(PATHS["evidence_pack_index"]) if evidence else None,
        },
        "rnd_master_index": str(PATHS["rnd_master_index"]) if PATHS["rnd_master_index"].is_file() else None,
        "missing_source_keys": missing,
        "guardrail": "Do not merge sections into single headline KPI; Track A active remains MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_summary()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "missing": doc.get("missing_source_keys"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
