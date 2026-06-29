#!/usr/bin/env python3
"""[HYPO] Pareto sweep: spine byte_exact + payload saving vs frozen ACTIVE (DESIGN_SWEEP)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_archetype_prior_terms_v1 import load_prior_terms
from scripts.nextgen_latent_codec_v1 import jaccard_text
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_binary_bytes,
    spine_packet_body_bytes,
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)
from scripts.run_nextgen_hybrid_spine_logos_stack_v1 import _salience_reconstruct_logos

SPEC_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_COMMERCIALIZATION_PARETO_SWEEP_SPEC_V1.json"
)
BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_commercialization_pareto_sweep_v1_latest.json"
)
DIET_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_prior_residual_diet_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": float(cm.get("global_token_saving_rate", 0)),
        "avg_reconstruction_fidelity_jaccard": float(
            cm.get("avg_reconstruction_fidelity_jaccard", 0)
        ),
    }


def _cap_sidecar_bytes(sem: str, cap: int | None) -> tuple[str, int]:
    if cap is None or cap <= 0:
        b = sem.encode("utf-8")
        return sem, len(b)
    enc = sem.encode("utf-8")
    if len(enc) <= cap:
        return sem, len(enc)
    return enc[:cap].decode("utf-8", errors="ignore"), cap


def _eval_grid_point(
    cases: list[dict[str, Any]],
    *,
    keep_ratio: float,
    residual_cap_ratio: float | None,
    prior_terms: frozenset[str],
    prior_boost: float,
) -> dict[str, Any]:
    total_raw = total_json_side = total_json_only = total_body = total_binary = 0
    exact = 0
    j_recon = j_side = 0.0
    boosted_terms = prior_terms
    if prior_boost != 1.0:
        boosted_terms = frozenset(
            {t for t in prior_terms} | {f"{t}_boost" for t in list(prior_terms)[:8]}
        )

    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        ok = raw == recon
        exact += int(ok)
        sem, _ = _salience_reconstruct_logos(raw, keep_ratio, boosted_terms)
        cap_b = None
        if residual_cap_ratio is not None:
            cap_b = max(1, int(len(raw.encode("utf-8")) * residual_cap_ratio))
        sem_capped, side_b = _cap_sidecar_bytes(sem, cap_b)
        spine_json_b = spine_packet_json_bytes(pkt)
        spine_body_b = spine_packet_body_bytes(pkt)
        spine_bin_b = spine_packet_binary_bytes(pkt)
        rb = len(raw.encode("utf-8"))
        total_raw += rb
        total_json_side += spine_json_b + side_b
        total_json_only += spine_json_b
        total_body += spine_body_b
        total_binary += spine_bin_b
        j_recon += jaccard_text(raw, recon)
        j_side += jaccard_text(raw, sem_capped)

    n = max(1, len(cases))
    byte_parity = exact / len(cases) if cases else 0.0
    fr = _frozen()
    frozen_s = float(fr["global_token_saving_rate"]) if fr.get("present") else None

    def _saving(stored: int) -> float:
        return round(1.0 - (stored / max(1, total_raw)), 6)

    modes = {
        "spine_json_plus_capped_sidecar": _saving(total_json_side),
        "spine_json_only_zero_sidecar_bill": _saving(total_json_only),
        "spine_binary_billable_mkvs": _saving(total_binary),
        "spine_body_only_reference": _saving(total_body),
    }

    billing: dict[str, Any] = {}
    for mode, saving in modes.items():
        beat = frozen_s is not None and saving >= frozen_s
        billing[mode] = {
            "global_token_saving_rate": saving,
            "beat_frozen_saving": beat,
            "dual_axis_beat": byte_parity >= 1.0 and beat,
        }

    legacy_saving = modes["spine_json_plus_capped_sidecar"]
    return {
        "keep_ratio": keep_ratio,
        "residual_cap_ratio_of_raw": residual_cap_ratio,
        "prior_boost": prior_boost,
        "case_count": len(cases),
        "byte_exact_count": exact,
        "byte_exact_subset_parity": round(byte_parity, 6),
        "payload_global_token_saving_rate": legacy_saving,
        "avg_b2b_recon_jaccard": round(j_recon / n, 6),
        "avg_sidecar_preview_jaccard": round(j_side / n, 6),
        "billing_modes": billing,
        "beat_frozen_saving": billing["spine_json_plus_capped_sidecar"]["beat_frozen_saving"],
        "dual_axis_beat": billing["spine_json_plus_capped_sidecar"]["dual_axis_beat"],
        "frozen_reference": fr,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec-json", type=Path, default=SPEC_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--smoke", action="store_true", help="Use sweep_grid_smoke from spec")
    ap.add_argument(
        "--diet-json",
        type=Path,
        default=None,
        help="After grid, add rows at Step1 recommended keep_ratio(s)",
    )
    args = ap.parse_args()
    if not args.spec_json.is_file() or not BENCH.is_file():
        print(json.dumps({"error": "missing_spec_or_bench"}))
        return 2

    spec = json.loads(args.spec_json.read_text(encoding="utf-8-sig"))
    grid_key = "sweep_grid_smoke" if args.smoke else "sweep_grid_default"
    grid = spec.get(grid_key) or spec.get("sweep_grid_default") or {}
    keep_ratios = grid.get("keep_ratio") or [0.82]
    cap_ratios = grid.get("residual_cap_ratio_of_raw") or [None]
    boosts = grid.get("prior_boost") or [1.0]

    prior_terms, prior_meta = load_prior_terms(
        root=ROOT,
        salience_hook_path=SALIENCE_HOOK,
        nav_frame_path=NAV_FRAME,
        logos_pack_path=None,
        max_terms=128,
    )
    cases = json.loads(BENCH.read_text(encoding="utf-8-sig")).get("compression_cases") or []

    rows: list[dict[str, Any]] = []
    for kr in keep_ratios:
        for cap in cap_ratios:
            for pb in boosts:
                cap_val = None if cap is None else float(cap)
                rows.append(
                    _eval_grid_point(
                        cases,
                        keep_ratio=float(kr),
                        residual_cap_ratio=cap_val,
                        prior_terms=prior_terms,
                        prior_boost=float(pb),
                    )
                )

    diet_path = args.diet_json or (DIET_DEFAULT if DIET_DEFAULT.is_file() else None)
    diet_pointer = None
    if diet_path and diet_path.is_file():
        diet_doc = json.loads(diet_path.read_text(encoding="utf-8-sig"))
        diet_pointer = str(diet_path.relative_to(ROOT)).replace("\\", "/")
        rec = diet_doc.get("recommended_diet") or {}
        for key, cap_default in (
            ("sidecar_zero_bill", None),
            ("sidecar_billable", 0.15),
        ):
            d = rec.get(key)
            if not d:
                continue
            kr = float(d["keep_ratio"])
            rows.append(
                _eval_grid_point(
                    cases,
                    keep_ratio=kr,
                    residual_cap_ratio=cap_default,
                    prior_terms=prior_terms,
                    prior_boost=1.0,
                )
            )
            rows[-1]["diet_source"] = key

    dual_beat = [r for r in rows if r.get("dual_axis_beat")]
    dual_json_only = [
        r
        for r in rows
        if (r.get("billing_modes") or {})
        .get("spine_json_only_zero_sidecar_bill", {})
        .get("dual_axis_beat")
    ]
    dual_binary = [
        r
        for r in rows
        if (r.get("billing_modes") or {})
        .get("spine_binary_billable_mkvs", {})
        .get("dual_axis_beat")
    ]
    best = max(rows, key=lambda r: r.get("payload_global_token_saving_rate", -99)) if rows else None

    out = {
        "schema": "nextgen_commercialization_pareto_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "spec_pointer": str(args.spec_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "sla_contract": spec.get("step_0_sla_contract"),
        "grid_key": grid_key,
        "prior_residual_diet_pointer": diet_pointer,
        "prior_terms_count": len(prior_terms),
        "prior_terms_meta": prior_meta,
        "frozen_baseline": _frozen(),
        "sweep_rows": rows,
        "pareto_summary": {
            "grid_points": len(rows),
            "dual_axis_beat_count_legacy_json_plus_sidecar": len(dual_beat),
            "dual_axis_beat_count_spine_json_only": len(dual_json_only),
            "dual_axis_beat_count_spine_binary_mkvs": len(dual_binary),
            "dual_axis_beat_rows": dual_beat[:5],
            "dual_axis_beat_spine_json_only_rows": dual_json_only[:5],
            "dual_axis_beat_spine_binary_rows": dual_binary[:5],
            "best_payload_saving_row": best,
            "export_prep_ready_estimate": len(dual_binary) > 0,
            "note_ko": "Step2b MKVS binary billable; promotion packet ng40_spine_binary_billable_v1 arm",
        },
        "guardrails": [
            "Official recon = spine only; sidecar not in byte_exact gate",
            "Does not write ACTIVE",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "grid_points": len(rows),
                "dual_axis_beat_count": len(dual_beat),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
