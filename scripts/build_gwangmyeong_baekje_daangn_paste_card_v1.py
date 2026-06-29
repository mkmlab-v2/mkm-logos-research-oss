#!/usr/bin/env python3
"""Build paste-ready HTML card for 광명백제한의원 당근 동네생활 copy (PUBLIC_FACING v1.7)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports" / "gwangmyeong_baekje_daangn_paste"
HTML_OUT = ROOT / "reports" / "demo" / "gwangmyeong_baekje_daangn_paste_assistant_v1.html"
META_OUT = ROOT / "reports" / "gwangmyeong_baekje_daangn_paste_build_latest.json"

FIELDS: dict[str, str] = {
    "post_a_chuna_title.txt": "광명사거리역 인근 — 추나·자세, 한의원에서 **어떻게** 접근하나요?",
    "post_a_chuna_body.txt": (
        "안녕하세요, 광명백제한의원입니다. (광명로 · 광명사거리역 인근)\n\n"
        "허리·목 불편, 오래 앉은 뒤 뻐근함, 자세 불균형은 **증상·생활습관·개인차**가 함께 얽혀 있습니다.\n"
        "저희는 **4진·변증**을 바탕으로, 추나요법·침·뜸·한약 등 **한의사가 진료실에서 판단**하는 범위 안에서 단계를 맞춥니다.\n\n"
        "※ 동네생활 글·댓글에서는 **개인 진료 상담을 하지 않습니다.**\n"
        "※ **완치·100%·무조건** 표현은 사용하지 않습니다.\n\n"
        "📍 내원·예약: [전화번호]\n"
        "💬 **카카오 채널** QR(접수대) → **본인 이름**을 먼저 보내 주시면, 진료·안내 연결에 도움이 됩니다."
    ),
    "post_b_traffic_title.txt": "교통사고 이후 — 한의원은 **어디까지** 볼 수 있나요? (광명·근교)",
    "post_b_traffic_body.txt": (
        "교통사고 후 목·허리·어깨 불편, 수면·스트ress 변화는 흔하지만, **사람마다 경과가 다릅니다.**\n\n"
        "광명백제한의원에서는\n"
        "① **응급·골절·출혈 등**은 **응급실·1차 병원** 우선\n"
        "② 안정기 이후 **한의사 진료·4진** 하에 침·뜸·추나·한약 등 **개별 계획**\n"
        "을 **진료실에서** 상의합니다.\n\n"
        "※ 글·댓글에서 **약·한약·유산균 “효능”·치료 결과**를 단정하지 않습니다.\n"
        "※ 보험·산재·합의 등 **법·행정**은 해당 기관·전문가 확인이 필요합니다.\n\n"
        "📍 내원: [전화번호] · 광명로 [상세]\n"
        "💬 카카오 채널 — 접수대 QR → **이름** 선발송 (채널 추가 후 1:1)"
    ),
    "post_c_core_title.txt": "“뱃살만”이 아닐 때 — 호흡·복벽·생활 **함께** 보는 이유",
    "post_c_core_body.txt": (
        "뱃살·복부 돌출은 **전신 대사·호흡·자세·생활습관**이 겹친 경우가 많습니다.\n"
        "“부위만 빠진다”기보다 **전체 리듬**을 함께 보는 편이 현실적입니다.\n\n"
        "광명백제한의원에서는 **담당 원장 진료·4진** 후, 침·추나·운동·생활 **참고**를 개인에 맞게 상의합니다. "
        "(진단·처방 **대체 아님**)\n\n"
        "※ 댓글/DM 상담 없음 → **내원·전화·카카오(이름 선발송)**\n"
        "※ 개인차·의료 확인 필요 — **완치·100% 금지**\n\n"
        "📍 광명사거리역 인근 · [전화번호]"
    ),
    "common_footer_disclaimer.txt": (
        "본 게시물은 **의료 진단·치료·처방을 제공하지 않습니다.** "
        "불편·증상·응급 의심 시 **의료기관·응급실**을 이용해 주세요.\n"
        "ready_for_external_send: false · SEND_GATE: HOLD · 법무 검토 전 배포 금지"
    ),
    "staff_daangn_rules_3lines.txt": (
        "【당근 운영 3줄 · 직원】\n"
        "1) 댓글 **증상 상담·약 추천 금지** → “내원·카카오·전화”\n"
        "2) **악성·분쟁** → DM 금지, 원장 에스컬\n"
        "3) 콘텐츠 **주 1–2회** · 동일 문구 스팸 금지"
    ),
    "desk_kakao_optin_script.txt": (
        "【접수대 Opt-in 스크립트】\n"
        "“카카오 **채널 추가** 후 **성함**만 보내 주세요. 진료 안내·예약 리마인드에 씁니다.”\n"
        "→ 데스크: 채널 1:1 **이름·내원일** 매핑\n"
        "→ 첫 회신: patient_wellness_entry **intro_kakao** (비진단) — 치료·약 효능 없음"
    ),
    "forbidden_3lines.txt": (
        "【대외 금지 3줄 · Kill-Matrix】\n"
        "1) AI·사주로 **체질·질병 진단/처방**\n"
        "2) KoGES 사상 + 사주 오행 **한 줄 합성**\n"
        "3) 근거 없는 **○○% 정확도·재방문 100%**"
    ),
}

LABELS = {
    "post_a_chuna_title.txt": "Post A · 제목 (추나·자세)",
    "post_a_chuna_body.txt": "Post A · 본문 (추나·자세)",
    "post_b_traffic_title.txt": "Post B · 제목 (교통사고)",
    "post_b_traffic_body.txt": "Post B · 본문 (교통사고 · 효능 배제)",
    "post_c_core_title.txt": "Post C · 제목 (복부·코어)",
    "post_c_core_body.txt": "Post C · 본문 (복부·코어)",
    "common_footer_disclaimer.txt": "공통 Footer · 면책",
    "staff_daangn_rules_3lines.txt": "직원 · 당근 운영 3줄",
    "desk_kakao_optin_script.txt": "데스크 · 카카오 Opt-in SOP",
    "forbidden_3lines.txt": "금지 3줄 · Kill-Matrix",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _html_block(block_id: str, title: str, text: str) -> str:
    safe_id = block_id.replace(".", "_").replace("-", "_")
    n = len(text)
    return (
        f'<section><h3>{title} · {n}자</h3>'
        f'<pre id="t_{safe_id}">{text}</pre>'
        f'<button type="button" onclick="copy(\'t_{safe_id}\')">복사</button></section>'
    )


def build_html() -> str:
    sections = "\n".join(
        _html_block(fname.replace(".txt", ""), LABELS[fname], FIELDS[fname]) for fname in LABELS
    )
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>광명백제 · 당근 카피 Paste</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;background:#0f1419;color:#e6edf3}}
h1{{font-size:1.25rem}} section{{margin:16px 0;padding:12px;border:1px solid #30363d;border-radius:8px}}
pre{{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:6px;font-size:13px}}
button{{margin-top:8px;padding:8px 14px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer}}
.meta{{color:#8b949e;font-size:12px}} .warn{{color:#f85149}} .hold{{color:#e8c88a;font-size:13px}}
</style></head><body>
<h1>광명백제한의원 · 당근 동네생활 카피 Lock-down v1</h1>
<p class="warn">SEND_GATE: HOLD · ready_for_external_send: false · 법무·의료광고 검토 전 배포 금지</p>
<p class="hold">채널 규칙: 댓글/DM 진료 상담 금지 → 내원·전화·카카오 Opt-in(이름 선발송)</p>
<p class="meta">SSOT: docs/final/artifacts/gwangmyeong_baekje_daangn_copy_v1_latest.md</p>
<p class="meta">재빌드: py scripts/build_gwangmyeong_baekje_daangn_paste_card_v1.py · 게이트: py scripts/check_gwangmyeong_baekje_daangn_public_copy_v1.py</p>
{sections}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t).then(()=>alert('복사됨'))}}
</script></body></html>
"""


def main() -> int:
    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    for fname, text in FIELDS.items():
        (PASTE_DIR / fname).write_text(text + "\n", encoding="utf-8")
    HTML_OUT.write_text(build_html(), encoding="utf-8")
    meta = {
        "schema": "gwangmyeong_baekje_daangn_paste_build_v1",
        "generated_at_utc": _utc(),
        "field_count": len(FIELDS),
        "html_out": str(HTML_OUT.relative_to(ROOT)).replace("\\", "/"),
        "paste_dir": str(PASTE_DIR.relative_to(ROOT)).replace("\\", "/"),
        "ready_for_external_send": False,
        "send_gate": "HOLD",
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {HTML_OUT}")
    print(f"OK: {PASTE_DIR} ({len(FIELDS)} txt)")
    print(f"OK: {META_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
