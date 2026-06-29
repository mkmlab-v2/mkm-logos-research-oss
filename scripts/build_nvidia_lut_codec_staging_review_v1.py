#!/usr/bin/env python3
"""[HYPO] LUT→codec staging review pack — bench lanes + anchor signoff, no ACTIVE wire."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = ROOT / "reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json"
WIRE_CONFIRM = ROOT / "reports/nvidia_lut_codec_staging_wire_confirm_v1_latest.json"
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
CODEC_MANIFEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json"
)
PATH_A = ROOT / "reports/ng40_path_a_product_signoff_chain_v1_latest.json"
DUAL_AXIS = ROOT / "reports/ng40_path_b_dual_axis_push_v1_latest.json"
TRILANE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
)
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "reports/nvidia_lut_codec_staging_review_v1_latest.json"
OUT_TXT = ROOT / "reports/nvidia_lut_codec_staging_review_paste_v1_latest.txt"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(p: Path) -> dict[str, Any] | None:
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main() -> int:
    signoff = _load(SIGNOFF) or {}
    lut = _load(LUT) or {}
    codec = _load(CODEC_MANIFEST) or {}
    path_a = _load(PATH_A) or {}
    dual = _load(DUAL_AXIS) or {}
    trilane = _load(TRILANE) or {}
    active = _load(ACTIVE) or {}
    wire = _load(WIRE_CONFIRM) or {}
    cm = active.get("compression_metrics") or {}

    lanes = codec.get("lanes") or {}
    latent = lanes.get("latent_golden40_dual_axis") or {}
    spine = lanes.get("spine_byte_exact_b2b") or {}
    hybrid = lanes.get("hybrid_sidecar_preview") or {}

    any_beat = bool(
        dual.get("any_beat_frozen_vs_active")
        or latent.get("path_b_sweep_any_beat")
        or (trilane.get("beat_check") or {}).get("beat_frozen")
    )
    gates = path_a.get("product_gates") or {}
    product_ready = bool(
        path_a.get("product_ready")
        or gates.get("product_ready")
    )
    byte_ok = (
        spine.get("guarded_byte_exact") == 1.0
        or spine.get("guarded_byte_exact") is True
        or gates.get("byte_exact_subset_parity") == 1.0
        or hybrid.get("byte_exact_parity") == 1.0
    )
    contract_ok = (
        spine.get("guarded_contract_met") is True
        or gates.get("guarded_contract_met") is True
    )

    codec_wired = bool(
        wire.get("codec_wired_staging")
        and str(wire.get("decision") or "") == "confirm_product_lane_staging_wire"
    )
    human_next = (
        "staging_product_lane_wired_review_only"
        if codec_wired
        else "confirm_lut_to_codec_staging_wire_or_hold"
    )

    doc = {
        "schema": "nvidia_lut_codec_staging_review_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "codec_wired": codec_wired,
        "codec_wire_confirm": {
            "decision": wire.get("decision"),
            "generated_at_utc": wire.get("generated_at_utc"),
            "recommended_lane": wire.get("recommended_lane"),
        },
        "track_a_active_write": False,
        "anchor_signoff": {
            "accepted": signoff.get("accepted_probe_ids") or [],
            "rejected": signoff.get("rejected_probe_ids") or [],
        },
        "lut_status": lut.get("status"),
        "frozen_active_reference": {
            "saving": cm.get("global_token_saving_rate"),
            "jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        },
        "bench_lanes": {
            "latent_dual_axis_beat_frozen": any_beat,
            "trilane_saving": (trilane.get("aggregate") or {}).get("global_token_saving_rate"),
            "trilane_jaccard": (trilane.get("aggregate") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "spine_byte_exact": spine.get("guarded_byte_exact"),
            "guarded_contract_met": contract_ok,
            "hybrid_keep_ratio": hybrid.get("keep_ratio"),
            "hybrid_byte_exact": hybrid.get("byte_exact_parity"),
        },
        "staging_verdict": {
            "product_lane_ready": product_ready and byte_ok and contract_ok,
            "latent_active_replacement_ready": any_beat,
            "recommended_primary_lane": (
                "hybrid_sidecar_preview"
                if product_ready and byte_ok and contract_ok
                else "research_only_hold"
            ),
        },
        "human_next": human_next,
        "forbidden": ["--apply-active", "auto_merge_into_active_codec"],
        "pointers": {
            "codec_manifest": str(CODEC_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "path_a_signoff": str(PATH_A.relative_to(ROOT)).replace("\\", "/"),
            "signoff": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# LUT→코덱 스테이징 검토 [HYPO]",
        f"**갱신:** {doc['generated_at_utc']}",
        "",
        f"- 앵커: accept **{len(doc['anchor_signoff']['accepted'])}** · reject **{len(doc['anchor_signoff']['rejected'])}**",
        f"- Product lane (hybrid+guarded): **{'GO' if doc['staging_verdict']['product_lane_ready'] else 'HOLD'}**",
        f"- Latent ACTIVE 교체: **{'가능(beat)' if any_beat else '불가(beat 없음)'}**",
        f"- 권장 본선 레인: `{doc['staging_verdict']['recommended_primary_lane']}`",
        f"- 코덱 배선: **{'staging 완료(product lane)' if codec_wired else '미실행'}** "
        f"({'hybrid_sidecar_preview' if codec_wired else '지휘관 confirm_lut_to_codec_staging_wire 후'})",
        "",
        "JSON: reports/nvidia_lut_codec_staging_review_v1_latest.json",
    ]
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "product_lane_ready": doc["staging_verdict"]["product_lane_ready"],
                "any_beat": any_beat,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
