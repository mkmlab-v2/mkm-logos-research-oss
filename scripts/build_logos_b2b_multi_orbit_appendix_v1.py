#!/usr/bin/env python3
"""Track C B2B Multi-Orbit appendix MD from showroom pack + variant layer (NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "docs/final/artifacts/logos_multi_orbit_showroom_pack_v1_latest.json"
DEFAULT_VARIANT = ROOT / "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json"
DEFAULT_KNN = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"
DEFAULT_KNN_PACK = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_pack_v1_latest.json"
DEFAULT_DSS_LANE_MANIFEST = ROOT / "docs/final/artifacts/logos_dss_satellite_lane_manifest_v1_latest.json"
DEFAULT_TR = ROOT / "docs/final/artifacts/logos_tr_tradition_scaffold_v1_latest.json"
DEFAULT_TR_NT = ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json"
DEFAULT_TR_CROSSVAL = ROOT / "docs/final/artifacts/logos_tr_scrollmapper_crossval_v1_latest.json"
DEFAULT_DSS_MANIFEST = ROOT / "docs/final/artifacts/logos_dss_enriched_manifest_v1_latest.json"
DEFAULT_DSS_SLOT_MAPPING = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
DEFAULT_DSS_STRICT_AUDIT = ROOT / "docs/final/artifacts/logos_dss_crossref_strict_gate_audit_v1_latest.json"
DEFAULT_DSS_REFRESH_PACK = ROOT / "docs/final/artifacts/logos_dss_slot_mapping_refresh_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/track_c_b2b_logos_multi_orbit_appendix_v1_latest.md"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_md(
    *,
    pack: dict[str, Any],
    variant: dict[str, Any] | None,
    knn: dict[str, Any] | None,
    knn_pack: dict[str, Any] | None,
    dss_lane_manifest: dict[str, Any] | None,
    tr: dict[str, Any] | None,
    tr_nt: dict[str, Any] | None,
    tr_crossval: dict[str, Any] | None,
    dss_manifest: dict[str, Any] | None,
    dss_slot_mapping: dict[str, Any] | None,
    dss_strict_audit: dict[str, Any] | None,
    dss_refresh_pack: dict[str, Any] | None,
    generated_at: str,
) -> str:
    summary = pack.get("summary") or {}
    dist_counts = summary.get("distance_status_counts") or {}
    lines = [
        "# Logos Multi-Orbit B2B Appendix (B-track · `[NON_GATING]`)",
        "",
        f"_Generated: {generated_at} UTC_",
        "",
        "## Boundary",
        "",
        pack.get("headline", ""),
        "",
        "- `ready_for_external_send`: **false** — 법무 Sign-off 전 대외 발송 금지.",
        "- 15 NT MT-only 스텁은 **complete JSONL에 병합하지 않음**.",
        "- TR·외경·DSS는 **별 궤도(Satellite)** 관측만.",
        "",
        "## Canon vs gap (Fact-Lock)",
        "",
        f"- Complete NT gap count: **{summary.get('complete_gap_nt', '?')}**",
        f"- Global medoid (observational): `{summary.get('global_medoid_verse_id', '?')}`",
        f"- Canon L2→medoid mean: `{summary.get('canon_l2_to_medoid_mean', '?')}`",
        f"- Gap L2→medoid mean: `{summary.get('gap_l2_to_medoid_mean', '?')}`",
        "",
        "## Textual-variant distance statuses",
        "",
    ]
    for st, n in sorted(dist_counts.items()):
        lines.append(f"- `{st}`: {n}")
    if variant:
        sample = (variant.get("entries") or [])[:3]
        if sample:
            lines.extend(["", "### Sample entries", ""])
            for e in sample:
                d = e.get("distance") or {}
                lines.append(
                    f"- `{e.get('verse_id')}`: status=`{d.get('status')}` "
                    f"L2=`{d.get('l2_vector_4d')}` proxy=`{d.get('sblgnt_proxy_verse_id')}`"
                )
    if knn and knn.get("satellite", {}).get("row_count"):
        sat = knn["satellite"]
        lines.extend(
            [
                "",
                "## Apocrypha satellite kNN (fixture lane)",
                "",
                f"- Rows: **{sat.get('row_count')}**",
                f"- L2 to medoid mean: `{sat.get('l2_to_medoid', {}).get('mean')}`",
                f"- kNN mean L2 to canon: `{sat.get('knn_mean_l2_to_canon', {}).get('mean')}`",
                f"- Δ vs canon mean: `{knn.get('contrast', {}).get('satellite_mean_minus_canon_mean')}`",
                "",
            ]
        )
    if tr:
        lines.extend(
            [
                "## TR tradition scaffold",
                "",
                f"- Verses awaiting licensed source: **{tr.get('verse_count', '?')}**",
                f"- Ingest contract: `{tr.get('ingest_contract', {}).get('expected_input', '?')}`",
                "",
            ]
        )
    if tr_nt:
        lines.extend(
            [
                "## TR full NT corpus (honza, B-track)",
                "",
                f"- Rows: **{tr_nt.get('row_count', '?')}**",
                f"- Gap 15/15 hits in TR: **{tr_nt.get('gap_policy_hits')}**",
                "",
            ]
        )
    if tr_crossval:
        gate = tr_crossval.get("gate") or {}
        counts = tr_crossval.get("counts") or {}
        lines.extend(
            [
                "## TR 2nd-source cross-validation (scrollmapper)",
                "",
                f"- Overlap compared: **{counts.get('overlap_compared', '?')}**",
                f"- Normalized exact match: **{counts.get('normalized_exact_match', '?')}**",
                f"- Gap 15/15 normalized match: **{gate.get('gap_15_of_15_normalized_match')}**",
                f"- Full-NT match rate: **{gate.get('full_nt_match_rate')}**",
                "",
            ]
        )
    if knn_pack and isinstance(knn_pack.get("satellites"), dict):
        dss_sat = knn_pack["satellites"].get("dss") or {}
        lines.extend(
            [
                "## DSS satellite kNN (4D lane)",
                "",
                f"- Vectors used: **{dss_sat.get('vectors_used', '?')}**",
                f"- L2 to medoid mean: `{dss_sat.get('l2_to_medoid', {}).get('mean')}`",
                f"- kNN mean L2 to canon: `{dss_sat.get('knn_mean_l2_to_canon', {}).get('mean')}`",
                f"- Δ vs canon mean: `{dss_sat.get('contrast_delta')}`",
                "",
            ]
        )
    if dss_lane_manifest:
        lines.extend(
            [
                "## DSS 4D satellite lane",
                "",
                f"- Lane rows: **{dss_lane_manifest.get('row_count', '?')}**",
                f"- Output: `{dss_lane_manifest.get('output_lane_jsonl', '?')}`",
                "",
            ]
        )
    if dss_manifest:
        lines.extend(
            [
                "## DSS enriched source (text)",
                "",
                f"- Rows: **{dss_manifest.get('row_count', '?')}**",
                f"- Input: `{dss_manifest.get('input_jsonl', '?')}`",
                "",
            ]
        )
    if dss_slot_mapping:
        sk = dss_slot_mapping.get("kpi") or {}
        lines.extend(
            [
                "## DSS × CROSS_REF 16-slot mapping (`[NON_GATING]`)",
                "",
                f"- Mapped slots: **{sk.get('mapped_slot_count', '?')}/16**",
                f"- Coverage: **{sk.get('slot_coverage_rate', '?')}**",
                f"- Mean confidence boost (v2 heuristic): **{sk.get('mean_confidence_boost', '?')}**",
                f"- Target ≥0.8 OK: **{sk.get('target_mean_confidence_boost_ok')}**",
                "",
            ]
        )
    if dss_strict_audit:
        gk = dss_strict_audit.get("kpi") or {}
        lines.extend(
            [
                "## DSS strict partial-anchor gate audit (`[NON_GATING]`)",
                "",
                f"- Entries audited (ENTRY_06–15): **{gk.get('entries_audited', '?')}**",
                f"- Strict gate pass: **{gk.get('strict_gate_pass', '?')}/{gk.get('entries_audited', '?')}**",
                f"- Primary DSS `.md` mapping: **{gk.get('primary_dss_md_mapping_count', '?')}/{gk.get('entries_audited', '?')}**",
                f"- CROSS_REF contract OK: **{(dss_strict_audit.get('gate') or {}).get('cross_ref_contract_ok')}**",
                "",
            ]
        )
    if dss_refresh_pack:
        cf = dss_refresh_pack.get("canonical_filter") or {}
        cmp_ = dss_refresh_pack.get("comparison") or {}
        lines.extend(
            [
                "## DSS slot mapping refresh (full vs canonical)",
                "",
                f"- Canonical rows kept: **{cf.get('kept_rows', '?')}** / **{cf.get('input_rows', '?')}**",
                f"- Full map: **{(dss_refresh_pack.get('full_mapping') or {}).get('mapped_slot_count', '?')}/16**",
                f"- Canonical map: **{(dss_refresh_pack.get('canonical_mapping') or {}).get('mapped_slot_count', '?')}/16**",
                f"- Slots divergent (full≠canonical): **{cmp_.get('divergent_slot_count', '?')}**",
                "",
            ]
        )
    lines.extend(
        [
            "## Artifacts",
            "",
            "```json",
            json.dumps(pack.get("artifact_refs") or {}, ensure_ascii=False, indent=2),
            "```",
            "",
            "_`[HYPO]` 분포·구조 관측용. 시장 예측·신학적 진리·무손실 단정 금지._",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--variant-json", type=Path, default=DEFAULT_VARIANT)
    ap.add_argument("--knn-json", type=Path, default=DEFAULT_KNN)
    ap.add_argument("--tr-json", type=Path, default=DEFAULT_TR)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pack = _load(args.pack_json)
    if not pack:
        print(f"missing pack: {args.pack_json}", file=sys.stderr)
        return 2

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    md = build_md(
        pack=pack,
        variant=_load(args.variant_json),
        knn=_load(args.knn_json),
        knn_pack=_load(DEFAULT_KNN_PACK),
        dss_lane_manifest=_load(DEFAULT_DSS_LANE_MANIFEST),
        tr=_load(args.tr_json),
        tr_nt=_load(DEFAULT_TR_NT),
        tr_crossval=_load(DEFAULT_TR_CROSSVAL),
        dss_manifest=_load(DEFAULT_DSS_MANIFEST),
        dss_slot_mapping=_load(DEFAULT_DSS_SLOT_MAPPING),
        dss_strict_audit=_load(DEFAULT_DSS_STRICT_AUDIT),
        dss_refresh_pack=_load(DEFAULT_DSS_REFRESH_PACK),
        generated_at=generated_at,
    )
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
