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
SIGNOFF = ROOT / "docs" / "final" / "artifacts" / "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"
FACTCHECK = ROOT / "docs" / "final" / "artifacts" / "lg_hs_before_after_factcheck_v1_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "lg_hs_compression_discipline_deck_v1_latest.md"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "lg_hs_compression_discipline_deck_v1_latest.json"
OUT_SPEAKER = ROOT / "docs" / "final" / "artifacts" / "lg_hs_ir_moat_speaker_pack_v1_latest.md"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.1f}%"


def _shard_bullets(factcheck: dict[str, Any], *, global_saving: float | None) -> list[str]:
    rows = factcheck.get("frozen_bench_shard_jaccard") or []
    saving_line = (
        f"40-case frozen bench — **token saving is global only** ({_pct(global_saving)}); shard rows are Jaccard only."
        if isinstance(global_saving, (int, float))
        else "40-case frozen bench — **token saving is global only**; shard rows are Jaccard only."
    )
    bullets = [
        saving_line,
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
    bench_floor = active.get("bench_saving_floor_min")
    bench_floor_ok = active.get("bench_saving_floor_ok")
    saving = active.get("global_token_saving_rate")
    jaccard = active.get("avg_reconstruction_fidelity_jaccard")
    policy_ok = active.get("ultra_saving_policy_ok")
    signoff = _read(SIGNOFF) if SIGNOFF.is_file() else {}
    variant_id = signoff.get("selected_variant_id")
    allowlist = None
    rc = signoff.get("selected_run_config")
    if isinstance(rc, dict):
        allowlist = rc.get("domain_relaxed_max_saving_case_allowlist")
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

    policy_line = (
        f"Policy floor **{floor}** · `ultra_saving_policy_ok` **{policy_ok}** (aligned with RQ-016 bench when promoted)."
        if policy_ok
        else f"RQ-016 bench floor **{bench_floor}** · bench_floor_ok **{bench_floor_ok}** (policy floor **{floor}** · policy_ok **{policy_ok}**)."
    )
    slide3_bullets: list[str] = [
        policy_line,
        f"벤치 전역 절감 **{_pct(saving if isinstance(saving, (int, float)) else None)}** (40건, frozen KPI · Track A active)",
        f"평균 Jaccard **{jaccard:.3f}**" if isinstance(jaccard, (int, float)) else "평균 Jaccard —",
    ]
    if variant_id:
        slide3_bullets.append(
            f"승격 프로필 **`{variant_id}`** — ssot cap 0.45 on allowlist only (no global pin)."
        )
    else:
        slide3_bullets.append("승격 프로필 — see promotion signoff artifact.")
    if isinstance(allowlist, list) and allowlist:
        slide3_bullets.append(f"Allowlist cases: {', '.join(allowlist)}.")
    slide3_bullets.append("Jaccard = 단어 겹침 프록시; 의미 %·BOM 절감 단정 금지.")

    saving_pct = _pct(saving if isinstance(saving, (int, float)) else None)
    jaccard_str = f"{jaccard:.3f}" if isinstance(jaccard, (int, float)) else "—"

    moat_slide_bullets = [
        "**질문 방어:** “단어장 만들면 끝 아니냐?” → 연료(41k) + 라우팅(JSON) + 동결 벤치 + 제어층(22장) 조립.",
        "| 축 | LLM 확률 압축 | MKM 결정론 (Track A 동결) |",
        "| 엔진 | LLM/벡터로 중요 토큰 **확률 선택** | **41,775** lookup + **키워드→샤드 1개** + 고정 압축 엔진 |",
        "| 재현·비용 | 모델/API에 따라 변동 | 동일 `run_config` → JSON 리포트 재현; **LLM 추론 없음** |",
        f"| 동결 KPI | 벤더별 상이 | 40건 벤치 · 절감 **{saving_pct}** · Jaccard **{jaccard_str}** · `apply_gematria_4d_bridge_policy: false` |",
        "| 제어 | 요약·절감 중심인 경우 많음 | **WATCH/HOLD** = 22장 실행 게이트 (**≠** 7장 floor **0.47**) |",
        "각주: 0.47 = 절감 하한; WATCH/HOLD = 실행 전 차단(가전·22장).",
    ]

    plugin_slide_bullets = [
        "**Plug-in scalability:** OS 커널처럼 **41k 글로벌 연료 고정** + 산업별 **`zone_*.json` 샤드 팩** 플러그인.",
        "41k(Logos 원어 Export)에 없는 B2B 용어 → 샤드 `must_keep_hard_terms` (예: `zone_f_code`, `zone_a_scm`, **`zone_g_health`**) — **not** `zone_c_health`.",
        "런타임: **41k lookup 항상 ON** + 라우터가 `routing_keywords` 점수로 **최적 샤드 1개** 선택 (`scripts/core/domain_router.py`) — 통짜 사전 스왑 ❌.",
        "혼합 도메인 문서: **41k 공통층 + 1차 샤드**; multi-shard union = **로드맵**(Track A 동결은 single-route).",
        "vs LoRA/거대 교체 사전: **KB급 JSON 팩** — **런타임 파인튜닝·가중치 스왑 없음** (Export·큐레이션 비용은 별도).",
    ]

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
            "bullets": slide3_bullets,
            "evidence": [
                "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json",
                "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
            ],
        },
        {
            "n": 4,
            "title": "Moat — LLM 확률 압축 vs MKM 결정론 (Track A)",
            "bullets": moat_slide_bullets,
            "evidence": [
                "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
                "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
            ],
        },
        {
            "n": 5,
            "title": "Plug-in scalability — 41k + zone JSON 팩",
            "bullets": plugin_slide_bullets,
            "evidence": [
                "codebook/shards/zone_*.json",
                "scripts/core/domain_router.py",
                "scripts/core/master_codebook_lexicon_v1_bridge.py",
            ],
        },
        {
            "n": 6,
            "title": "Shard Jaccard (frozen bench — not per-shard saving)",
            "bullets": _shard_bullets(
                factcheck,
                global_saving=saving if isinstance(saving, (int, float)) else None,
            )
            if factcheck
            else ["Run `build_lg_hs_before_after_factcheck_v1.py` first."],
            "evidence": [
                "docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json",
                "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            ],
        },
        {
            "n": 7,
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
            "n": 8,
            "title": "Kill-Matrix (대외 금지)",
            "bullets": [
                "환각 제거 · 리콜 0% · Zero-Liability",
                "7,680 하드웨어 스윕(레포 SSOT 없으면)",
                "하루 만에 자동차/로봇 이식 · 8.2ms(아티팩트 없으면)",
                "MMLU 점수만으로 양산 승인",
                "학습 비용 0원 · 멀티 샤드 동시 활성화 · zone_c_health · Jaccard 0.899",
            ],
        },
        {
            "n": 9,
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
            "학습 비용 0원",
            "메모리 오버헤드 0",
            "무한대 도메인",
            "Jaccard 0.899",
            "도메인별 훈련 모델",
            "멀티 샤드 동시 활성화",
            "zone_c_health",
            "4D 끄니까 47%",
            "어떤 텍스트든 보장",
        ],
        "moat_speaker_pack": "docs/final/artifacts/lg_hs_ir_moat_speaker_pack_v1_latest.md",
        "factcheck_pointer": "docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.md",
        "pointers": {
            "persuasion_module": "docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md",
            "executive_summary": "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
            "track_c": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.1.2",
        },
    }

    lines = [
        "# LG HS — Compression discipline deck outline (v1.1 · 9 slides)",
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
            if b:
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
            "Moat slides 4–5 full scripts: `lg_hs_ir_moat_speaker_pack_v1_latest.md`.",
            "",
        ]
    )

    speaker_lines = [
        "# LG HS IR — Moat speaker pack (v1)",
        "",
        "**Status:** `[DRAFT]` · Track A only · B-track/`[HYPO]`/실매매 격리.",
        "",
        f"**Generated:** {doc['generated_at_utc']}",
        "",
        f"**Frozen bench (40 cases):** saving **{saving_pct}** · avg Jaccard **{jaccard_str}** · lexicon ON · 4D bridge policy OFF.",
        "",
        "---",
        "",
        "## Slide 4 — LLM vs MKM (45초)",
        "",
        "> 시장에는 LLM으로 텍스트를 줄이는 화려한 스택이 많습니다. 엔터프라이즈 B2B에서는 매번 결과가 널뛰는 확률적 마법을 양산 기본값으로 쓰기 어렵습니다.",
        "> 우리는 Logos 원어에서 Export한 **41,775종 전역 렉시콘**을 lookup하고, **키워드 라우터가 최적 JSON 샤드 1개**의 must_keep을 더한 뒤, **동결 40건 벤치**에서 **약 "
        f"{saving_pct} 절감·Jaccard {jaccard_str}**를 JSON으로 재현합니다. 상용 동결은 **4D bridge policy OFF**입니다.",
        "> **0.47**은 7장 절감 하한이고, **WATCH/HOLD**는 22장 실행 전 제어층입니다 — 한 문장에 섞지 않습니다.",
        "",
        "## Slide 5 — Plug-in scalability (45초)",
        "",
        "> 도메인 확장마다 LoRA·파인튜닝을 하지 않습니다. **41k 글로벌 뼈대는 고정**하고, IT·SCM·헬스 등은 **`zone_*.json` KB급 팩**을 플러그인합니다.",
        "> 런타임은 **41k lookup 항상 ON** + **키워드 점수로 샤드 1개** — 통짜 사전 스왑이 아닙니다. 혼합 문서는 **41k 공통층 + 최적 샤드**이며, multi-shard union은 **로드맵**입니다.",
        "",
        "## Q&A — “단어장이면 끝 아니냐?” (20초)",
        "",
        "> 단어장 아이디어는 흔합니다. 우리 해자는 **Export 연료 + 샤드 라우팅 + 동결 AB + 제어 포장**의 **시스템 조립**입니다.",
        "",
        "## Q&A — “도메인마다 재학습?” (20초)",
        "",
        "> **런타임 재학습 없음.** 새 산업은 **`zone_*.json` 팩 추가**로 확장합니다. 의료 팩 파일명은 **`zone_g_health`** 입니다.",
        "",
        "---",
        "",
        "## Kill-Matrix (이 팩에서도 금지)",
        "",
        "- 학습 비용 0원 · 메모리 0 · 무한대 도메인 · Jaccard 0.899",
        "- 멀티 샤드 3개 동시 활성화 (Track A 미구현)",
        "- `zone_c_health` · 도메인별 훈련 ML 모델",
        "",
    ]

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines), encoding="utf-8")
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_SPEAKER.write_text("\n".join(speaker_lines), encoding="utf-8")
    print(json.dumps({"out_md": str(args.out_md), "out_json": str(args.out_json), "slides": len(slides)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
