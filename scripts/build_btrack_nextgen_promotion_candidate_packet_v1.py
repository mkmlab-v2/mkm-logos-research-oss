#!/usr/bin/env python3
"""[HYPO] Next-Gen promotion candidate packet (commander sign-off → apply gate).

Does not write ACTIVE unless apply script is run with --human-approve-promotion and gates pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
CHARTER = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
PARALLEL = ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"
NG40_STUB = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_stub_shadow_v1_latest.json"
)
NG40_EVAL = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_v1_latest.json"
)
NG40_BEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
)
NG40_HIGH_JACCARD = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_high_jaccard_v1_latest.json"
)
NG40_BEST_41K_ON = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_best_v1_latest.json"
)
NG40_BEST_41K_ON_FINEBEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_offbest_best_v1_latest.json"
)
NG40_BEST_41K_CAPS_PAIR = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_offbest_caps_pair_best_v1_latest.json"
)
NG40_MERGED_SHARDS = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_golden40_merged_v1_latest.json"
)
NG_BASELINE = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/nextgen_neural_baseline_v1_latest.json"
)
OUT = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
SIGNOFF_OUT = ROOT / "reports/btrack_nextgen_promotion_signoff_v1_latest.json"

MIN_SAVING = 0.45
MIN_JACCARD = 0.87
MAX_J_DROP_PP = 2.0


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _agg(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    if doc.get("aggregate"):
        return doc["aggregate"]
    if doc.get("compression_metrics"):
        cm = doc["compression_metrics"]
        return {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        }
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--human-approve-research",
        action="store_true",
        help="Commander approved research promotion packet (not ACTIVE apply)",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="Next-Gen NG-40 eval lane B-track sign-off")
    args = ap.parse_args()

    frozen_doc = _load(ACTIVE)
    if not frozen_doc:
        print("ABORT: missing ACTIVE", file=sys.stderr)
        return 1
    frozen_cm = frozen_doc.get("compression_metrics") or {}
    saving_f = float(frozen_cm.get("global_token_saving_rate") or 0)
    j_f = float(frozen_cm.get("avg_reconstruction_fidelity_jaccard") or 0)

    candidates: list[dict[str, Any]] = []
    eval_paths = sorted(
        p
        for p in (ROOT / "experiments/nextgen_clean_slate_cpu_v1/results").glob(
            "ng40_latent_eval*.json"
        )
        if not p.name.endswith(".report.json")
        and "cap_sweep" not in p.name
    )
    if not eval_paths and NG40_EVAL.is_file():
        eval_paths = [NG40_EVAL]
    arm_paths: list[tuple[str, Path]] = []
    if NG40_MERGED_SHARDS.is_file():
        arm_paths.append(("ng40_golden40_merged_shards_v1", NG40_MERGED_SHARDS))
    if NG40_BEST_41K_CAPS_PAIR.is_file():
        arm_paths.append(
            ("ng40_latent_eval_41k_on_offbest_caps_pair_best_v1", NG40_BEST_41K_CAPS_PAIR)
        )
    if NG40_BEST_41K_ON_FINEBEST.is_file():
        arm_paths.append(
            ("ng40_latent_eval_41k_on_offbest_best_v1", NG40_BEST_41K_ON_FINEBEST)
        )
    if NG40_BEST_41K_ON.is_file():
        arm_paths.append(("ng40_latent_eval_41k_on_best_v1", NG40_BEST_41K_ON))
    if NG40_BEST.is_file():
        arm_paths.append(("ng40_latent_eval_best_v1", NG40_BEST))
    if NG40_HIGH_JACCARD.is_file():
        arm_paths.append(("ng40_latent_eval_high_jaccard_v1", NG40_HIGH_JACCARD))
    seen_arms: set[str] = {a for a, _ in arm_paths}
    for p in eval_paths:
        arm = p.stem.replace("_latest", "")
        if arm in seen_arms:
            continue
        seen_arms.add(arm)
        arm_paths.append((arm, p))
    arm_paths.append(("ng40_crc_stub_v0", NG40_STUB))
    for arm_id, path in arm_paths:
        doc = _load(path)
        agg = _agg(doc)
        if not agg:
            continue
        saving_c = float(agg.get("global_token_saving_rate") or 0)
        j_c = float(agg.get("avg_reconstruction_fidelity_jaccard") or 0)
        delta_j_pp = (j_c - j_f) * 100
        beat = saving_c >= saving_f and j_c >= j_f
        floor_ok = saving_c >= min(MIN_SAVING, saving_f) and j_c >= min(
            MIN_JACCARD, j_f - 1e-6
        )
        drop_ok = delta_j_pp >= -MAX_J_DROP_PP
        candidates.append(
            {
                "arm_id": arm_id,
                "evidence_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "metrics": agg,
                "beat_check": {
                    "beat_frozen": beat,
                    "delta_saving_pp": round((saving_c - saving_f) * 100, 2),
                    "delta_jaccard_pp": round(delta_j_pp, 2),
                },
                "gates": {
                    "floor_saving_jaccard_ok": floor_ok,
                    "jaccard_drop_within_2pp": drop_ok,
                    "auto_track_a_promotion_allowed": beat and floor_ok and drop_ok,
                },
            }
        )

    def _is_41k_on_arm(arm_id: str) -> bool:
        return "41k_on" in arm_id

    def _strict_beat(c: dict[str, Any]) -> bool:
        bc = c.get("beat_check") or {}
        return bool(bc.get("beat_frozen")) and (
            float(bc.get("delta_saving_pp") or 0) > 0
            or float(bc.get("delta_jaccard_pp") or 0) > 0
        )

    def _pick_best(
        pool: list[dict[str, Any]], *, primary: str = "jaccard"
    ) -> dict[str, Any] | None:
        if not pool:
            return None
        strict = [c for c in pool if _strict_beat(c)]
        use = strict if strict else pool
        best_row = use[0]
        for c in use[1:]:
            m, b = c["metrics"], best_row["metrics"]
            if primary == "saving":
                key = (
                    float(m.get("global_token_saving_rate") or 0),
                    float(m.get("avg_reconstruction_fidelity_jaccard") or 0),
                )
                key_b = (
                    float(b.get("global_token_saving_rate") or 0),
                    float(b.get("avg_reconstruction_fidelity_jaccard") or 0),
                )
            else:
                key = (
                    float(m.get("avg_reconstruction_fidelity_jaccard") or 0),
                    float(m.get("global_token_saving_rate") or 0),
                )
                key_b = (
                    float(b.get("avg_reconstruction_fidelity_jaccard") or 0),
                    float(b.get("global_token_saving_rate") or 0),
                )
            if key > key_b:
                best_row = c
        return best_row

    def _candidate_by_arm(pool: list[dict[str, Any]], arm_id: str) -> dict[str, Any] | None:
        for c in pool:
            if c.get("arm_id") == arm_id:
                return c
        return None

    eligible = [c for c in candidates if c["gates"]["auto_track_a_promotion_allowed"]]
    on_eligible = [c for c in eligible if _is_41k_on_arm(c["arm_id"])]
    off_eligible = [c for c in eligible if not _is_41k_on_arm(c["arm_id"])]

    research_saving = (
        _candidate_by_arm(off_eligible, "ng40_latent_eval_best_v1")
        or _pick_best(off_eligible, primary="saving")
        or _pick_best(eligible, primary="saving")
    )
    research_jaccard = (
        _candidate_by_arm(off_eligible, "ng40_latent_eval_high_jaccard_v1")
        or _pick_best(off_eligible, primary="jaccard")
        or _pick_best(eligible, primary="jaccard")
    )
    research_best = research_saving
    active_best = _pick_best(on_eligible, primary="jaccard")

    export_prep_ready = bool(args.human_approve_research) and (
        research_best is not None or active_best is not None
    )

    active_apply_allowed = False
    active_apply_recommended = False
    if active_best:
        rep_path = (ROOT / str(active_best["evidence_path"]).replace("/", "\\")).with_suffix(
            ".report.json"
        )
        rep = _load(rep_path)
        rc = (rep or {}).get("run_config") or {}
        active_apply_allowed = export_prep_ready and rc.get(
            "use_master_codebook_lexicon_v1"
        ) is True
        active_apply_recommended = active_apply_allowed and _strict_beat(active_best)

    apply_forbidden = not active_apply_allowed
    best = research_best or active_best
    research_signoff_ready = bool(args.human_approve_research)

    packet = {
        "schema": "btrack_nextgen_promotion_candidate_packet_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "commander_research_approval": bool(args.human_approve_research),
        "reviewer": args.reviewer if args.human_approve_research else None,
        "note": args.note,
        "frozen_active_metrics": {
            "global_token_saving_rate": saving_f,
            "avg_reconstruction_fidelity_jaccard": j_f,
        },
        "candidates": candidates,
        "selected_arm": best["arm_id"] if best else None,
        "selected_arm_research_uplift": (
            research_best["arm_id"] if research_best else None
        ),
        "selected_arm_research_saving_uplift": (
            research_saving["arm_id"] if research_saving else None
        ),
        "selected_arm_research_jaccard_uplift": (
            research_jaccard["arm_id"] if research_jaccard else None
        ),
        "research_uplift_pick_policy": {
            "headline": "saving_first",
            "saving_primary": True,
            "jaccard_alternate_pinned": NG40_HIGH_JACCARD.is_file(),
        },
        "selected_arm_active_parity": (
            active_best["arm_id"] if active_best else None
        ),
        "active_apply_recommended": active_apply_recommended,
        "export_prep_ready": export_prep_ready,
        "research_signoff_ready": research_signoff_ready,
        "active_apply_allowed": active_apply_allowed,
        "apply_forbidden": apply_forbidden,
        "active_apply_blocker": (
            "41k_off_experimental_lane; TRACK_A_STRICT_LOCK + lexicon parity required"
            if export_prep_ready and not active_apply_allowed
            else None
        ),
        "would_change_active": False,
        "blocker_if_no_active_apply": (
            None
            if export_prep_ready
            else "beat_frozen false on all candidates (Jaccard below frozen ACTIVE typical ~0.87)"
        ),
        "apply_script": "scripts/apply_btrack_nextgen_promotion_to_active_v1.py",
        "pointers": {
            "charter": str(CHARTER.relative_to(ROOT)).replace("\\", "/") if CHARTER.is_file() else None,
            "parallel_bench": (
                str(PARALLEL.relative_to(ROOT)).replace("\\", "/")
                if PARALLEL.is_file()
                else None
            ),
            "infra_baseline": (
                str(NG_BASELINE.relative_to(ROOT)).replace("\\", "/")
                if NG_BASELINE.is_file()
                else None
            ),
        },
        "next_action": (
            "Research headline: selected_arm_research_saving_uplift (41k OFF, saving-first). "
            "Alternate: selected_arm_research_jaccard_uplift. "
            "ACTIVE apply only if selected_arm_active_parity strict-beats and "
            "TRACK_A_STRICT_LOCK released; skip apply on frozen tie (noop)."
            if export_prep_ready
            else "Improve ng40_latent_eval or stub; beat frozen Golden-40 first"
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.human_approve_research:
        signoff = {
            "schema": "btrack_nextgen_promotion_signoff_v1",
            "approved_at_utc": _utc(),
            "reviewer": args.reviewer,
            "note": args.note,
            "research_only": True,
            "packet_pointer": str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "selected_arm": packet["selected_arm"],
            "export_prep_ready": export_prep_ready,
            "active_apply_still_requires": [
                "apply_btrack_nextgen_promotion_to_active_v1.py",
                "--human-approve-promotion",
                "beat_check.beat_frozen true",
            ],
        }
        SIGNOFF_OUT.write_text(
            json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "export_prep_ready": export_prep_ready,
                "selected_arm": packet["selected_arm"],
                "apply_forbidden": apply_forbidden,
            },
            ensure_ascii=False,
        )
    )
    return 0 if args.human_approve_research else (0 if candidates else 1)


if __name__ == "__main__":
    raise SystemExit(main())
