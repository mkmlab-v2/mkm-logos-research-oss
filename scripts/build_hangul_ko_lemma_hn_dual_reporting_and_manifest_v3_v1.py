#!/usr/bin/env python3
"""HN Dual Reporting card + manifest v3 (Golden-40 evidence-only ko lemmas)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HIT = ROOT / "reports/hangul_ko_lemma_golden40_case_hit_map_v1_latest.json"
AB = ROOT / "reports/hangul_ko_lemma_golden40_ab_41708_vs_41696_pruned_v1_latest.json"
POINTER = ROOT / "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
V2_CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_V2_CANDIDATE.json"
V2_APPLY = ROOT / "reports/hangul_curated_v2_active_report_apply_v1_latest.json"
V2_PRUNED_MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2_pruned.json"
CARD_OUT = ROOT / "reports/hangul_ko_lemma_hn_dual_reporting_card_v1_latest.json"
MANIFEST_V3_OUT = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json"
PACKET_OUT = ROOT / "reports/hangul_ko_lemma_wave3_research_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(doc: dict[str, Any]) -> dict[str, Any]:
    m = doc.get("compression_metrics") or doc.get("golden40_kpi") or {}
    saving = m.get("global_token_saving_rate")
    jaccard = m.get("avg_reconstruction_fidelity_jaccard")
    return {
        "global_token_saving_rate": saving,
        "global_token_saving_rate_pct": round(float(saving) * 100, 2) if saving is not None else None,
        "avg_reconstruction_fidelity_jaccard": jaccard,
    }


def _tier_lookup() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for rel in (
        V2_PRUNED_MANIFEST,
        ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json",
        ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json",
    ):
        if not rel.is_file():
            continue
        for ent in _read_json(rel).get("lemmas") or []:
            form = str(ent.get("form") or "")
            if form and form not in out:
                out[form] = {
                    "tier": str(ent.get("tier") or "Z_golden40_evidence"),
                    "source": str(ent.get("source") or "golden40_case_hit_map_v1"),
                }
    return out


def build_dual_reporting_card() -> dict[str, Any]:
    hit = _read_json(HIT)
    ab = _read_json(AB) if AB.is_file() else {}
    pointer = _read_json(POINTER) if POINTER.is_file() else {}
    active = _read_json(ACTIVE) if ACTIVE.is_file() else {}
    v2c = _read_json(V2_CANDIDATE) if V2_CANDIDATE.is_file() else {}
    v2apply = _read_json(V2_APPLY) if V2_APPLY.is_file() else {}

    prod = pointer.get("production_ssot") or {}
    ms_archive = (pointer.get("frozen_ms_external_headline") or {}).get("ms_submission_archive") or {}

    reproduce_41708 = (ab.get("summary") or {}).get("metrics_production_41708") or {}
    reproduce_41658 = (hit.get("summary") or {}).get("metrics_41658") or {}

    active_disk = _metrics(active)
    v2_candidate = _metrics(v2c)
    pointer_bench = _metrics({"golden40_kpi": prod.get("golden40_kpi") or {}})
    v2_apply_logged = v2apply.get("compression_metrics") or {}

    active_drift = None
    if v2_apply_logged.get("global_token_saving_rate") and active_disk.get("global_token_saving_rate"):
        ds = (float(active_disk["global_token_saving_rate"]) - float(v2_apply_logged["global_token_saving_rate"])) * 100
        if abs(ds) > 0.05:
            active_drift = {
                "note": "ACTIVE file on disk differs from v2 apply log — cite both; do not collapse.",
                "v2_apply_log_saving_pct": round(float(v2_apply_logged["global_token_saving_rate"]) * 100, 2),
                "active_disk_saving_pct": active_disk.get("global_token_saving_rate_pct"),
                "delta_pp": round(ds, 2),
            }

    hn_one_liner_ko = (
        "41k 본체는 Logos 원어(그리스·히브리) 보존 rail; "
        "한글 42 lemma overlay는 cmp2_011–040 30건에 국소 must_keep — core 10건 enterprise bench hit 0."
    )

    return {
        "schema": "hangul_ko_lemma_hn_dual_reporting_card_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "reproduce": "py scripts/build_hangul_ko_lemma_hn_dual_reporting_and_manifest_v3_v1.py",
        "hn_one_liner_ko": hn_one_liner_ko,
        "hn_one_liner_en": (
            "41k base = Logos Greek/Hebrew preservation lexicon; "
            "42 Korean lemmas are a curated must_keep overlay firing on cmp2_011–040 only (0/10 core cases)."
        ),
        "dual_reporting_lanes": [
            {
                "lane_id": "bench_pointer_ssot",
                "role": "Track A production lexicon pointer (41708 file, 41700 rows, ko 42)",
                "rewrite_allowed": False,
                "path": str(POINTER.relative_to(ROOT)).replace("\\", "/"),
                "metrics": pointer_bench,
                "headline": prod.get("ms_paste_headline"),
            },
            {
                "lane_id": "v2_active_apply_log",
                "role": "v2 ACTIVE apply log (2026-06-03) — intended bench KPI after Hangul v2",
                "rewrite_allowed": False,
                "path": str(V2_APPLY.relative_to(ROOT)).replace("\\", "/"),
                "metrics": {
                    "global_token_saving_rate": v2_apply_logged.get("global_token_saving_rate"),
                    "global_token_saving_rate_pct": round(
                        float(v2_apply_logged.get("global_token_saving_rate", 0)) * 100, 2
                    )
                    if v2_apply_logged.get("global_token_saving_rate") is not None
                    else None,
                    "avg_reconstruction_fidelity_jaccard": v2_apply_logged.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "ms_paste_headline": v2apply.get("ms_paste_headline"),
            },
            {
                "lane_id": "active_report_disk",
                "role": "MULTILENS ACTIVE on disk (current file bytes)",
                "rewrite_allowed": False,
                "path": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
                "metrics": active_disk,
                "drift_vs_v2_apply": active_drift,
            },
            {
                "lane_id": "ms_submission_archive",
                "role": "Submitted MS ma-jung archive — FAIL-COMP-004 rewrite false",
                "rewrite_allowed": False,
                "path": str(POINTER.relative_to(ROOT)).replace("\\", "/"),
                "metrics": {
                    "global_token_saving_rate": ms_archive.get("global_token_saving_rate"),
                    "global_token_saving_rate_pct": ms_archive.get("global_token_saving_rate_pct"),
                    "avg_reconstruction_fidelity_jaccard": ms_archive.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "note": ms_archive.get("note"),
            },
            {
                "lane_id": "reproduce_eval_golden40_ab",
                "role": "Reproduce eval via build_master_codebook_golden40_lexicon_ab (41708 lexicon)",
                "rewrite_allowed": False,
                "path": str(AB.relative_to(ROOT)).replace("\\", "/"),
                "metrics": {
                    "global_token_saving_rate": reproduce_41708.get("global_token_saving_rate"),
                    "global_token_saving_rate_pct": round(
                        float(reproduce_41708.get("global_token_saving_rate", 0)) * 100, 2
                    )
                    if reproduce_41708.get("global_token_saving_rate") is not None
                    else None,
                    "avg_reconstruction_fidelity_jaccard": reproduce_41708.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "baseline_41658_same_path": {
                    "global_token_saving_rate_pct": round(
                        float(reproduce_41658.get("global_token_saving_rate", 0)) * 100, 2
                    )
                    if reproduce_41658.get("global_token_saving_rate") is not None
                    else None,
                    "avg_reconstruction_fidelity_jaccard": reproduce_41658.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
            },
        ],
        "evidence_anchors": {
            "hit_map": str(HIT.relative_to(ROOT)).replace("\\", "/"),
            "ab_41708_vs_41696": str(AB.relative_to(ROOT)).replace("\\", "/"),
            "ko_inventory_production": hit.get("ko_lemma_inventory_count"),
            "ko_fired_golden40": hit.get("summary", {}).get("ko_lemma_fired_count"),
            "golden40_core_ko_hits": hit.get("summary", {}).get("golden40_core_with_ko_hits"),
            "cmp2_hangul_subset_ko_hits": hit.get("summary", {}).get("cmp2_subset_with_ko_hits"),
        },
        "forbidden_claims": [
            "41k is a Korean-specialized dictionary (base is Logos Greek/Hebrew/other).",
            "All 42 ko lemmas fire on Golden-40 (18/42 fire; core 10 cases = 0).",
            "Collapse MS archive 47.54% with bench pointer 48.8% in public copy.",
            "Auto-promote 41696 pruned or manifest v3 without commander signoff chain.",
        ],
    }


def build_manifest_v3(hit: dict[str, Any]) -> dict[str, Any]:
    fire: dict[str, int] = dict((hit.get("summary") or {}).get("ko_lemma_fire_count") or {})
    inventory: list[str] = list(hit.get("ko_lemma_inventory") or [])
    tiers = _tier_lookup()

    kept: list[dict[str, Any]] = []
    for form, count in sorted(fire.items(), key=lambda x: (-x[1], x[0])):
        meta = tiers.get(form, {"tier": "Z_golden40_evidence", "source": "golden40_case_hit_map_v1"})
        kept.append(
            {
                "form": form,
                "tier": meta["tier"],
                "source": meta["source"],
                "golden40_case_hit_count": count,
            }
        )

    never_fired = [f for f in inventory if f.lower() not in {k.lower() for k in fire}]
    dropped_from_production: list[dict[str, Any]] = []
    for form in never_fired:
        meta = tiers.get(form, {"tier": "unknown", "source": "production_41708_inventory"})
        dropped_from_production.append(
            {
                "form": form,
                "tier": meta["tier"],
                "source": meta["source"],
                "drop_reason": "never_fired_golden40_40_cases",
            }
        )

    return {
        "schema": "hangul_lexicon_curated_ingest_v3_golden40_evidence",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "wave": 3,
        "parent_manifest_v2_pruned": str(V2_PRUNED_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "evidence_inputs": {
            "hit_map": str(HIT.relative_to(ROOT)).replace("\\", "/"),
            "ab_41708_vs_41696": str(AB.relative_to(ROOT)).replace("\\", "/"),
        },
        "selection_policy": "golden40_case_hit_count_gt_0_only",
        "lemma_count": len(kept),
        "lemmas": kept,
        "dropped_from_production_42": dropped_from_production,
        "dropped_count": len(dropped_from_production),
        "overlay_output_role_v3_draft": (
            "reports/constitution/btrack_pilot/"
            "master_codebook_lexicon_v1_41658_hangul_curated_overlay_v3_golden40_evidence.json"
        ),
        "promotion": "HOLD — draft only; export overlay + double gate + commander signoff required",
        "acceptance_gates": {
            "gate1_cmp2_cases_with_hit_gt_0": 25,
            "gate2_golden40_delta_saving_pp_min": -0.02,
        },
    }


def main() -> int:
    missing = [p for p in (HIT, AB, POINTER) if not p.is_file()]
    if missing:
        print("ABORT: missing inputs:", ", ".join(str(p) for p in missing))
        return 1

    hit = _read_json(HIT)
    card = build_dual_reporting_card()
    manifest_v3 = build_manifest_v3(hit)

    packet = {
        "schema": "hangul_ko_lemma_wave3_research_packet_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "reproduce": "py scripts/build_hangul_ko_lemma_hn_dual_reporting_and_manifest_v3_v1.py",
        "outputs": {
            "hn_dual_reporting_card": str(CARD_OUT.relative_to(ROOT)).replace("\\", "/"),
            "manifest_v3_golden40_evidence": str(MANIFEST_V3_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "summary": {
            "manifest_v3_lemma_count": manifest_v3["lemma_count"],
            "manifest_v3_dropped_count": manifest_v3["dropped_count"],
            "dual_reporting_lane_count": len(card["dual_reporting_lanes"]),
            "active_disk_drift": (card["dual_reporting_lanes"][2].get("drift_vs_v2_apply")),
        },
    }

    CARD_OUT.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST_V3_OUT.write_text(json.dumps(manifest_v3, ensure_ascii=False, indent=2), encoding="utf-8")
    PACKET_OUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"WROTE: {CARD_OUT}")
    print(f"WROTE: {MANIFEST_V3_OUT}")
    print(f"WROTE: {PACKET_OUT}")
    print(f"manifest_v3={manifest_v3['lemma_count']} lemmas dropped={manifest_v3['dropped_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
