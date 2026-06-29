#!/usr/bin/env python3
"""Tier-3 Human checklist for enterprise/apply Turnstile E2E (hg-02 handoff)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "reports/enterprise_apply_live_smoke_v1_latest.json"
OUT_JSON = ROOT / "reports/enterprise_apply_turnstile_e2e_checklist_v1_latest.json"
OUT_MD = ROOT / "reports/enterprise_apply_turnstile_e2e_checklist_v1_latest.md"

APPLY_URL = "https://app.jema-ai.com/enterprise/apply"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    smoke = _load(SMOKE)
    steps = [
        {
            "n": 1,
            "action": "일반 Chrome(에이전트/openchrome 아님)에서 apply URL 열기",
            "url": APPLY_URL,
            "pass": "폼·Turnstile 위젯 로드",
        },
        {
            "n": 2,
            "action": "테스트용 더미 값 입력 (실 PII 금지)",
            "fields": ["company", "contact_email", "use_case", "pii_scrub_ack"],
            "pass": "필수 필드 검증 통과",
        },
        {
            "n": 3,
            "action": "Turnstile 체크박스 완료 (지휘관 직접)",
            "pass": "위젯 success 상태",
        },
        {
            "n": 4,
            "action": "제출 클릭",
            "pass": "성공 토스트/확인 화면 또는 2xx API 응답",
        },
        {
            "n": 5,
            "action": "스크린샷 또는 Network 탭에서 POST 응답 캡처 (비밀 제외)",
            "pass": "reports/ 에 증거 파일명 기록",
        },
        {
            "n": 6,
            "action": "API smoke 재실행으로 회귀 확인",
            "command": "py scripts/check_enterprise_apply_live_smoke_v1.py",
            "pass": "decision PASS 유지",
        },
    ]
    forbidden = [
        "에이전트 browser_* / openchrome으로 Turnstile 제출",
        "dash.cloudflare.com 에이전트 로그인",
        "Turnstile 토큰 우회·스크립트 주입",
        "실 고객 PII를 채팅/커밋에 붙이기",
    ]
    return {
        "schema": "enterprise_apply_turnstile_e2e_checklist_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "web_ops_tier3_human",
        "human_gate": "captcha_turnstile_tier3",
        "apply_url": APPLY_URL,
        "api_smoke": {
            "path": str(SMOKE.relative_to(ROOT)),
            "all_ok": smoke.get("all_ok"),
            "decision": smoke.get("decision"),
            "generated_at_utc": smoke.get("generated_at_utc"),
        },
        "prerequisite": "API smoke PASS before browser E2E",
        "steps": steps,
        "forbidden": forbidden,
        "hg_handoff": "hg-02",
        "reproduce": "py scripts/build_enterprise_apply_turnstile_e2e_checklist_v1.py",
    }


def _md(doc: dict[str, Any]) -> str:
    sm = doc.get("api_smoke") or {}
    lines = [
        "# Enterprise Apply — Turnstile E2E 체크리스트 (Tier 3 Human)",
        "",
        f"- 생성: {doc.get('generated_at_utc')}",
        f"- URL: {doc.get('apply_url')}",
        f"- API smoke: **{sm.get('decision')}** (`{sm.get('path')}`)",
        "",
        "## 사전 조건",
        "",
        "- `py scripts/check_enterprise_apply_live_smoke_v1.py` → **PASS**",
        "- **일반 Chrome**만 사용 (에이전트/openchrome 금지)",
        "",
        "## 단계",
        "",
    ]
    for s in doc.get("steps") or []:
        lines.append(f"### {s['n']}. {s['action']}")
        if s.get("url"):
            lines.append(f"- URL: {s['url']}")
        if s.get("fields"):
            lines.append(f"- 필드: {', '.join(s['fields'])}")
        if s.get("command"):
            lines.append(f"- 명령: `{s['command']}`")
        lines.append(f"- Pass: {s['pass']}")
        lines.append("")
    lines.append("## 금지")
    lines.append("")
    for f in doc.get("forbidden") or []:
        lines.append(f"- {f}")
    lines.extend(
        [
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/build_enterprise_apply_turnstile_e2e_checklist_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    if not doc.get("api_smoke", {}).get("all_ok"):
        print(json.dumps({"ok": False, "reason": "api_smoke_not_pass"}, ensure_ascii=False))
        return 1
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "steps": len(doc["steps"]), "hg_handoff": "hg-02"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
