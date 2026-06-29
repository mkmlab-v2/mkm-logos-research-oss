"""Emit compact UI copy bundle for Cosmic Meta-Architecture panel (HYPO · B-track)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT_JSON = ROOT / "docs/final/artifacts/logos_cosmic_meta_architecture_draft_v1_latest.json"
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"
OUT_PATHS = [
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_meta_architecture_ui_v1.json",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/logos_cosmic_meta_architecture_ui_v1.json",
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging/logos_cosmic_meta_architecture_ui_v1.json",
]


def build_ui_bundle() -> dict:
    draft = json.loads(DRAFT_JSON.read_text(encoding="utf-8"))
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    force_rows = []
    for row in lexicon.get("entries", []):
        force_rows.append(
            {
                "force_id": row.get("force_id"),
                "force_label_ko": row.get("force_label_ko"),
                "primitive": row.get("primitive"),
                "kernel_param": row.get("kernel_param"),
                "sasang_label_ko": row.get("sasang_label_ko"),
                "notes_ko": row.get("notes_ko"),
            }
        )
    return {
        "schema": "logos_cosmic_meta_architecture_ui_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "title_ko": "Cosmic Meta-Architecture",
        "badge_ko": "[HYPO] · research_only · NON_GATING",
        "summary_ko": (
            "이기종 도메인(물리·사상·Logos)을 팽창/수축·교환·밀도·여백으로 읽는 B-track 메타 좌표계입니다. "
            "물리·체질·신학 단정이 아니며, 운영 SSOT는 S-L-K-M(gematria_bridge_v1)입니다."
        ),
        "disclaimer_ko": draft.get(
            "disclaimer_ko",
            "[HYPO] 메타-아키텍처 B-track 서사. Track A·live·SEND 금지.",
        ),
        "layers": [
            {
                "id": "kernel",
                "label_ko": "운영 4D (FACT)",
                "body_ko": "S-L-K-M — gematria_bridge_v1. cosmic anchor vector_4d 및 orb draft의 기준 축.",
            },
            {
                "id": "thermo_alias",
                "label_ko": "열역학 별칭 (HYPO · SSOT 아님)",
                "body_ko": "Ei/Pf/Dd/Hc = legacy_thermo_alias. 게마트리아 합에서 기계 유도된 표시용 병렬 표기.",
            },
            {
                "id": "force_lexicon",
                "label_ko": "4대 힘 ↔ primitive (교육용 HYPO)",
                "body_ko": "pedagogical_isomorphism_only — 물리·체질 단정 금지. kernel_alignment 코사인으로 verse별 draft.",
            },
            {
                "id": "regime_transition_valve",
                "label_ko": "상태 전환 밸브 (HYPO · UI 리듬)",
                "body_ko": (
                    "regime_transition_index = K×(1−M)×earth_mediation. "
                    "충돌 시 K↔M 상태 전환 밸브 — 연구·UI 리듬만, Track A·live·SEND 금지."
                ),
            },
        ],
        "force_rows": force_rows,
        "forbidden_ko": [
            "물리 4대 힘 = 사상 체질 (FACT) 단정",
            "Ei/Pf/Dd/Hc를 S-L-K-M 대체 SSOT로 승격",
            "신학·체질·임상 병명 단정",
            "Track A Final Action을 resonance similarity로 확정",
        ],
        "ssot_doc": draft.get("narrative_md"),
        "ssot_json": "docs/final/artifacts/logos_cosmic_meta_architecture_draft_v1_latest.json",
    }


def main() -> int:
    bundle = build_ui_bundle()
    text = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"WROTE: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
