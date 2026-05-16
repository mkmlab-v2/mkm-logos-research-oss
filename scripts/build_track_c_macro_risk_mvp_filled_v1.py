#!/usr/bin/env python3
"""Fill Track C 2026 H2 macro risk MVP §2 and B2B one-pager from latest JSON artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        # utf-8-sig: PowerShell / some editors write BOM-prefixed JSON
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _fmt_ts(raw: Any) -> str:
    if raw is None:
        return "(missing)"
    s = str(raw).strip()
    return s if s else "(missing)"


def _top_insight_keys(insight_7: dict[str, Any], k: int = 4) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    for key, val in insight_7.items():
        try:
            items.append((key, float(val)))
        except (TypeError, ValueError):
            continue
    items.sort(key=lambda x: -x[1])
    return items[:k]


def _exec_summary_md(
    *,
    generated_at: str,
    smoke: dict[str, Any] | None,
    n8n: dict[str, Any] | None,
    health: dict[str, Any] | None,
    weekly: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append(f"_본 절은 `build_track_c_macro_risk_mvp_filled_v1.py`가 디스크 아티팩트에서 생성했습니다. 생성 시각(UTC): `{generated_at}`._")
    lines.append("")
    lines.append("**Core theory protection:** 본 요약은 의사결정 보조 산출물만 포함하며, 핵심 산식·가중치·중간 계산 기여도는 비공개 운영 원칙(`TRACK_C` §9A)을 따른다.")
    lines.append("")
    lines.append("**보고 기간:** 2026-07-01 ~ 2026-12-31 — Track C §3.8 MVP 범위(시나리오·경보 브리프). 특정 시점 스냅샷 수치는 인용한 JSON 기준.")
    lines.append("")

    if smoke:
        ds = _fmt_ts(smoke.get("decision_state"))
        rw = _fmt_ts(smoke.get("risk_warning_level"))
        cb = _fmt_ts(smoke.get("confidence_band"))
        posture = _fmt_ts(smoke.get("recommended_operator_posture"))
        ts = _fmt_ts(smoke.get("timestamp_utc"))
        prim = None
        rc = smoke.get("regime_context")
        if isinstance(rc, dict):
            prim = rc.get("primary_regime_id")
        lines.append(
            f"**한 줄 포즈(스모크 스냅샷):** 구조화 경보 `decision_state={ds}`, "
            f"`risk_warning_level={rw}`, `confidence_band={cb}`, 운영자 포즈 `{posture}` — "
            "매매 지시·자동 실행 아님 (`macro_risk_warning_api_smoke_latest.json`, "
            f"`timestamp_utc={ts}`)."
        )
        if prim:
            lines.append(f"- 레짐 맥락(스모크): `primary_regime_id={prim}`")
        lines.append("")
        insight = smoke.get("insight_7")
        if isinstance(insight, dict):
            top = _top_insight_keys(insight, 5)
            rows = []
            for name, val in top:
                rows.append(f"| `{name}` | {val:.4f} |")
            lines.append("| 스모크 insight_7 축 (상위) | 값 |")
            lines.append("|---|---|")
            lines.extend(rows)
            lines.append("")
    else:
        lines.append(
            "**한 줄 포즈:** `docs/final/artifacts/macro_risk_warning_api_smoke_latest.json` 가 없거나 파싱 실패 — 스모크 재생성 후 갱신."
        )
        lines.append("")

    lines.append("| 블록 | 내용 |")
    lines.append("|------|------|")
    themes = (
        "유동성 스트레스·교차자산 괴리·변동성 레짐·테일 압력 등 — 위 스모크 `insight_7` 수치 인용"
        if smoke and isinstance(smoke.get("insight_7"), dict)
        else "아티팩트 부재 시 수동 보강"
    )
    lines.append(f"| 상위 리스크 테마 (≤5) | {themes} |")

    if smoke:
        lines.append(
            f"| 현재 경보 수준(스모크) | `decision_state={smoke.get('decision_state')}`, "
            f"`risk_warning_level={smoke.get('risk_warning_level')}` — 운영 라벨은 정책 바인딩 JSON과 정합 확인 |"
        )
    else:
        lines.append("| 현재 경보 수준 | (스모크 없음) |")

    evidence = []
    evidence.append("`docs/final/artifacts/macro_risk_warning_api_smoke_latest.json`")
    evidence.append("`reports/macro_risk_n8n_daily_check_latest.json`")
    evidence.append("`docs/final/artifacts/pre_news_shadow_task_health_latest.json`")
    evidence.append("`docs/final/artifacts/pre_news_shadow_weekly_report_latest.json`")
    lines.append(f"| 근거 링크 | {', '.join(evidence)} |")

    uncert: list[str] = []
    if n8n:
        ov = _fmt_ts(n8n.get("overall"))
        nh = None
        ch = n8n.get("checks")
        if isinstance(ch, dict):
            nh = ch.get("n8n_health")
        uncert.append(f"n8n 일일 점검 `overall={ov}`")
        if nh:
            uncert.append(f"`n8n_health={nh}`")
        uncert.append(f"스냅샷 시각 `{_fmt_ts(n8n.get('ts_utc'))}`")
    else:
        uncert.append("`macro_risk_n8n_daily_check_latest.json` 없음")
    if health:
        uncert.append(
            f"Pre-News 작업 건강도 `healthy={health.get('healthy')}`, `result_category={health.get('result_category')}` "
            f"(`generated_at_utc={health.get('generated_at_utc')}`)"
        )
    if weekly:
        uncert.append(
            f"주간 리포트 창 `{weekly.get('window_days')}d`, 창 내 실행 `{weekly.get('runs_in_window')}`회 "
            f"(`generated_at_utc={weekly.get('generated_at_utc')}`)"
        )
    uncert.append("과거 스냅샷은 현재 시장과 다를 수 있음; 법무 검토 전 대외 확정 금지.")

    lines.append(f"| 불확실성 | {'; '.join(uncert)} |")

    next_refresh = "일일 체인·스케줄 실행 시 (운영 캘린더와 정합)"
    if health and health.get("next_run_time"):
        next_refresh += f"; Pre-News 작업 `next_run_time={health.get('next_run_time')}` 참고"
    lines.append(f"| 다음 갱신 | {next_refresh} |")

    lines.append("")
    lines.append(
        "**금지:** 특정 자산 매수·매도 지시, 목표가, 성과에 대한 약속."
    )
    return "\n".join(lines)


def _b2b_onepager_md(*, generated_at: str) -> str:
    return f"""# Track C — 기업용 매크로 조기 경보 구독 (세일즈 시트 초안)

- **generated_at_utc:** `{generated_at}`
- **aligned_with:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.8 · §9 · §9A · §10 항목 2
- **status:** `DRAFT_AUTO`

## 포함 (구독 범위 예시)

- 분기·월간 **거시·레짐 시나리오 브리프** (PDF / 공유 링크)
- **이메일·(옵션) 대시보드** 알림 — 구조화 경보·운영자 포즈 표기 (매매 지시 아님)
- **읽기 전용 경보 API** 는 별도 계약 — 계약 SSOT `docs/final/openapi_macro_risk_warning_api_v1.yaml`

## 제외 (명시)

- 투자 자문, 특정 자산에 대한 매매 지시·목표가, 성과에 대한 약속
- 고객 거래소 API·실키를 당사가 저장·중계하지 않음 (`TRACK_C` §3.8 운영 경계)
- 핵심이론 산식·가중치·중간 피처 기여도·튜닝 규칙 비공개 (`TRACK_C` §9A)

## 신뢰·거버넌스 KPI (요약)

- 재현 가능한 **JSON·로그 경로**를 납기물에 병기 (Fact-Lock)
- 월간 **투명성** 리포트(계약 범위 내): 경보 적시성·정시 납기 등 `TRACK_C` §7과 정합 가능 영역만
- 감사 추적: 고객·시점별 조회 기록(append-only) 및 유출 추적 워터마킹 적용

## 대외 비교 포지셔닝 (Fact-Lock)

- WRING류는 기초모델 내부 표현공간 편향 교정(기초 과학), MKM12 Track C는 운영 파이프라인·정책 바인딩·감사 추적(응용 거버넌스) 전장
- 기술 우열 단정 금지; 상용 문구는 "운영 통제 가능성·감사 가능성" 중심으로 고정
- 모델 내부 개조 없이 API 계약·HITL·로그 증거로 리스크 경보 운영을 검증 가능하게 제공

## Core Theory Protection (Commercial Security Gate, §9A)

- **Model-as-a-Service:** 핵심 엔진은 서버 내부에서만 실행, 대시보드/API는 결과값만 제공
- **응답 최소화:** 점수·사분면·상태 라벨은 제공하되 산식 상세·가중치·중간 계산값은 미제공
- **계약 통제:** NDA, 역공학 금지, 재배포 금지, 파생모델 학습 금지 조항 기본 적용
- **접근 통제:** tenant별 API 키, 권한 분리(RBAC), 엔터프라이즈 옵션(IP allowlist)

## 대외 고정 문구 (§9 English default)

> MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

## Short copy (§9)

- Risk Warning First, Not Trade Advice.
- Token Efficiency + Risk Posture, with Reproducible Evidence.
- Governance-driven, Artifact-backed, Operator-in-the-loop.

## 가격·계약

- 별도 견적·영업 확정 (본 초안은 의향 표시용)
- 기본 라이선스: `decision-support output license` (core formula license 아님)

## 근거 MVP 뼈대

- `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`
"""


def _logos_module_md(
    *,
    generated_at: str,
    bundle: dict[str, Any] | None,
    commander: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append(
        f"_본 절은 `build_track_c_macro_risk_mvp_filled_v1.py`가 Logos 아티팩트에서 생성했습니다. "
        f"UTC `{generated_at}`._"
    )
    lines.append("")
    lines.append(
        "**포지션:** §3.8 매크로 경보 구독의 **프리미엄 모듈** — 고전/철학 코퍼스(Logos) **스트레스 테스트·심층 리스크 내러티브**. "
        "예언·종교·매매 지시 아님. 성경/Logos 렌즈는 **`[NON_GATING]`** — 최종 포즈는 Field(실물 레짐)+운영 게이트."
    )
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|------|-----|")
    if bundle:
        pol = bundle.get("policy") if isinstance(bundle.get("policy"), dict) else {}
        lines.append(
            f"| Logos insight bundle | `generated_at_utc={_fmt_ts(bundle.get('generated_at_utc'))}`, "
            f"`research_only={pol.get('research_only')}`, `non_gating={pol.get('non_gating')}`, "
            f"`degraded={bundle.get('degraded')}` |"
        )
        q = bundle.get("query")
        if isinstance(q, dict) and q.get("query_fingerprint"):
            fp = str(q.get("query_fingerprint"))
            lines.append(f"| Query fingerprint | `{fp[:48]}…` |")
    else:
        lines.append("| Logos insight bundle | `logos_insight_bundle_v1_latest.json` 없음 — `build_logos_insight_bundle_v1.py` |")

    if commander:
        cmd_ts = commander.get("generated_at_utc") or commander.get("ts_utc")
        lines.append(
            f"| Commander deep report | `snapshot_utc={_fmt_ts(cmd_ts)}`, "
            f"`schema={_fmt_ts(commander.get('schema'))}` |"
        )
        summary = commander.get("executive_summary")
        if isinstance(summary, str) and summary.strip():
            short = summary.strip().replace("\n", " ")
            if len(short) > 200:
                short = short[:197] + "…"
            lines.append(f"| Executive summary (excerpt) | {short} |")
    else:
        lines.append(
            "| Commander deep report | `logos_track_b_commander_deep_report_latest.json` 없음 — "
            "`run_logos_track_b_commander_deep_report_v1.py` |"
        )

    lines.append("")
    lines.append(
        "**대외 1-pager:** `docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md` "
        "(재생성: `py scripts/build_track_c_logos_b2b_offer_onepager_v1.py`). "
        "**합본:** `track_c_combined_b2b_offer_onepager_v1_latest.md`."
    )
    lines.append("")
    lines.append("**금지:** “성경이 시장을 예측”, 실시간 신탁, Logos 단독 시그널 상품 포장.")
    return "\n".join(lines)


def _patch_mvp_header_status(text: str, generated_at: str) -> str:
    """Set status line to show last auto-fill time."""
    line_pat = r"^- \*\*status:\*\* `[^`]+` —[^\n]*"
    repl = (
        f"- **status:** `DRAFT_AUTO_FILLED` — 마지막 자동 갱신 UTC `{generated_at}`. "
        "목차·근거 경로 동결; §2 본문은 스크립트가 아티팩트에서 채움."
    )
    out, n = re.subn(line_pat, repl, text, count=1, flags=re.MULTILINE)
    return out if n else text


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill Track C macro risk MVP from artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="Print paths only; do not write files.")
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    smoke_path = root / "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json"
    n8n_path = root / "reports/macro_risk_n8n_daily_check_latest.json"
    health_path = root / "docs/final/artifacts/pre_news_shadow_task_health_latest.json"
    weekly_path = root / "docs/final/artifacts/pre_news_shadow_weekly_report_latest.json"

    smoke = _load_json(smoke_path)
    n8n = _load_json(n8n_path)
    health = _load_json(health_path)
    weekly = _load_json(weekly_path)
    logos_bundle_path = root / "docs/final/artifacts/logos_insight_bundle_v1_latest.json"
    logos_commander_path = root / "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json"
    logos_bundle = _load_json(logos_bundle_path)
    logos_commander = _load_json(logos_commander_path)

    new_section2 = _exec_summary_md(
        generated_at=generated_at,
        smoke=smoke if isinstance(smoke, dict) else None,
        n8n=n8n if isinstance(n8n, dict) else None,
        health=health if isinstance(health, dict) else None,
        weekly=weekly if isinstance(weekly, dict) else None,
    )

    mvp_path = root / "docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md"
    b2b_path = root / "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md"

    if args.dry_run:
        print("Would update:", mvp_path)
        print("Would write:", b2b_path)
        print("--- §2 preview ---")
        print(new_section2)
        return 0

    mark_begin = "<!-- track_c_mvp_section_2_auto_v1 -->"
    mark_end = "<!-- /track_c_mvp_section_2_auto_v1 -->"
    # Non-greedy between unique markers (do not require extra \n before closing tag).
    block_pat = re.compile(
        re.escape(mark_begin) + r"[\s\S]*?" + re.escape(mark_end),
        flags=re.DOTALL,
    )

    text = mvp_path.read_text(encoding="utf-8")
    if not block_pat.search(text):
        print(
            "build_track_c_macro_risk_mvp_filled_v1: markers "
            f"{mark_begin!r} … {mark_end!r} not found in MVP file"
        )
        return 1

    replacement = f"{mark_begin}\n{new_section2}\n{mark_end}"
    new_text = block_pat.sub(replacement, text, count=1)

    logos_begin = "<!-- track_c_mvp_logos_module_auto_v1 -->"
    logos_end = "<!-- /track_c_mvp_logos_module_auto_v1 -->"
    logos_pat = re.compile(
        re.escape(logos_begin) + r"[\s\S]*?" + re.escape(logos_end),
        flags=re.DOTALL,
    )
    new_logos = _logos_module_md(
        generated_at=generated_at,
        bundle=logos_bundle if isinstance(logos_bundle, dict) else None,
        commander=logos_commander if isinstance(logos_commander, dict) else None,
    )
    if logos_pat.search(new_text):
        new_text = logos_pat.sub(f"{logos_begin}\n{new_logos}\n{logos_end}", new_text, count=1)
    else:
        print(
            "build_track_c_macro_risk_mvp_filled_v1: WARN logos markers not found; "
            "skipped §2b Logos module patch"
        )

    new_text = _patch_mvp_header_status(new_text, generated_at)
    mvp_path.write_text(new_text, encoding="utf-8", newline="\n")

    b2b_path.write_text(_b2b_onepager_md(generated_at=generated_at), encoding="utf-8", newline="\n")

    print(f"Updated {mvp_path}")
    print(f"Wrote {b2b_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
