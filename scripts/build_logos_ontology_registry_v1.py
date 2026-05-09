#!/usr/bin/env python3
"""Build Logos ontology mapping registry (NON_GATING) from 63779 + morphology registries."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_63779 = ART / "logos_63779_registry_v1_latest.json"
DEFAULT_MORPH = ART / "logos_morphology_registry_v1_latest.json"
DEFAULT_OUT = ART / "logos_ontology_registry_v1_latest.json"

_LEMMA_TO_STRONGS: dict[str, tuple[str, str]] = {
    "ברא": ("H1254", "Genesis 1:1"),
    "אמר": ("H0559", "Genesis 1:3"),
    "אור": ("H0216", "Genesis 1:3"),
    "טוב": ("H2896", "Genesis 1:4"),
    "תהו": ("H8414", "Genesis 1:2"),
    "תהום": ("H8415", "Genesis 1:2"),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _band_from_ratio(v: float) -> str:
    if v < 1.0:
        return "<1x"
    if v < 3.0:
        return "1-3x"
    if v < 10.0:
        return "3-10x"
    return "10x+"


def _morph_roots(morph_layer: dict[str, Any], limit: int = 6) -> list[dict[str, str]]:
    def _coerce_strongs_from_lemma(lemma: str) -> str | None:
        m = re.search(r"(\d{1,4})", lemma)
        if not m:
            return None
        num = int(m.group(1))
        if num <= 0:
            return None
        return f"H{num:04d}"

    roots: list[dict[str, str]] = []
    rows = morph_layer.get("top_lemmas") if isinstance(morph_layer.get("top_lemmas"), list) else []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        lemma = str(row.get("lemma") or "").strip()
        if not lemma:
            continue
        strongs, ref = _LEMMA_TO_STRONGS.get(lemma, ("H0000", "UNVERIFIED_REF"))
        if strongs == "H0000":
            derived = _coerce_strongs_from_lemma(lemma)
            if derived:
                strongs = derived
                ref = "STRONGS_LEXICON"
        roots.append(
            {
                "lemma": lemma,
                "strongs_code": strongs,
                "canonical_reference": ref,
                "verification_status": "verified" if strongs != "H0000" else "unverified",
            }
        )
    if roots:
        return roots
    return [
        {
            "lemma": "placeholder_root",
            "strongs_code": "H0000",
            "canonical_reference": "UNVERIFIED_REF",
            "verification_status": "unverified",
        }
    ]


def build_registry(reg63779: dict[str, Any], reg_morph: dict[str, Any]) -> dict[str, Any]:
    deep = reg63779.get("deep_logos_tension_gematria") if isinstance(reg63779.get("deep_logos_tension_gematria"), dict) else {}
    arch = reg63779.get("archetypal_chaos_order_phase") if isinstance(reg63779.get("archetypal_chaos_order_phase"), dict) else {}
    regime_ctx = reg63779.get("regime_context") if isinstance(reg63779.get("regime_context"), dict) else {}
    morph_layer = reg_morph.get("morphology_layer") if isinstance(reg_morph.get("morphology_layer"), dict) else {}

    chaos = float(arch.get("chaos_score") or 0.0)
    order = float(arch.get("order_score") or 0.0)
    similarity = float(deep.get("similarity_0_1") or 0.0)
    cohesion_ratio = float(deep.get("cohesion_ratio") or 0.0)
    tension = _clip01((chaos * 0.5) + ((1.0 - order) * 0.35) + (_clip01(cohesion_ratio / 10.0) * 0.15))
    cohesion_band = str(deep.get("cohesion_band") or _band_from_ratio(cohesion_ratio))
    phase_label = str(arch.get("phase_label") or "balanced_tension")
    regime = str(regime_ctx.get("primary_regime") or "unknown")

    numeric_symbols = [
        {
            "symbol_id": "gematria_63779",
            "label": "63779 pattern id",
            "raw_value": 63779.0,
            "normalized_ratio": round(similarity, 6),
            "band_label": "pattern_similarity",
            "role": "pattern_id",
        },
        {
            "symbol_id": "cohesion_3000000_threshold",
            "label": "3M cohesion threshold",
            "raw_value": 3000000.0,
            "normalized_ratio": round(_clip01(cohesion_ratio / 3.0), 6),
            "band_label": "cohesion_threshold_3m",
            "role": "cohesion_threshold",
        },
        {
            "symbol_id": "cohesion_10000000_threshold",
            "label": "10M cohesion threshold",
            "raw_value": 10000000.0,
            "normalized_ratio": round(_clip01(cohesion_ratio / 10.0), 6),
            "band_label": "cohesion_threshold_10m",
            "role": "cohesion_threshold",
        },
    ]

    roots = _morph_roots(morph_layer)
    first_root = roots[0]["lemma"]
    atoms = [
        {
            "atom_id": "atom_chaos_pressure",
            "label": "Chaos pressure over order",
            "source_type": "numeric",
            "source_ref": "gematria_63779",
            "tensor_4d_alignment": {
                "S": round(_clip01(0.35 + tension * 0.15), 6),
                "L": round(_clip01(0.45 + similarity * 0.2), 6),
                "K": round(_clip01(0.5 + chaos * 0.35), 6),
                "M": round(_clip01(0.4 + cohesion_ratio / 15.0), 6),
            },
        },
        {
            "atom_id": "atom_order_rebuild_watch",
            "label": "Order rebuild watchpoint",
            "source_type": "regime",
            "source_ref": regime,
            "tensor_4d_alignment": {
                "S": round(_clip01(0.4 + order * 0.2), 6),
                "L": round(_clip01(0.5 + order * 0.25), 6),
                "K": round(_clip01(0.3 + (1.0 - chaos) * 0.3), 6),
                "M": round(_clip01(0.45 + _clip01(cohesion_ratio / 12.0) * 0.25), 6),
            },
        },
        {
            "atom_id": "atom_morph_root_anchor",
            "label": "Morphology root anchor",
            "source_type": "morphology",
            "source_ref": first_root,
            "tensor_4d_alignment": {
                "S": 0.55,
                "L": 0.65,
                "K": 0.45,
                "M": 0.35,
            },
        },
    ]

    relations = [
        {
            "rule_id": "rule_babel_tension_v1",
            "if_condition": "chaos_score > 0.8 and cohesion_ratio >= 4.0",
            "then_atoms": ["atom_chaos_pressure", "atom_morph_root_anchor"],
            "metaphor_key": "babel_tension",
            "falsification_trigger": [
                "chaos_score < 0.55 for 2 consecutive updates",
                "cohesion_ratio < 2.0",
            ],
        },
        {
            "rule_id": "rule_order_rebuild_v1",
            "if_condition": "order_score >= chaos_score and similarity_0_1 >= 0.5",
            "then_atoms": ["atom_order_rebuild_watch", "atom_morph_root_anchor"],
            "metaphor_key": "order_rebuild_watch",
            "falsification_trigger": [
                "order_score < 0.45",
                "similarity_0_1 < 0.3 for 3 consecutive updates",
            ],
        },
        {
            "rule_id": "rule_crisis_memory_imf_v1",
            "if_condition": "regime == 'imf' and similarity_0_1 >= 0.5",
            "then_atoms": ["atom_order_rebuild_watch", "atom_chaos_pressure"],
            "metaphor_key": "crisis_memory_reframe",
            "falsification_trigger": [
                "regime != 'imf'",
                "similarity_0_1 < 0.35 for 2 consecutive updates",
            ],
        },
        {
            "rule_id": "rule_tension_release_watch_v1",
            "if_condition": "tension_score < 0.45 and order_score >= 0.55",
            "then_atoms": ["atom_order_rebuild_watch"],
            "metaphor_key": "tension_release_watch",
            "falsification_trigger": [
                "tension_score >= 0.6",
                "order_score < 0.5",
            ],
        },
    ]

    templates = [
        {
            "metaphor_key": "babel_tension",
            "template": "응집이 과도하게 집중되어 바벨탑 텐션이 커지는 구간으로 해석한다. 관측 지표의 균열 여부를 우선 점검한다.",
            "non_gating_footer": "[NON_GATING] 상징 해석은 실행 트리거가 아니다.",
        },
        {
            "metaphor_key": "order_rebuild_watch",
            "template": "혼돈 대비 질서 회복 신호가 우세해지는 재정렬 구간으로 본다. 구조적 재배열의 지속성을 관측한다.",
            "non_gating_footer": "[NON_GATING] 해석은 설명 계층이며 가격 단정이 아니다.",
        },
        {
            "metaphor_key": "crisis_memory_reframe",
            "template": "위기 기억 레짐의 잔향이 남아 있어 과거 서사를 현재에 과투영할 위험이 있다. 구조 전환 여부를 분리 관측한다.",
            "non_gating_footer": "[NON_GATING] 이 문장은 리스크 해설이며 실행 트리거가 아니다.",
        },
        {
            "metaphor_key": "tension_release_watch",
            "template": "텐션 완화 구간에서 질서 회복 후보가 관측된다. 단기 안도와 구조 회복을 구분해 추적한다.",
            "non_gating_footer": "[NON_GATING] 완화 해석은 매수/매도 지시가 아니다.",
        },
    ]

    return {
        "schema": "logos_ontology_mapping_v1",
        "generated_at_utc": _now(),
        "source_refs": {
            "registry_63779_json": "docs/final/artifacts/logos_63779_registry_v1_latest.json",
            "morphology_registry_json": "docs/final/artifacts/logos_morphology_registry_v1_latest.json",
        },
        "observation": {
            "chaos_score": round(_clip01(chaos), 6),
            "order_score": round(_clip01(order), 6),
            "tension_score": round(tension, 6),
            "similarity_0_1": round(_clip01(similarity), 6),
            "cohesion_ratio": round(max(0.0, cohesion_ratio), 6),
            "cohesion_band": cohesion_band,
            "phase_label": phase_label,
            "regime": regime,
        },
        "entities": {
            "numeric_symbols": numeric_symbols,
            "morphology_roots": roots,
            "atoms": atoms,
        },
        "relations": relations,
        "render_templates": templates,
        "guardrails": {
            "non_gating_only": True,
            "price_mapping_forbidden": True,
            "execution_trigger_allowed": False,
            "banned_phrases": [
                "무조건 상승",
                "무조건 하락",
                "100% 보장",
            ],
        },
        "falsification_global": [
            "observation.tension_score < 0.3 for 3 consecutive updates",
            "source registry timestamps stale > 72h",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-63779-json", type=Path, default=DEFAULT_63779)
    ap.add_argument("--morphology-registry-json", type=Path, default=DEFAULT_MORPH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    reg63779_path = args.registry_63779_json if args.registry_63779_json.is_absolute() else ROOT / args.registry_63779_json
    reg_morph_path = args.morphology_registry_json if args.morphology_registry_json.is_absolute() else ROOT / args.morphology_registry_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not reg63779_path.is_file():
        raise SystemExit(f"Missing --registry-63779-json: {reg63779_path}")
    if not reg_morph_path.is_file():
        raise SystemExit(f"Missing --morphology-registry-json: {reg_morph_path}")

    reg63779 = _read_json(reg63779_path)
    reg_morph = _read_json(reg_morph_path)
    payload = build_registry(reg63779, reg_morph)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "schema": payload["schema"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
