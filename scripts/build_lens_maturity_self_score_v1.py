#!/usr/bin/env python3
"""Build 3-lens maturity self-scores (10-pt rubric v2) for ops/Telegram synthesis.

B-track [HYPO] · not Track A promotion proof · Logos [NON_GATING].
v2 order: ①명리 D ②성경 D ③사상 B/C — gate-driven from artifacts (see lens_maturity_scoring_v2.py).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lens_maturity_scoring_v2 import (
    score_logos_a_v2,
    score_logos_d_v2,
    score_myeongni_a_c_v2,
    score_myeongni_d_v2,
    score_sasang_a_v2,
    score_sasang_b_c_v2,
    score_sasang_c_v2,
    score_sasang_d_v2,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "reports" / "lens_maturity_self_score_v1_latest.json"
SCHEMA_ID = "lens_maturity_self_score_v2"

# Rubric anchors (human-reviewed 2026-06-04); script adjusts D slightly from live gates.
BASE = {
    "myeongni": {
        "label_ko": "명리",
        "axes": {"A_engine": 8.5, "B_governance": 8.0, "C_product": 7.0, "D_validation": 5.0},
        "notes_ko": [
            "만세력·stage2 realset·체인 SSOT 두께",
            "시장 단독 적중 헤드라인 미고정",
        ],
    },
    "logos": {
        "label_ko": "성경",
        "axes": {"A_engine": 7.5, "B_governance": 8.5, "C_product": 9.0, "D_validation": 6.0},
        "notes_ko": [
            "GraphRAG·일일융합·브리핑 최상",
            "독립렌즈 sample-batch 괴리 주의",
            "[NON_GATING]",
        ],
    },
    "sasang": {
        "label_ko": "사상",
        "axes": {"A_engine": 7.5, "B_governance": 7.0, "C_product": 6.5, "D_validation": 6.0},
        "notes_ko": [
            "4-agent·high-reliability 게이트",
            "fusion_gate HOLD 시 B -0.5",
        ],
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _composite(axes: Dict[str, float]) -> float:
    vals = [axes["A_engine"], axes["B_governance"], axes["C_product"], axes["D_validation"]]
    return round(sum(vals) / len(vals), 1)


def _apply_live_adjustments(ws: Path, lens_id: str, axes: Dict[str, float], notes: List[str]) -> Dict[str, float]:
    out = dict(axes)
    art = ws / "docs" / "final" / "artifacts"

    if lens_id == "myeongni":
        if not _read_json(art / "myeongni_stage2_realset_gate_latest.json").get("pass"):
            out["A_engine"] = min(out["A_engine"], 7.0)
            notes.append("stage2 realset gate missing/fail")
        shadow = _read_json(art / "independent_lens_shadow_gate_latest.json").get("decision", "")
        if shadow != "KEEP_OBSERVATION_ONLY":
            notes.append(f"shadow_gate={shadow}")

    elif lens_id == "logos":
        lo = _read_json(art / "logos_independent_lens_latest.json")
        prov = lo.get("provenance") if isinstance(lo.get("provenance"), dict) else {}
        src = str(prov.get("source", ""))
        if src == "ann_resonance_graphrag":
            out["A_engine"] = min(8.5, out["A_engine"] + 0.5)
            notes.append("logos_production_evidence")
            if "독립렌즈 sample-batch 괴리 주의" in notes:
                notes.remove("독립렌즈 sample-batch 괴리 주의")
        elif "sample" in str(prov.get("input_path", "")).lower():
            out["A_engine"] = min(out["A_engine"], 7.5)
            notes.append("independent_lens=sample_batch")
        rag = _read_json(art / "logos_rag_btrack_promotion_gate_v1_latest.json")
        tiers = rag.get("tiers") if isinstance(rag.get("tiers"), dict) else {}
        l2 = tiers.get("L2_track_c_shadow_ingest") if isinstance(tiers.get("L2_track_c_shadow_ingest"), dict) else {}
        if l2.get("passed"):
            notes.append("rag_L2_pass")
        else:
            out["B_governance"] = min(out["B_governance"], 7.5)
        oos = _read_json(art / "prophecy_logos_revalidation_oos_gate_latest.json")
        gate = oos.get("gate") if isinstance(oos.get("gate"), dict) else {}
        if gate.get("go"):
            hit = (oos.get("oos_metrics") or {}).get("directional_hit_rate_active")
            notes.append(f"prophecy_logos_oos_hit={hit}")

    elif lens_id == "sasang":
        if "fusion_gate HOLD 시 B -0.5" in notes:
            notes.remove("fusion_gate HOLD 시 B -0.5")

    return out


def _apply_v2_axis_scores(
    ws: Path, lens_id: str, axes: Dict[str, float], notes: List[str]
) -> Dict[str, float]:
    """Gate-driven overrides: ①명리 D ②성경 D ③사상 B/C."""
    out = dict(axes)
    if lens_id == "myeongni":
        a, c, ac_notes = score_myeongni_a_c_v2(ws, _read_json)
        out["A_engine"] = a
        out["C_product"] = c
        notes.extend(ac_notes)
        d, d_notes = score_myeongni_d_v2(ws, _read_json)
        out["D_validation"] = d
        notes.extend(d_notes)
    elif lens_id == "logos":
        a, a_notes = score_logos_a_v2(ws, _read_json)
        out["A_engine"] = a
        notes.extend(a_notes)
        d, d_notes = score_logos_d_v2(ws, _read_json)
        out["D_validation"] = d
        notes.extend(d_notes)
    elif lens_id == "sasang":
        b, _, bc_notes = score_sasang_b_c_v2(ws, _read_json)
        out["B_governance"] = b
        notes.extend(bc_notes)
        a, a_notes = score_sasang_a_v2(ws, _read_json)
        out["A_engine"] = a
        notes.extend(a_notes)
        c, c_notes = score_sasang_c_v2(ws, _read_json)
        out["C_product"] = c
        notes.extend(c_notes)
        d, d_notes = score_sasang_d_v2(ws, _read_json)
        out["D_validation"] = d
        notes.extend(d_notes)
    return out


def build_lens_maturity_self_score(workspace: Path | None = None) -> Dict[str, Any]:
    ws = (workspace or ROOT).resolve()
    lenses_out: Dict[str, Any] = {}
    evidence_refs: List[Dict[str, str]] = []

    for lens_id, base in BASE.items():
        notes = list(base["notes_ko"])
        axes = _apply_live_adjustments(ws, lens_id, base["axes"], notes)
        axes = _apply_v2_axis_scores(ws, lens_id, axes, notes)
        comp = _composite(axes)
        lenses_out[lens_id] = {
            "label_ko": base["label_ko"],
            "axes": {k: round(v, 1) for k, v in axes.items()},
            "composite_10": comp,
            "one_liner_ko": (
                f"{base['label_ko']} {comp}/10 "
                f"(A{axes['A_engine']:.1f} B{axes['B_governance']:.1f} "
                f"C{axes['C_product']:.1f} D{axes['D_validation']:.1f})"
            ),
            "notes_ko": notes[:8],
        }

    comps = [lenses_out[k]["composite_10"] for k in ("myeongni", "logos", "sasang")]
    telegram_line = (
        "━━ 렌즈 고도화(10·[HYPO]·비게이팅) ━━\n"
        f"  명리 {lenses_out['myeongni']['composite_10']} · "
        f"성경 {lenses_out['logos']['composite_10']} · "
        f"사상 {lenses_out['sasang']['composite_10']}\n"
        "  (A엔진·B거버넌스·C제품·D검증 평균 · Track A·적중 단정 아님)"
    )
    oos_gate = _read_json(ws / "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json")
    oos_m = oos_gate.get("oos_metrics") if isinstance(oos_gate.get("oos_metrics"), dict) else {}
    d_hit = oos_m.get("directional_hit_rate_active")
    if d_hit is not None:
        telegram_line += f"\n  성경 D(OOS SSOT)={float(d_hit):.4f} · [NON_GATING] · 승격=golden sparse KOSPI"
    compare_path = ws / "reports/logos_oos_sidecar_variant_compare_v1_latest.json"
    if compare_path.is_file():
        cmp_doc = _read_json(compare_path)
        foot: list[str] = []
        for v in cmp_doc.get("variants") or []:
            if not isinstance(v, dict) or v.get("missing"):
                continue
            lab = str(v.get("label") or "")
            if lab in ("hybrid_ext", "birth_sw025", "birth_sw025_band006") and v.get("oos_hit") is not None:
                foot.append(f"{lab} hit={float(v['oos_hit']):.3f} n={v.get('oos_n_active','?')}")
        if foot:
            telegram_line += "\n  연구각주(B-track·미승격): " + " · ".join(foot)

    for rel in (
        "docs/final/artifacts/myeongni_promotion_gate_latest.json",
        "docs/final/artifacts/logos_rag_btrack_promotion_gate_v1_latest.json",
        "docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json",
        "docs/final/artifacts/independent_lens_shadow_gate_latest.json",
    ):
        if (ws / rel).is_file():
            evidence_refs.append({"path": rel, "role": "ssot_pointer"})

    for rel, role in (
        ("reports/myeongni_lens_observation_report_v1_latest.json", "myeongni_d_v2"),
        ("reports/sasang_lens_observation_report_v1_latest.json", "sasang_d_v2"),
        ("docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json", "sasang_shadow_hit"),
    ):
        if (ws / rel).is_file():
            evidence_refs.append({"path": rel, "role": role})
    evidence_refs.append(
        {
            "path": "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json",
            "role": "logos_d_v2",
        }
    )

    doc = {
        "schema": SCHEMA_ID,
        "scoring_version": "v2_gate_driven",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "rubric_ko": "A=엔진·재현 B=운영·거버넌스 C=해석·제품 D=예측·검증 (각 0~10, 평균=composite; v2 D/B/C=게이트·관측 SSOT)",
        "axis_caps_ko": "축 상한 8.5(성경 D 8.0). 10점=human sign-off·전용 벤치 별도.",
        "lenses": lenses_out,
        "ranking_by_composite": sorted(
            ["myeongni", "logos", "sasang"],
            key=lambda k: lenses_out[k]["composite_10"],
            reverse=True,
        ),
        "telegram_synthesis_block_ko": telegram_line,
        "disclaimer_ko": "자체 채점·관측용. verify_p0·Track A 승격·실매매 GO와 무관.",
        "evidence_refs": evidence_refs,
    }
    return doc


def write_lens_maturity_self_score(workspace: Path | None = None, out_path: Path | None = None) -> Path:
    ws = (workspace or ROOT).resolve()
    dest = out_path or (ws / "reports" / "lens_maturity_self_score_v1_latest.json")
    doc = build_lens_maturity_self_score(ws)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()
    path = write_lens_maturity_self_score(args.workspace_root.resolve(), args.out)
    doc = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    print(f"WROTE: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
