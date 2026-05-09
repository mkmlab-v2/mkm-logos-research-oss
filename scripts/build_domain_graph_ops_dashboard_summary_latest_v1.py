#!/usr/bin/env python3
"""Build domain graph ops dashboard summary latest markdown."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_path = root / "docs" / "final" / "artifacts" / "DOMAIN_GRAPH_OPS_DASHBOARD_SUMMARY_LATEST.md"
    ledger_summary_path = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_ledger_summary_latest.json"
    weekly_report_path = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_weekly_report_latest.json"
    ledger = _read_json(ledger_summary_path)
    weekly = _read_json(weekly_report_path)
    latest_severity = str(ledger.get("latest_severity", "UNKNOWN"))
    latest_review_required = bool(ledger.get("latest_human_review_required", False))
    latest_dispatch_status = str(ledger.get("latest_dispatch_status", "unknown"))
    ledger_updated_at = str(ledger.get("updated_at_utc", "unknown"))
    warning_streak = int(weekly.get("warning_streak", 0) or 0)
    critical_streak = int(weekly.get("critical_streak", 0) or 0)
    weekly_review_required_count = int(weekly.get("review_required_count", 0) or 0)
    threshold_switch_min_rows = int(weekly.get("threshold_switch_min_rows", 14) or 14)
    threshold_switch_readiness = str(weekly.get("readiness_for_threshold_switch", "unknown"))
    threshold_switch_recommendation = str(weekly.get("threshold_switch_recommendation", "unknown"))
    if critical_streak > 0:
        status = "RED"
    elif warning_streak > 0 or latest_review_required:
        status = "YELLOW"
    else:
        status = "GREEN"
    generated_at = _now_utc()

    md = f"""# Domain Graph Ops Dashboard Summary (Latest)

## 메타
- `generated_at_utc`: `{generated_at}`
- `status`: `{status}`
- `source`: `scripts/build_domain_graph_ops_dashboard_summary_latest_v1.py`

## 목적
- 쇼룸/허브/성경 코퍼스 트랙을 분리 운영하면서도, 운영자가 한 장으로 상태를 파악하도록 만든 요약판.
- 기준: `Understand-Anything` 기반 구조 그래프 + 현재 레포 SSOT 경로.

## A) 쇼룸 트랙 (jemaai.cloud)
- **도메인 역할:** 공개 전광판/관측 쇼룸 (실매매 격리)
- **핵심 경로:**
  - `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_board_minimal.html`
  - `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py`
  - `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`
- **체크 포인트:**
  - 공개 필드만 노출되는가 (`public-event.v1`)
  - 실거래/주문/실키 정보 비노출인가
  - 쇼룸 정적 보드 경로가 배포/스모크와 정합인가

## B) 허브 트랙 (jema-ai.com)
- **도메인 역할:** 브랜드 허브 + CTA 분기
- **핵심 경로:**
  - `projects/no1kmedi/src/app/page.tsx`
  - `projects/no1kmedi/marketing-site/public-copy.json`
  - `projects/no1kmedi/src/content/siteCopy.ts`
- **체크 포인트:**
  - `hub_links` 3분기(쇼룸/제품/API)가 살아있는가
  - 쇼룸 UI를 허브에 중복 임베드하지 않았는가
  - 허브 카피가 보안/IP 가드레일 문서와 충돌하지 않는가

## C) 코퍼스/팩트락 트랙 (성경/Global Atom)
- **도메인 역할:** 근거/검증/대외 문구 무결성
- **핵심 경로:**
  - `docs/final/artifacts/global_atom_corpus_profiles_v1.json`
  - `docs/final/artifacts/global_atom_claim_lock_registry_latest.json`
  - `docs/final/artifacts/global_atom_edge_claim_anchor_v1.json`
  - `docs/final/artifacts/global_atom_edge_claim_atom_set_latest.json`
  - `scripts/check_global_atom_claim_lock_v1.py`
  - `scripts/check_global_atom_edge_claim_atom_set_v1.py`
  - `scripts/check_global_atom_corpus_profile_lock_v1.py`
  - `scripts/build_global_atom_corpus_fact_brief_latest_v1.py`
- **체크 포인트:**
  - `corpus_profile_id`가 claim/anchor/atom/onepager 전 구간에서 일치하는가
  - anchor/current/delta 3점 보고가 유지되는가
  - 대외 1문장 가드(프로필+앵커+현재+델타)가 강제되는가

## 운용 상태등급 (신호등)
- **Green:** A/B/C 체크 포인트 전부 통과 + daily chain 성공
- **Yellow:** 기능은 동작하나 한 트랙에서 문구/경로/카피 정합 경고
- **Red:** strict 검증 실패 또는 공개 경로에 금지 정보 노출 가능성

## Chronicle Human Gate (B-track)
- `latest_severity`: `{latest_severity}`
- `human_review_required`: `{str(latest_review_required).lower()}`
- `dispatch_status`: `{latest_dispatch_status}`
- `ledger_updated_at_utc`: `{ledger_updated_at}`
- `weekly_review_required_count`: `{weekly_review_required_count}`
- `warning_streak`: `{warning_streak}`
- `critical_streak`: `{critical_streak}`
- `threshold_switch_min_rows`: `{threshold_switch_min_rows}`
- `threshold_switch_readiness`: `{threshold_switch_readiness}`
- `threshold_switch_recommendation`: `{threshold_switch_recommendation}`

## 오늘의 권장 순서 (운영 10분 루틴)
1. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_claim_lock_daily.ps1`
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1`
3. 쇼룸 스모크(배포 시): `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_showroom_vps_guarded_deploy.ps1`
4. 허브 카피 스키마(변경 시): `projects/no1kmedi/scripts/check-public-copy-schema.mjs`

## 요약 결론
- 쇼룸(`jemaai.cloud`)은 **관측 UI**, 허브(`jema-ai.com`)는 **분기 CTA**, 코퍼스 트랙은 **팩트락 증거 체계**로 역할을 고정한다.
- 세 트랙을 섞지 않고, 각 트랙의 체크 포인트를 독립 통과시키는 것이 운영 안정성의 핵심이다.
"""
    out_path.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "domain_graph_ops_dashboard_build_v1",
                "generated_at_utc": generated_at,
                "output_md": str(out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
