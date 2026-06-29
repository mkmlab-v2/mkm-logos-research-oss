#!/usr/bin/env python3
"""Build KOCCA / VP studio partner brief from on-disk cinematic proof artifacts only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_JSON = ART / "cinematic_kocca_partner_brief_v1_latest.json"
DEFAULT_MD = ART / "cinematic_kocca_partner_brief_v1_latest.md"
BUNDLE = ART / "auditable_cinematic_free_bundle_v1_latest.json"
MANIFEST = ART / "cinematic_injection_manifest_v1_latest.json"
SHOT_PLAN = ART / "director_agent_v1_shot_plan_auditable_poc_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def vp_need_for_shot(shot_id: str, intent: str) -> str:
    if shot_id in {"SHOT_04", "SHOT_05", "SHOT_06"} or "Animatic bridge" in intent:
        return "optional_2d_or_animatic"
    if "Close-up" in intent or "window" in intent.lower():
        return "vp_recommended_face_continuity"
    return "vp_recommended_interior"


def build_scene_rows(shot_plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shot in shot_plan.get("shots") or []:
        sid = str(shot.get("shot_id") or "")
        intent = str(shot.get("intent") or "")
        vp = vp_need_for_shot(sid, intent)
        rows.append(
            {
                "shot_id": sid,
                "duration_sec": shot.get("duration_sec"),
                "intent": intent,
                "poc_mode_economy": "animatic_hero_economy" if sid <= "SHOT_03" else "animatic_meta",
                "poc_mode_hybrid_hero": "reuse_donor_veo" if sid <= "SHOT_03" else "animatic_meta",
                "vp_need": vp,
                "partner_primary": (
                    "VP stage · LED background · actor · camera · on-set supervision"
                    if vp.startswith("vp_")
                    else "Optional motion graphics / title design"
                ),
                "mkm_primary": (
                    "Shot plan JSON · fact_lock anchors · timing · audit trail · local rebuild"
                    if vp.startswith("vp_")
                    else "Pipeline meta slots · reproducible command bundle"
                ),
            }
        )
    return rows


def render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# KOCCA VP 협력 브리프 (MKM Auditable Cinematic · v1)",
        "",
        f"**Generated:** {doc['generated_at_utc']} · **Status:** `{doc['send_gate']}` · **Promotion:** `{doc['promotion']}`",
        "",
        "## 포지션 (정직)",
        "",
        doc["positioning"]["summary"],
        "",
        f"- **단독 신청 적합도:** {doc['positioning']['solo_application_fit']}",
        f"- **제작사/VPP 협력 적합도:** {doc['positioning']['partner_application_fit']}",
        "",
        "## 디스크 증거 (Fact-Lock)",
        "",
        "| 항목 | 경로 |",
        "|------|------|",
    ]
    for k, v in doc["disk_evidence"].items():
        lines.append(f"| {k} | `{v}` |")
    lines.extend(
        [
            "",
            f"- Bundle OK: **{doc['proof']['bundle_ok']}** · Veo API called: **{doc['proof']['veo_api_called']}** · Cost: **${doc['proof']['cost_usd']}**",
            "",
            "## VP 씬리스트 (companion-human PoC 기준)",
            "",
            "| Shot | 초 | VP 필요도 | PoC economy | PoC hybrid | 제작사 | MKM |",
            "|------|-----|-----------|-------------|------------|--------|-----|",
        ]
    )
    for row in doc["vp_scene_list"]:
        lines.append(
            f"| {row['shot_id']} | {row['duration_sec']} | {row['vp_need']} | "
            f"{row['poc_mode_economy']} | {row['poc_mode_hybrid_hero']} | "
            f"{row['partner_primary'][:40]}… | {row['mkm_primary'][:40]}… |"
        )
    lines.extend(
        [
            "",
            "## 역할 분담 요약",
            "",
            "| 레이어 | 제작사/VPP | MKM |",
            "|--------|------------|-----|",
            "| 프리프로덕션 | 촬영·VP 스케줄, 세트, 배우 | 시나리오→샷플랜 JSON, fact_lock 앵커 |",
            "| 제작 | LED·실사 촬영, 현장 연출 | 로컬 파이프라인·게이트·감사 로그 |",
            "| 후반 | 컬러·사운드 마스터 | 슬롯 정합·재현 번들·루브릭 (기술) |",
            "",
            "## 하지 않는 주장",
            "",
        ]
    )
    for item in doc["disallowed_claims"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 재현",
            "",
            "```powershell",
            doc["reproduce_cmd"],
            "```",
            "",
            "```powershell",
            "py scripts/cinematic/build_cinematic_kocca_partner_brief_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=BUNDLE)
    ap.add_argument("--manifest-json", type=Path, default=MANIFEST)
    ap.add_argument("--shot-plan-json", type=Path, default=SHOT_PLAN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    bundle = load(args.bundle_json)
    manifest = load(args.manifest_json)
    shot_plan = load(args.shot_plan_json)

    missing = [p for p in (args.bundle_json, args.shot_plan_json) if not p.is_file()]
    if missing:
        raise SystemExit(f"missing required artifacts: {', '.join(str(p) for p in missing)}")

    scene_rows = build_scene_rows(shot_plan)
    doc: dict[str, Any] = {
        "schema": "cinematic_kocca_partner_brief_v1",
        "generated_at_utc": now_utc(),
        "send_gate": "HOLD",
        "promotion": "infra_only",
        "positioning": {
            "summary": (
                "MKM 단독은 '완성 영화 제작사'가 아니라 Auditable Cinematic Pipeline(샷플랜 JSON·게이트·재현) "
                "제공자로 KOCCA VP 인프라 과제에 협력 신청이 적합하다."
            ),
            "solo_application_fit": "low",
            "partner_application_fit": "medium",
            "program_context": "KOCCA VP 활용 콘텐츠 제작 인프라 지원 (제작사 공동 신청 전제)",
        },
        "proof": {
            "bundle_ok": bundle.get("ok"),
            "veo_api_called": bundle.get("veo_api_called"),
            "cost_usd": bundle.get("cost_usd", 0),
            "economy_master_mp4": (bundle.get("variants") or {}).get("economy", {}).get("master_mp4"),
            "hybrid_master_mp4": (bundle.get("variants") or {}).get("hybrid", {}).get("master_mp4"),
        },
        "disk_evidence": {
            "free_bundle": str(args.bundle_json),
            "injection_manifest": str(args.manifest_json),
            "shot_plan": str(args.shot_plan_json),
            "proof_readme": str(ART / "cinematic_auditable_poc_proof_readme_v1.md"),
            "hero_rubric": str(ART / "cinematic_hero_rubric_check_v1_latest.json"),
        },
        "vp_scene_list": scene_rows,
        "hybrid_disclaimer": (manifest.get("hybrid") or {}).get("disclaimer"),
        "disallowed_claims": [
            "할리우드·극장급 실사 영화 완성",
            "companion-human 정체성 일관성 (hybrid donor 슬롯 기준)",
            "Track A 상용·실매매·의료·투자 효과",
            "Vertex 무과금 고품질 생성 (free bundle은 $0 API)",
        ],
        "reproduce_cmd": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\cinematic\\Run-AuditableCinematicFreeBundle_v1.ps1",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(args.out_json), "out_md": str(args.out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
