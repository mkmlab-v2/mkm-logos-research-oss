#!/usr/bin/env python3
"""[HYPO] Coordinator science kernel v2 — bounded 4-knob loss sweep (spine byte_exact guard)."""
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

from scripts.nextgen_coordinator_science_loss_v1 import (
    compute_coordinator_loss,
    lens_disagreement_proxy,
    load_disagreement_probe_defaults,
    partition_lens_terms,
    salience_boost_weights,
)
from scripts.nextgen_latent_codec_v1 import jaccard_text
from scripts.nextgen_science_prior_terms_v1 import (
    DEFAULT_SPEC,
    load_science_prior_terms,
    load_trilane_prior_terms,
)
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)
from scripts.run_nextgen_hybrid_spine_trilane_stack_v1 import _salience_reconstruct_trilane

SPEC_DEFAULT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/COORDINATOR_SCIENCE_KERNEL_V2.json"
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
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_science_loss_sweep_v1_latest.json"
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


def _eval_point(
    cases: list[dict[str, Any]],
    *,
    keep_ratio: float,
    science_weight_scale: float,
    w_s: float,
    w_j: float,
    all_terms: frozenset[str],
    science_terms: frozenset[str],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    logos_t, sci_t, sas_t, mye_t = partition_lens_terms(all_terms, science_terms)
    spec_doc = json.loads(
        (ROOT / "experiments/nextgen_clean_slate_cpu_v1/SCIENCE_PRIOR_SIDECAR_SPEC_V1.json").read_text(
            encoding="utf-8-sig"
        )
    )
    w_logos, w_sci, w_sas, w_mye = salience_boost_weights(spec_doc)
    w_sci *= science_weight_scale
    dis_probe = load_disagreement_probe_defaults(
        ROOT / "experiments/nextgen_clean_slate_cpu_v1/COORDINATOR_SCIENCE_KERNEL_V2.json"
    )
    dis_kr = float(dis_probe.get("keep_ratio_cap", 0.55))

    total_raw = total_spine = total_side = 0
    exact = 0
    j_spine = j_side = 0.0
    disagree_sum = 0.0

    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        ok = raw == recon
        exact += int(ok)
        sem, _ = _salience_reconstruct_trilane(
            raw, keep_ratio, logos_t, sci_t, sas_t, w_logos, w_sci, w_sas, mye_t, w_mye
        )
        rb = len(raw.encode("utf-8"))
        sb_b = spine_packet_json_bytes(pkt)
        sc = len(sem.encode("utf-8"))
        total_raw += rb
        total_spine += sb_b
        total_side += sc
        j_spine += jaccard_text(raw, recon)
        j_side += jaccard_text(raw, sem)
        disagree_sum += lens_disagreement_proxy(
            raw,
            keep_ratio=keep_ratio,
            logos_terms=logos_t,
            science_terms=sci_t,
            sasang_terms=sas_t,
            science_weight_scale=science_weight_scale,
            myeongni_terms=mye_t,
            myeongni_weight=w_mye,
            disagreement_keep_ratio=dis_kr,
        )

    n = max(1, len(cases))
    parity = exact / len(cases) if cases else 0.0
    saving_side = 1.0 - ((total_spine + total_side) / max(1, total_raw))
    j_side_avg = j_side / n
    disagree_avg = disagree_sum / n
    byte_violation = 0.0 if parity >= 1.0 else 1.0

    loss = compute_coordinator_loss(
        saving=saving_side,
        jaccard=j_side_avg,
        byte_exact_violation=byte_violation,
        disagreement=disagree_avg,
        w_s=w_s,
        w_j=w_j,
        lambda_disagreement=float(defaults.get("lambda_disagreement", 0.5)),
        mu_byte_exact=float(defaults.get("mu_byte_exact", 1000.0)),
        j_target=float(defaults.get("j_target", 0.89)),
    )

    fr = _frozen()
    frozen_s = fr.get("global_token_saving_rate") if fr.get("present") else None
    frozen_j = fr.get("avg_reconstruction_fidelity_jaccard") if fr.get("present") else None
    beat_s = frozen_s is not None and saving_side >= float(frozen_s)
    beat_j = frozen_j is not None and j_side_avg >= float(frozen_j)
    return {
        "keep_ratio": keep_ratio,
        "science_weight_scale": science_weight_scale,
        "w_s": w_s,
        "w_j": w_j,
        "byte_exact_subset_parity": round(parity, 6),
        "payload_global_token_saving_rate": round(saving_side, 6),
        "avg_sidecar_jaccard": round(j_side_avg, 6),
        "avg_lens_disagreement": round(disagree_avg, 6),
        "coordinator_loss": round(loss, 6),
        "beat_frozen_saving": beat_s,
        "beat_frozen_jaccard": beat_j,
        "dual_axis_beat": beat_s and beat_j and parity >= 1.0,
        "frozen_reference": fr,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec-json", type=Path, default=SPEC_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    if not args.spec_json.is_file() or not BENCH.is_file():
        print(json.dumps({"error": "missing_spec_or_bench"}))
        return 2

    spec = json.loads(args.spec_json.read_text(encoding="utf-8-sig"))
    grid_key = "sweep_grid_smoke" if args.smoke else "sweep_grid_default"
    grid = spec.get(grid_key) or {}
    defaults = (spec.get("loss_function_v1") or {}).get("defaults") or {}

    all_terms, prior_meta = load_trilane_prior_terms(
        root=ROOT,
        spec_path=ROOT / DEFAULT_SPEC,
        salience_hook_path=SALIENCE_HOOK,
        nav_frame_path=NAV_FRAME,
        logos_pack_path=None,
        merge_archetype=True,
    )
    science_terms, _ = load_science_prior_terms(root=ROOT)
    cases = json.loads(BENCH.read_text(encoding="utf-8-sig")).get("compression_cases") or []

    rows: list[dict[str, Any]] = []
    for kr in grid.get("keep_ratio") or [0.82]:
        for sw in grid.get("science_weight_scale") or [1.0]:
            for wj in grid.get("w_j") or [2.0]:
                for ws in grid.get("w_s") or [1.0]:
                    rows.append(
                        _eval_point(
                            cases,
                            keep_ratio=float(kr),
                            science_weight_scale=float(sw),
                            w_s=float(ws),
                            w_j=float(wj),
                            all_terms=all_terms,
                            science_terms=science_terms,
                            defaults=defaults,
                        )
                    )

    eligible = [r for r in rows if r["byte_exact_subset_parity"] >= 1.0]
    best_loss = min(eligible, key=lambda r: r["coordinator_loss"]) if eligible else None
    best_dual = next((r for r in eligible if r["dual_axis_beat"]), None)
    fr = _frozen()
    by_loss = sorted(eligible, key=lambda r: r["coordinator_loss"])[:5]
    by_j = sorted(eligible, key=lambda r: r["avg_sidecar_jaccard"], reverse=True)[:5]
    pareto_summary = {
        "frozen_active": fr,
        "best_dual_axis_beat": best_dual,
        "top5_by_coordinator_loss": by_loss,
        "top5_by_sidecar_jaccard": by_j,
        "measurement_axis_ko": (
            "payload_global_token_saving_rate = hybrid spine+trilane bytes vs raw; "
            "NOT Track A global_token_saving_rate from evaluate_report"
        ),
    }

    out = {
        "schema": "nextgen_coordinator_science_loss_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "coordinator_role": "Absolute Balance Coordinator Mode science kernel v2",
        "grid_key": grid_key,
        "row_count": len(rows),
        "eligible_spine_guard_rows": len(eligible),
        "prior_terms_meta": prior_meta,
        "best_by_loss": best_loss,
        "best_dual_axis_beat": best_dual,
        "pareto_summary": pareto_summary,
        "pareto_note_ko": "dual_axis_beat = byte_exact 1.0 + beat frozen saving and jaccard",
        "rows_sample": rows[:12],
        "stub_pointer": spec.get("measurement", {}).get("output_pointer"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "rows": len(rows),
                "best_dual_axis_beat": bool(best_dual),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
