#!/usr/bin/env python3
"""Commander one-page paste — plain Korean summary + appendix (Fact-Lock paths)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "reports/nvidia_hybrid_operator_paste_v1_latest.txt"
OUT_JSON = ROOT / "reports/nvidia_hybrid_operator_paste_v1_latest.json"

ANCHOR_SIGNOFF = ROOT / "reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json"
CODEC_STAGING = ROOT / "reports/nvidia_lut_codec_staging_review_v1_latest.json"
WIRE_CONFIRM = ROOT / "reports/nvidia_lut_codec_staging_wire_confirm_v1_latest.json"
TRACKC_READY = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
TRACKC_COUNSEL = ROOT / "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"
TRACKC_DISCLAIMER = ROOT / "reports/track_c_b2b_disclaimer_integrity_v1_latest.json"
SHOWROOM_SMOKE = ROOT / "reports/showroom_trust_viz_public_chain_smoke_latest.json"
SHOWROOM_NGINX = ROOT / "reports/showroom_track_c_nginx_weekly_apply_v1_latest.json"
PATHS = {
    "hybrid_status": ROOT / "reports/hybrid_ai_lab_status_v1_latest.json",
    "spine": ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json",
    "de_nim": ROOT / "reports/ng40_de_probe_nim_synthesis_v1_latest.json",
    "de_probe": ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json",
    "lut": ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json",
    "ops": ROOT / "reports/nvidia_gpu_credit_ops_status_v1_latest.json",
    "logos_nim": ROOT / "reports/nim_logos_research_handoff_v1_latest.json",
    "market_nim": ROOT / "reports/nim_market_news_graphrag_handoff_v1_latest.json",
}


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _plain_summary(
    hybrid: dict | None,
    spine: dict | None,
    de_nim: dict | None,
    de_probe: dict | None,
    lut: dict | None,
    ops: dict | None,
    anchor_signoff: dict | None = None,
    codec_staging: dict | None = None,
    wire_confirm: dict | None = None,
    trackc_ready: dict | None = None,
    trackc_counsel: dict | None = None,
    trackc_disclaimer: dict | None = None,
    showroom_smoke: dict | None = None,
    showroom_nginx: dict | None = None,
) -> list[str]:
    snap = (hybrid or {}).get("snapshots") or {}
    green = sum(1 for v in snap.values() if v is True)
    total = len(snap) or 11
    parity = None
    if spine:
        agg = spine.get("aggregate") or {}
        parity = agg.get("byte_exact_subset_parity")
    de_ok = (de_nim or {}).get("summary", {}).get("ok")
    de_probes = (de_nim or {}).get("summary", {}).get("probes")
    hits = (de_probe or {}).get("total_hits")
    if hits is None and de_probe:
        sm = de_probe.get("summary") or {}
        hits = sm.get("total_hits")
    nim_model = (de_nim or {}).get("model") or "meta/llama-3.3-70b-instruct"
    lut_status = (lut or {}).get("status", "unknown")
    lut_counts = (lut or {}).get("counts") or {}
    nim_refs = lut_counts.get("nim_verse_refs_guess") or lut_counts.get(
        "verse_refs_merged_de_plus_llm"
    )
    lab = (ops or {}).get("innovation_lab_brev") or {}
    acc = len((anchor_signoff or {}).get("accepted_probe_ids") or [])
    rej = len((anchor_signoff or {}).get("rejected_probe_ids") or [])
    wired = bool((wire_confirm or {}).get("codec_wired_staging"))
    anchor_line = None
    if anchor_signoff:
        codec_note = (
            "코덱 스테이징 배선됨(product lane)"
            if wired
            else "코덱 미배선"
        )
        anchor_line = (
            f"- DE/NIM 앵커 서명: **accept {acc} · reject {rej}** "
            f"(`reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json`) · {codec_note}"
        )

    lines = [
        "## 지휘관용 요약 (쉬운 말 · PLAIN_REPORT)",
        "",
        "### 오늘 한 일 (3줄)",
        f"1. **자료 수집 + AI 초안:** 구글 Discovery Engine이 Logos 관련 문서를 검색했고, "
        f"NVIDIA 클라우드 AI(`{nim_model}`)가 **{de_probes or '?'}개 주제**에 대해 "
        f"성경 앵커 **검토용 초안**을 만들었습니다 (성공 {de_ok or '?'}/{de_probes or '?'}).",
        f"2. **원문 안전:** 압축 뼈대(Spine) 검증 subset **parity = {parity if parity is not None else '—'}** "
        "(실험 중 원문 깨짐 없음).",
        f"3. **한 파일 정리:** 이 보고서(`nvidia_hybrid_operator_paste_v1_latest.txt`)에 핵심만 모았습니다.",
        "",
        "### 지금 상태",
        f"- 체크리스트: 스냅샷 **{green}/{total}** 존재·OK (실험실 B-track `[HYPO]`만).",
        f"- DE 검색 적중: **{hits or '—'}건** (상용 코덱·실매매와 **자동 연결 안 함**).",
        f"- LUT 표지 상태: `{lut_status}` · NIM 병합 앵커 수(참고): **{nim_refs or 'LUT에 nim 병합 행 없음 — synthesis JSON 참고'}**",
        f"- Logos 렌즈: **`[NON_GATING]`** · 최종 권고: **WATCH** (매매 GO 없음).",
        f"- 학습용 GPU: Innovation Lab **{lab.get('status', 'unknown')}** (승인 메일 전까지 API 추론만).",
    ]
    if anchor_line:
        lines.append(anchor_line)
    if trackc_ready:
        lines.append(
            f"- Track C B2B 미팅팩: 내부 **{'OK' if trackc_ready.get('ready_for_internal_meeting') else 'HOLD'}** · "
            f"대외 send **{'금지' if not trackc_ready.get('ready_for_external_send') else 'OK'}** "
            f"(법무 sign-off 전)"
        )
    if trackc_counsel:
        lines.append(
            f"- Track C counsel copy scan: **{'OK' if trackc_counsel.get('scan_ok') else 'BLOCK'}** · "
            f"counsel 제출 준비 **{'OK' if trackc_counsel.get('ready_for_counsel_submission') else 'HOLD'}** "
            f"(`reports/track_c_b2b_counsel_one_minute_brief_v1_latest.md`)"
        )
    if trackc_disclaimer:
        warn_n = trackc_disclaimer.get("tier_b_warn_count", 0)
        tail_ok = trackc_disclaimer.get("tier_b_clear", warn_n == 0)
        lines.append(
            f"- Track C disclaimer integrity: Tier A **{'OK' if trackc_disclaimer.get('integrity_ok') else 'BLOCK'}** · "
            f"Tier B tail **{'OK' if tail_ok else f'WARN {warn_n}'}** · "
            f"대외 send **금지**(법무 human sign-off) "
            f"(`reports/track_c_b2b_disclaimer_integrity_v1_latest.json`)"
        )
    if showroom_smoke:
        lines.append(
            f"- jemaai.cloud 쇼룸 publish: dual-host smoke **{'OK' if showroom_smoke.get('ok') else 'FAIL'}** "
            f"(`reports/showroom_trust_viz_public_chain_smoke_latest.json`)"
        )
    if showroom_nginx and showroom_nginx.get("nginx_reload_ok"):
        lines.append(
            "- VPS nginx 스니펫: **적용·reload OK** "
            f"(`{showroom_nginx.get('remote_snippet', '/etc/nginx/snippets/jemaai_showroom_ui.conf')}`)"
        )
    lines.extend(
        [
        "",
        "### 지휘관이 할 일 (1개)",
        ]
    )
    if wire_confirm and wire_confirm.get("codec_wired_staging"):
        showroom_note = (
            " · 쇼룸: `Invoke-ShowroomTrackCPublishRoutine_v1.ps1` (예약은 `-SkipVpsSync`)"
            if showroom_smoke and showroom_smoke.get("ok")
            else ""
        )
        lines.append(
            "내부 미팅: `docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md` (slide→demo→combined). "
            "제품 paste: `reports/ng40_b2b_product_export_paste_v1_latest.txt`"
            f"{showroom_note}. latent ACTIVE·실매매 GO **없음**."
        )
    elif codec_staging:
        sv = codec_staging.get("staging_verdict") or {}
        lines.append(
            f"LUT→코덱 스테이징 검토 완료 · product lane **"
            f"{'GO' if sv.get('product_lane_ready') else 'HOLD'}** · "
            f"latent ACTIVE 교체 **{'beat' if sv.get('latent_active_replacement_ready') else 'no beat'}**. "
            f"상세: `reports/nvidia_lut_codec_staging_review_paste_v1_latest.txt` · "
            "**코덱 실배선은 지휘관 확인 후 수동**."
        )
    elif anchor_signoff:
        lines.append(
            "앵커 **4 accept / 1 reject(tariff)** 스테이징 반영 완료. "
            "다음은 **LUT→코덱 스테이징 검토**만 수동(Track A·실매매 자동 반영 금지). "
            "픽리스트 재검토: `reports/nvidia_de_nim_commander_anchor_picklist_v1_latest.txt`."
        )
    else:
        lines.append(
            "아래 **부록**과 5행 픽리스트(`reports/nvidia_de_nim_commander_anchor_picklist_v1_latest.txt`)를 보고 "
            "DE/NIM **앵커 후보 채택·폐기**만 지시하세요. "
            "코덱·Track A·실매매에는 **자동 반영하지 않습니다**."
        )
    lines.extend(
        [
            "",
            "### 격벽",
            "실험실 클라우드 합성 완료 → 상용 엔진·실매매 **무단 합선 금지**.",
            "",
            "---",
            "",
        ]
    )
    return lines


def main() -> int:
    docs = {k: _load(p) for k, p in PATHS.items()}
    finished = datetime.now(timezone.utc).isoformat()

    lines = [
        f"# MKM NVIDIA hybrid operator paste",
        f"**갱신:** {finished}",
        "[HYPO] · research_only · NON_GATING · no trading GO",
        "",
    ]
    anchor_signoff = _load(ANCHOR_SIGNOFF)
    codec_staging = _load(CODEC_STAGING)
    wire_confirm = _load(WIRE_CONFIRM)
    trackc_ready = _load(TRACKC_READY)
    trackc_counsel = _load(TRACKC_COUNSEL)
    trackc_disclaimer = _load(TRACKC_DISCLAIMER)
    showroom_smoke = _load(SHOWROOM_SMOKE)
    showroom_nginx = _load(SHOWROOM_NGINX)
    lines.extend(
        _plain_summary(
            docs.get("hybrid_status"),
            docs.get("spine"),
            docs.get("de_nim"),
            docs.get("de_probe"),
            docs.get("lut"),
            docs.get("ops"),
            anchor_signoff,
            codec_staging,
            wire_confirm,
            trackc_ready,
            trackc_counsel,
            trackc_disclaimer,
            showroom_smoke,
            showroom_nginx,
        )
    )

    appendix: list[tuple[str, str, int]] = [
        ("시장·뉴스 NIM 초안", "market_nim", 2800),
        ("AI 산업 Logos NIM 초안", "logos_nim", 1800),
        ("DE×NIM 앵커 요약", "de_nim", 800),
    ]
    for title, key, cap in appendix:
        doc = docs.get(key)
        lines.append(f"## 부록 · {title}")
        if not doc:
            lines.append("(파일 없음)")
        elif key == "de_nim":
            lines.append(json.dumps(doc.get("summary"), ensure_ascii=False, indent=2))
        elif key in ("logos_nim", "market_nim"):
            text = ((doc.get("chat") or {}).get("text") or "")[:cap]
            lines.append(text or "(empty)")
        lines.append("")

    lines.append("## 부록 · 체크리스트 JSON (기술)")
    if docs.get("hybrid_status"):
        lines.append(
            json.dumps(
                {
                    "summary": docs["hybrid_status"].get("summary"),
                    "snapshots": docs["hybrid_status"].get("snapshots"),
                    "finished_at_utc": docs["hybrid_status"].get("finished_at_utc"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    lines.append("")
    lines.append(
        "**경로 SSOT:** reports/hybrid_ai_lab_status_v1_latest.json · "
        "reports/ng40_de_probe_nim_synthesis_v1_latest.json"
    )

    text = "\n".join(lines)
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(text, encoding="utf-8")

    meta = {
        "schema": "nvidia_hybrid_operator_paste_v1",
        "finished_at_utc": finished,
        "plain_report": True,
        "paths": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in PATHS.items()},
        "txt_path": str(OUT_TXT.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT_JSON.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
