#!/usr/bin/env python3
"""One-page JSON digest of comp_atom05 profile matrix (B-track, no active writes)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_sweep_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not MATRIX.is_file():
        print(f"missing {MATRIX}", file=sys.stderr)
        return 1

    doc = json.loads(MATRIX.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for block in doc.get("matrices") or []:
        label = block.get("bench_label")
        for cell in block.get("cells") or []:
            m = cell.get("metrics") or {}
            rows.append(
                {
                    "bench": label,
                    "cell_id": cell.get("cell_id"),
                    "saving": m.get("global_token_saving_rate"),
                    "jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
                    "bridge": m.get("apply_gematria_4d_bridge_policy"),
                    "wire": cell.get("graph_wire_selective_bridge"),
                }
            )

    economy = next((r for r in rows if r["cell_id"] == "economy" and r["bench"] == "full_v2_40"), {})
    wire = next((r for r in rows if r["cell_id"] == "economy_plus_wire" and r["bench"] == "full_v2_40"), {})
    fidelity = next((r for r in rows if r["cell_id"] == "fidelity" and r["bench"] == "full_v2_40"), {})
    fidelity_wire = next(
        (r for r in rows if r["cell_id"] == "fidelity_plus_wire" and r["bench"] == "full_v2_40"),
        {},
    )

    brief = {
        "schema": "comp_atom05_profile_matrix_brief_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_anchor": {
            "cell": "full_v2_40/economy",
            "saving": economy.get("saving"),
            "jaccard": economy.get("jaccard"),
            "bridge": economy.get("bridge"),
        },
        "wire_selective_delta_vs_economy": {
            "saving_pp": (wire.get("saving") or 0) - (economy.get("saving") or 0),
            "jaccard_pp": (wire.get("jaccard") or 0) - (economy.get("jaccard") or 0),
        },
        "headline": (
            "Track A frozen at economy ~47.5% bridge OFF; wire_selective adds small Jaccard "
            "at ~0.4pp saving cost on full_v2_40 — B-track only."
        ),
        "do_not_promote": [
            "fidelity bridge ON (~32% saving) without human AB + sign-off",
            "claim single API call always equals bench 47.1% / 0.897 aggregate",
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json without human",
            "genesis pointer_primary as Track A default (0/40 strict on V2 bench)",
        ],
        "v2_draft_contract": {
            "openapi": "docs/final/openapi_token_compression_v2_draft.yaml",
            "stub": "scripts/compression_token_api_v2_stub.py",
            "profile_module": "scripts/compression_profile_v1.py",
            "status": "0.1.0-draft — not Track A commercial sign-off",
        },
        "profile_presets": {
            "track_a_frozen": {
                "compression_profile": "economy",
                "graph_wire_selective_bridge": False,
                "bench_headline": "47.5% saving / Jaccard 0.890 (40-case full_v2_40)",
                "active_report": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            },
            "btrack_recommended_v2": {
                "compression_profile": "economy",
                "graph_wire_selective_bridge": True,
                "emit_semantic_pointer": True,
                "bench_headline": "47.1% saving / Jaccard 0.897 (40-case aggregate; per-text bridge_boost varies)",
                "evidence": "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_sweep_v1.json",
            },
            "fidelity_requires_human": {
                "compression_profile": "fidelity",
                "graph_wire_selective_bridge": False,
                "bench_headline": "32.2% saving / Jaccard 0.967",
                "note": "wire ON adds no delta when global bridge already ON",
            },
        },
        "operator_guide_ko": {
            "title": "v2 draft — 4-Cell 프로필·Wire 함정 예방 (연동팀용)",
            "four_cell_analogy": "자동차 4기어: economy=연비, fidelity=스포츠, wire=GPS가 가파른 구간에서만 bridge_boost",
            "cells_full_v2_40": [
                {
                    "cell": "economy",
                    "saving_pct": round((economy.get("saving") or 0) * 100, 2),
                    "jaccard": economy.get("jaccard"),
                    "wire": False,
                    "role": "Track A 본선 동결 기본값",
                },
                {
                    "cell": "economy_plus_wire",
                    "saving_pct": round((wire.get("saving") or 0) * 100, 2),
                    "jaccard": wire.get("jaccard"),
                    "wire": True,
                    "role": "B-track/v2 draft 권장 하이브리드 (GraphRAG 라우팅 + 선택 bridge_boost, must_keep 아님)",
                },
                {
                    "cell": "fidelity",
                    "saving_pct": round((fidelity.get("saving") or 0) * 100, 2),
                    "jaccard": fidelity.get("jaccard"),
                    "wire": bool(fidelity.get("wire")),
                    "role": "고정확·고비용 — human AB + sign-off 전제",
                },
                {
                    "cell": "fidelity_plus_wire",
                    "saving_pct": round((fidelity_wire.get("saving") or 0) * 100, 2),
                    "jaccard": fidelity_wire.get("jaccard"),
                    "wire": bool(fidelity_wire.get("wire")),
                    "role": "fidelity와 동일 KPI (Δ=0) — wire 중복",
                },
            ],
            "pitfalls": [
                "벤치 40건 평균(47.1%/0.897)을 단일 POST 응답에 그대로 기대하지 말 것 — bridge_boost는 케이스·텍스트 의존",
                "graph_wire_selective_bridge=true여도 40건 중 9건만 bridge_boost (score≥0.35); 나머지는 economy와 동일",
                "Wire는 must_keep에 그래프 단어를 붙여넣지 않음 — semantic_pointer.graph_wire_influence_v1 경로",
                "Track A active를 economy+wire로 자동 승격하지 말 것 — 본선은 economy bridge OFF 고정",
                "fidelity 프로필을 상용 기본값으로 두지 말 것 — 절감률 32%대로 하락",
                "GraphRAG 미로드·브리지 메타 탈락 경로에서는 wire=true도 no-op(economy와 동일) — OpenAPI default false 유지",
                "apply_multilens_ultra_compression_track_a_promotion_v1.py로 wire KPI를 active에 덮어쓰기 금지",
            ],
            "integration_checklist": [
                "POST /v2/compress 기본: compression_profile=economy, graph_wire_selective_bridge=false",
                "B-track 실험만: graph_wire_selective_bridge=true + emit_semantic_pointer=true",
                "응답 integrity_flags.graph_wire_bridge_boost / residual_meta.semantic_pointer 확인",
                "본선 KPI 주장은 Track A economy 벤치(47.5/0.890)와 분리 서술",
                "1단계 승격 스코프: comp_v2_wire_staging_promotion_scope_v1.json (staging only)",
            ],
        },
        "matrix_rows": rows,
    }
    OUT.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
