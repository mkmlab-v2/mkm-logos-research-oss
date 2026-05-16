#!/usr/bin/env python3
"""Build LG HS compression-governance deck outline from frozen artifacts (Fact-Lock)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KPI = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
FACTCHECK = ROOT / "docs" / "final" / "artifacts" / "lg_hs_before_after_factcheck_v1_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "lg_hs_compression_discipline_deck_v1_latest.md"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "lg_hs_compression_discipline_deck_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.1f}%"


def _shard_bullets(factcheck: dict[str, Any]) -> list[str]:
    rows = factcheck.get("frozen_bench_shard_jaccard") or []
    bullets = [
        "40-case frozen bench — **token saving is global only** (~47.1%); shard rows are Jaccard only.",
        "Jaccard = overlap proxy; not semantic meaning %.",
    ]
    for row in rows:
        sid = row.get("shard_id", "")
        n = row.get("case_count")
        avg_j = row.get("avg_jaccard")
        min_j = row.get("min_jaccard")
        if isinstance(avg_j, (int, float)) and isinstance(min_j, (int, float)):
            bullets.append(f"`{sid}` (n={n}): avg **{avg_j:.3f}**, min **{min_j:.3f}**")
    g = factcheck.get("frozen_bench_global") or {}
    if isinstance(g.get("min_reconstruction_fidelity_jaccard"), (int, float)):
        bullets.append(f"Global min Jaccard **{g['min_reconstruction_fidelity_jaccard']:.3f}** (worst case on bench).")
    return bullets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    kpi = _read(KPI)
    active = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}
    floor = active.get("ultra_saving_policy_min")
    saving = active.get("global_token_saving_rate")
    jaccard = active.get("avg_reconstruction_fidelity_jaccard")
    policy_ok = active.get("ultra_saving_policy_ok")
    factcheck = _read(FACTCHECK) if FACTCHECK.is_file() else {}
    if not factcheck and ACTIVE.is_file():
        # Regenerate factcheck if deck runs standalone
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_lg_hs_before_after_factcheck_v1.py")],
            cwd=str(ROOT),
            check=False,
        )
        factcheck = _read(FACTCHECK)

    slides = [
        {
            "n": 1,
            "title": "오프닝 — 제조업 언어",
            "bullets": [
                "우리는 가장 화려한 모델 점수가 아니라, 운영 가능한 AI 디시플린을 제안합니다.",
                "벤치·정책 하한·감사 로그는 동결 아티팩트로 재현합니다.",
                "[DRAFT] 법무·PUBLIC_FACING v1.7 통과 전 대외 배포 금지.",
            ],
        },
        {
            "n": 2,
            "title": "문제 정의 (70%)",
            "bullets": [
                "가전·플랫폼 AI의 리스크: 오작동 전이, 지연 스파이크, 양산 정합성.",
                "벤치만 좋은 모델은 양산 현장에서 방어 불가.",
                "WATCH/HOLD·재질문 정책 = 실행 전 리스크 차단(투자조언 아님).",
            ],
        },
        {
            "n": 3,
            "title": "압축 거버넌스 증거 (조건부 수치)",
            "bullets": [
                f"정책 하한 floor **{floor}** · policy_ok **{policy_ok}**",
                f"벤치 전역 절감 **{_pct(saving if isinstance(saving, (int, float)) else None)}** (40건, frozen KPI)",
                f"평균 Jaccard **{jaccard:.3f}**" if isinstance(jaccard, (int, float)) else "평균 Jaccard —",
                "Jaccard = 단어 겹침 프록시; 의미 %·BOM 절감 단정 금지.",
            ],
            "evidence": [
                "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json",
                "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
            ],
        },
        {
            "n": 4,
            "title": "Shard Jaccard (frozen bench — not per-shard saving)",
            "bullets": _shard_bullets(factcheck) if factcheck else ["Run `build_lg_hs_before_after_factcheck_v1.py` first."],
            "evidence": [
                "docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json",
                "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            ],
        },
        {
            "n": 5,
            "title": "Governance proofs (accurate)",
            "bullets": [
                "Lexicon **41,775** terms — deterministic must_keep join path.",
                "Shadow Auditor: **4** artifact contract pytest passes + frozen KPI scan (not **17/17**).",
                "Full 40-case re-bench: optional `--refresh-bench` (weekly chain), not every nightly default.",
                "RTT: VPS same-host p95 **~665–847 ms** (2026-05-16); loopback conc10 is smoke only — **no ms↔saving causality**.",
            ],
            "evidence": [
                "reports/constitution/btrack_pilot/compression_shadow_auditor_latest.json",
                "docs/final/artifacts/compression_board_ms_correlation_report_v1_latest.json",
            ],
        },
        {
            "n": 6,
            "title": "Kill-Matrix (대외 금지)",
            "bullets": [
                "환각 제거 · 리콜 0% · Zero-Liability",
                "7,680 하드웨어 스윕(레포 SSOT 없으면)",
                "하루 만에 자동차/로봇 이식 · 8.2ms(아티팩트 없으면)",
                "MMLU 점수만으로 양산 승인",
            ],
        },
        {
            "n": 7,
            "title": "클로징 — 다음 단계",
            "bullets": [
                "로컬 벤치 기준선 → 타깃 보드 실측(RQ-017, [HYPO]) → 월간 Go/No-Go.",
                "산출: 코드북·게이트 기준·실측 리포트·운영 가이드.",
                "면책: Not investment advice; bench ≠ production SLA.",
            ],
        },
    ]

    doc = {
        "schema": "lg_hs_compression_discipline_deck_v1",
        "status": "[DRAFT]",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tone_ratio": "70/20/10",
        "slides": slides,
        "forbidden_phrases": [
            "환각 제거",
            "리콜 0%",
            "Zero-Liability",
            "세계 유일",
            "의미 89% 복원",
            "17/17 passed",
            "샤드별 47% 절약",
            "SCM 평균 0.667",
            "Timing 0.910",
            "conc10 = 양산 SLA",
        ],
        "factcheck_pointer": "docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.md",
        "pointers": {
            "persuasion_module": "docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md",
            "executive_summary": "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
            "track_c": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.1.2",
        },
    }

    lines = [
        "# LG HS — Compression discipline deck outline (v1)",
        "",
        "**Status:** `[DRAFT]` — slides only; not legal-approved external send.",
        "",
        f"**Generated:** {doc['generated_at_utc']}",
        "",
        "**Tone:** 70/20/10 · manufacturing language · `lg_hs_persuasion_module_v1_2026-05-08.md`",
        "",
        "---",
        "",
    ]
    for s in slides:
        lines.append(f"## Slide {s['n']}: {s['title']}")
        lines.append("")
        for b in s["bullets"]:
            lines.append(f"- {b}")
        if s.get("evidence"):
            lines.append("")
            lines.append("Evidence:")
            for e in s["evidence"]:
                lines.append(f"- `{e}`")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Speaker note (one line)",
            "",
            "> We sell artifact-bound discipline—not flashiest model scores.",
            "",
        ]
    )

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines), encoding="utf-8")
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out_md": str(args.out_md), "out_json": str(args.out_json), "slides": len(slides)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
