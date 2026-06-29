#!/usr/bin/env python3
"""MS/제안서용 external validation evidence pack — main headline SSOT links only."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "external_validation_ms_evidence_pack_v1_latest"
MINIMAL_MANIFEST = ROOT / "reports/external_validation_minimal_pack_v1_latest/manifest.json"

BUNDLE_REQUIRED = [
    "reports/external_validation_2week_closure_v1_latest.json",
    "reports/external_validation_gate_review_memo_v1_latest.json",
    "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json",
    "reports/external_validation_d6_independent_rehearsal_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.md",
    "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.md",
    "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json",
    "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
    "reports/external_validation_minimal_pack_v1_latest/manifest.json",
    "docs/final/artifacts/pointerguard_ops_readiness_latest.json",
]
BUNDLE_OPTIONAL = [
    "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-live-v1_v1_latest.json",
    "reports/wtt_compression_bridge_export_v1_latest.json",
]

POINTER_ONLY = [
    "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
    "docs/final/artifacts/external_validation_2week_execution_plan_v1_latest.md",
    "reports/edge_encoder_air_gap_bundle_v1_latest/",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct_from_poc(path: Path) -> str | None:
    doc = _load_json(path)
    agg = doc.get("aggregate") or {}
    raw = agg.get("mean_token_saving_rate_proxy")
    if raw is None:
        return None
    return f"{float(raw) * 100:.1f}%"


def _paste_lines(signoff: dict, closure: dict) -> str:
    send_gate = signoff.get("send_gate", closure.get("send_gate", "HOLD"))
    ready = signoff.get("ready_for_external_send", closure.get("ready_for_external_send", False))
    readiness = _load_json(ROOT / "docs/final/artifacts/pointerguard_ops_readiness_latest.json").get(
        "all_ok", closure.get("week2", {}).get("D10", {}).get("readiness_all_ok", False)
    )
    bodyonly_poc = ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json"
    live_poc = ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-live-v1_v1_latest.json"
    bodyonly_pct = _pct_from_poc(bodyonly_poc) or "~20.4%"
    live_pct = _pct_from_poc(live_poc)
    lines = [
        "MS/제안서용 헤드라인·증거 링크 (main SSOT만 · aux 절감률 재실행 불필요)",
        "",
        "[게이트]",
        f"send_gate: {send_gate}",
        f"ready_for_external_send: {ready}",
        f"readiness_all_ok: {readiness} (인프라 스모크·유료 API는 별도)",
        "근거: docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json",
        "",
        "[헤드라인 — 반드시 분리 표기 (FAIL-COMP-004)]",
        f"압축 고객 PoC raw 절감 (bodyonly SSOT): {bodyonly_pct}",
        "  → reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json",
        "  → docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
        *((
            [
                f"압축 live 마스킹 코퍼스 (별도·헤드라인 합산 금지): {live_pct}",
                "  → reports/customer_compression_stateless_poc_wtt-premium-cs-customer-live-v1_v1_latest.json",
            ]
            if live_pct
            else []
        )),
        "Edge coord wire proxy: ~156 tokens (압축 %와 합산·혼용 금지)",
        "  → docs/final/artifacts/edge_encoder_spec_v1_latest.json",
        "",
        "[D6 재현 — 절차·게이트 일치만; 절감률 SSOT 아님]",
        "reports/external_validation_d6_independent_rehearsal_v1_latest.json",
        "",
        "[입증 패키지 폴더]",
        "reports/external_validation_minimal_pack_v1_latest/",
        "reports/external_validation_ms_evidence_pack_v1_latest/",
        "",
        "[상용·벤치 트래커 (main)]",
        "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        "",
        "[재현]",
        "py scripts/build_external_validation_ms_evidence_pack_v1.py",
    ]
    return "\n".join(lines) + "\n"


def _one_pager_ko(signoff: dict, closure: dict, tech_brief: str) -> str:
    send_gate = signoff.get("send_gate", closure.get("send_gate", "HOLD"))
    ready = signoff.get("ready_for_external_send", closure.get("ready_for_external_send", False))
    readiness = _load_json(ROOT / "docs/final/artifacts/pointerguard_ops_readiness_latest.json").get(
        "all_ok", closure.get("week2", {}).get("D10", {}).get("readiness_all_ok", False)
    )
    bodyonly_pct = _pct_from_poc(
        ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json"
    ) or "약 20.4%"
    live_pct = _pct_from_poc(
        ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-live-v1_v1_latest.json"
    )
    tech_snip = ""
    for line in tech_brief.splitlines():
        if line.strip().startswith("- "):
            tech_snip = line.strip()[2:].strip()
            break
    return f"""[MS/제안서 1페이지 초안 — 내부 붙여넣기용 · research_only]

■ 한 줄 가치
하이브리드 B2B 공급망형 토큰 압축·Edge 전처리 — 온프레미/공공 중견 PoC 근거 패키지 동봉.

■ 게이트 (Fact-Lock)
- send_gate: {send_gate} · ready_for_external_send: {ready}
- readiness_all_ok: {readiness} (nginx·공개 바인딩·유료 API는 별도 human/infra)
- 법무·운영 서명: docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json

■ 헤드라인 (반드시 분리 — FAIL-COMP-004)
1) 고객 PoC raw 절감 (bodyonly SSOT): {bodyonly_pct} (Track A ~47%와 혼용 금지)
{f"2) live 마스킹 코퍼스 (별도): {live_pct} — 헤드라인 합산 금지" if live_pct else ""}
3) Edge coord wire proxy: 약 156 tokens (압축 %와 합산·단일 헤드라인 금지)
※ aux D6 절감률 재벤치 불필요 — 절차·게이트 재현만 입증.

■ 범위
- In: 중견·공공 온프레미, Edge SDK 전처리, 미터링 PoC
- Out: 마스터 코드북 OSS, 초대규모 학습, 실매매·Track A 자동 승격

■ 외부 검증 요약
- 2주 클로저 + D6 독립 리허설 7/7 · gate_match
- 증거 번들: reports/external_validation_minimal_pack_v1_latest/
- MS 전용 팩: reports/external_validation_ms_evidence_pack_v1_latest/

■ 기술 한 줄
{tech_snip or "PointerGuard + stateless compression API stub; main SSOT metrics only."}

■ 다음 (제안서 본문에 넣지 말 것)
- VPS nginx 배포·open-bench HTML 바인딩 = Tier 3 human
- 유료 청구 API 해제 = counsel + readiness_all_ok 별도

[재현] py scripts/build_external_validation_ms_evidence_pack_v1.py
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    missing_optional: list[str] = []
    for rel in BUNDLE_REQUIRED:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f"missing: {src.relative_to(ROOT)}")
        dst = OUT / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "bundled": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "tier": "required",
            }
        )
    for rel in BUNDLE_OPTIONAL:
        src = ROOT / rel
        if not src.is_file():
            missing_optional.append(rel)
            continue
        dst = OUT / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "bundled": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "tier": "optional",
            }
        )

    signoff = _load_json(ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json")
    closure = _load_json(ROOT / "reports/external_validation_2week_closure_v1_latest.json")
    minimal = _load_json(MINIMAL_MANIFEST)

    paste_path = OUT / "ms_proposal_headline_links_v1.txt"
    paste_path.write_text(_paste_lines(signoff, closure), encoding="utf-8")

    tech_md_path = ROOT / "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.md"
    tech_text = tech_md_path.read_text(encoding="utf-8") if tech_md_path.is_file() else ""
    one_pager_path = OUT / "ms_proposal_one_pager_ko_v1.txt"
    one_pager_path.write_text(_one_pager_ko(signoff, closure, tech_text), encoding="utf-8")

    manifest = {
        "schema": "external_validation_ms_evidence_pack_v1",
        "generated_at_utc": _utc_now(),
        "lane": "ms_proposal",
        "disclaimer": "internal_only",
        "send_gate": signoff.get("send_gate", minimal.get("send_gate", "HOLD")),
        "ready_for_external_send": bool(
            signoff.get("ready_for_external_send", minimal.get("ready_for_external_send", False))
        ),
        "aux_savings_rate_required": False,
        "headline_ssot_main_only": [
            "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json",
            "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
            "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        ],
        "fail_comp_004": "Never merge compression ~20.4% and edge ~156 tok in one headline.",
        "paste_ready": str(paste_path.relative_to(ROOT)).replace("\\", "/"),
        "one_pager_ko": str(one_pager_path.relative_to(ROOT)).replace("\\", "/"),
        "minimal_pack_pointer": "reports/external_validation_minimal_pack_v1_latest/manifest.json",
        "closure_pointer": "reports/external_validation_2week_closure_v1_latest.json",
        "bundled_files": copied,
        "missing_optional": missing_optional,
        "pointer_only": POINTER_ONLY,
        "reproduce": "py scripts/build_external_validation_ms_evidence_pack_v1.py",
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT.relative_to(ROOT)),
                "paste": manifest["paste_ready"],
                "file_count": len(copied) + 2,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
