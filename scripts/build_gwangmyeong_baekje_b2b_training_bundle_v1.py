#!/usr/bin/env python3
"""[HYPO] B2B 한의원 연수 번들 — rib55 adjudication + Google Form spec + barrier audit.

Internal staging only; send_gate HOLD; no live Solapi/Form publish.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json"
FORM = ROOT / "docs/final/artifacts/b2b_han_clinic_training_google_form_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
ADJ_RECORD = ROOT / "docs/final/artifacts/rib55_overlay_adjudication_record_pilot_ninth_rib_55deg_v0_latest.json"
OUT = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_bundle_v1_latest.json"
HUB_OUT = ROOT / "reports/gwangmyeong_baekje_b2b_static_hub_draft_v1.md"
AUDIT_OUT = ROOT / "reports/gwangmyeong_baekje_b2b_barrier_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rib55_status(manifest: dict[str, Any]) -> dict[str, Any]:
    entry = (manifest.get("entries") or [{}])[0]
    adj = entry.get("adjudication") or {}
    return {
        "entry_id": entry.get("entry_id"),
        "status": entry.get("status"),
        "decision": adj.get("decision"),
        "signed_by": adj.get("signed_by"),
        "signed_at": adj.get("signed_at"),
        "pilot_png": "docs/final/artifacts/rib55_overlay_pilot_ninth_rib_55deg_v0_latest.png",
        "adjudication_record": str(ADJ_RECORD.relative_to(ROOT)).replace("\\", "/"),
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
    }


def _sync_spec(spec: dict[str, Any], rib55: dict[str, Any], form_rel: str) -> None:
    assets = spec.setdefault("education_assets_b2b_only", {})
    assets["rib55_pilot_pointer"] = rib55["pilot_png"]
    assets["rib55_status"] = rib55.get("status")
    assets["rib55_adjudication_decision"] = rib55.get("decision")
    assets["rib55_adjudication_record_pointer"] = rib55["adjudication_record"]
    assets["rib55_manifest_pointer"] = rib55["manifest"]
    assets["mkm_google_form_pointer"] = form_rel
    assets["rib55_usage"] = (
        "B2B lecture slide only; adjudicated_education_internal; not patient imaging; "
        "rib sweep HYPO not clinical angle; send_gate HOLD"
    )
    spec.setdefault("reproduction", {})["bundle_cmd"] = (
        "py scripts/build_gwangmyeong_baekje_b2b_training_bundle_v1.py"
    )
    spec["updated_at_utc"] = _utc()


def _build_hub_md(rib55: dict[str, Any]) -> str:
    caption = (
        "9번 늑골 측면 rib sweep [교육용·비진단] — adjudication_internal 승인; "
        "외부 송출 HOLD"
    )
    return f"""# 광명백제 B2B 연수 — 1페이지 정적 허브 v1

**Status:** `[HYPO]` · `SEND_GATE: HOLD` · patient funnel 격벽 · **updated:** {_utc()}

## 상단 고지 (필수)

- 본 허브는 **동료 한의사 B2B 연수** 전용입니다.
- **환자 예약·소개·진료 상담 목적이 아닙니다.**
- 교육 자료는 학술·실습 참고이며 **치료 효능·임상 자격을 보장하지 않습니다.**

## 링크 블록 (원장이 URL만 채움)

| 주차 | 내용 | 링크 |
|------|------|------|
| 등록 | Google Form FORM-01 | `#{{등록_폼_URL}}` |
| 1주 | 개론·호흡/늑골 교육 영상 (Drive) | `#{{1주_영상_URL}}` |
| 2–4주 | 주차 모듈 + 과제 FORM-02 | `#{{과제_폼_URL}}` |
| Q&A | FORM-03 (비식별) | `#{{QA_폼_URL}}` |

## 교육 도판 — rib55 pilot (내부 승인)

| 항목 | 값 |
|------|-----|
| PNG | `{rib55["pilot_png"]}` |
| entry | `{rib55.get("entry_id")}` |
| status | `{rib55.get("status")}` |
| decision | `{rib55.get("decision")}` |
| signed_by | `{rib55.get("signed_by")}` |
| record | `{rib55["adjudication_record"]}` |

- 캡션: **{caption}**
- Commons CC-BY-SA-2.1-JP attribution footer 유지

## MKM Google Form 스펙 (Charter R5)

- SSOT: `docs/final/artifacts/b2b_han_clinic_training_google_form_v1_latest.json`
- 수동 Google Forms 복제 · CRM/Zapier 연동 금지

## Solapi 알림톡

- Phase 2 · 스펙만 확보 · **실발송 HOLD** (`gwangmyeong_baekje_b2b_training_spec_v1.json`)

## 격벽 감사

```powershell
py scripts/check_gwangmyeong_baekje_b2b_training_spec_v1.py --write-spec-status
py scripts/build_gwangmyeong_baekje_b2b_training_bundle_v1.py
```
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-audit", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for path in (SPEC, FORM, MANIFEST, ADJ_RECORD):
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"missing {path}"}))
            return 2

    manifest = _load(MANIFEST)
    spec = _load(SPEC)
    form = _load(FORM)
    rib55 = _rib55_status(manifest)

    if rib55.get("decision") != "approved_education_internal":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "rib55 adjudication not approved_education_internal",
                    "rib55": rib55,
                },
                ensure_ascii=False,
            )
        )
        return 1

    form_rel = str(FORM.relative_to(ROOT)).replace("\\", "/")
    _sync_spec(spec, rib55, form_rel)
    hub_md = _build_hub_md(rib55)

    audit_doc: dict[str, Any] | None = None
    audit_exit = 0
    if not args.skip_audit and not args.dry_run:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/check_gwangmyeong_baekje_b2b_training_spec_v1.py",
                "--write-spec-status",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        audit_exit = proc.returncode
        if AUDIT_OUT.is_file():
            audit_doc = _load(AUDIT_OUT)

    bundle = {
        "schema": "gwangmyeong_baekje_b2b_training_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "rib55": rib55,
        "pointers": {
            "training_spec": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
            "google_form": form_rel,
            "static_hub_md": str(HUB_OUT.relative_to(ROOT)).replace("\\", "/"),
            "static_hub_html": "reports/demo/gwangmyeong_baekje_b2b_static_hub_v1.html",
            "solapi_dry": "docs/final/artifacts/gwangmyeong_baekje_b2b_solapi_dry_v1_latest.json",
            "staff_handout": spec.get("education_assets_b2b_only", {}).get("staff_handout_pointer"),
            "barrier_audit": str(AUDIT_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "google_form_summary": {
            "sections": len(form.get("sections") or []),
            "send_gate": (form.get("passive_corral") or {}).get("send_gate"),
        },
        "barrier_audit_status": (audit_doc or {}).get("audit_status"),
        "barrier_audit_ok": audit_exit == 0,
        "operator_lines": [
            "- [B2B-BUNDLE] rib55 adjudication linked; send_gate=HOLD.",
            f"- [B2B-BUNDLE] static_hub={HUB_OUT.name}",
            f"- [B2B-BUNDLE] barrier_audit={'PASS' if audit_exit == 0 else 'FAIL'}",
        ],
        "reproduce": "py scripts/build_gwangmyeong_baekje_b2b_training_bundle_v1.py",
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "rib55": rib55}, ensure_ascii=False))
        return 0

    SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    HUB_OUT.parent.mkdir(parents=True, exist_ok=True)
    HUB_OUT.write_text(hub_md + "\n", encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": audit_exit == 0, "out": str(OUT), "audit_exit": audit_exit}, ensure_ascii=False))
    return 0 if audit_exit == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
