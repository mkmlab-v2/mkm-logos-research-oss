#!/usr/bin/env python3
"""Rebuild Saving the News legal counsel handoff from manifest + signoff."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
MANIFEST = ART / "saving_the_news_counsel_export_manifest_v1_latest.json"
SIGNOFF = ART / "saving_the_news_legal_counsel_signoff_v1_latest.json"
ZIP_META = ART / "saving_the_news_counsel_zip_pack_v1_latest.json"
DEFAULT_OUT = ART / "saving_the_news_legal_counsel_handoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    manifest = _read(MANIFEST) or {}
    signoff = _read(SIGNOFF)
    files = manifest.get("files") or []
    return {
        "schema": "saving_the_news_legal_counsel_handoff_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "research_only",
        "ready_for_external_send": False,
        "legal_posture_status": (
            "COUNSEL_REVIEWED" if signoff and signoff.get("status") == "COUNSEL_REVIEWED" else "PRIMARY_SOURCE_REVIEWED_PENDING_COUNSEL"
        ),
        "counsel_signoff_required": not bool(signoff),
        "target_status_after_review": "COUNSEL_REVIEWED",
        "primary_source": {
            "issuer": "문화체육관광부·한국저작권위원회",
            "document_title_ko": "생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서",
            "published_utc_approx": "2026-02-26",
            "official_page_url": "https://www.copyright.or.kr/information-materials/publication/research-report/view.do?brdctsno=55211",
        },
        "documents_for_counsel": [row.get("path") for row in files if isinstance(row, dict)],
        "file_manifest": files,
        "counsel_questions_ko": [
            "B2B 관측·게이트 레이어가 「기사 전체 크롤링·자동 요약 대체」에 해당하지 않는지 (2026 공정이용 안내서 사례).",
            "RSS·State Card·Matrix·mkmlife 5-card 덱이 「시장 대체」 저작물 이용에 해당할 여지.",
            "대외 1p·쇼룸 카피의 면책·GTM 3문장 법무 적합성.",
            "ready_for_external_send 승격 전 필수 체크리스트.",
        ],
        "explicit_non_claims": [
            "zero_hallucination",
            "full_article_auto_summary_consumer_replacement",
            "provenance_equals_factuality",
            "track_a_47_5_percent_as_news_proof",
        ],
        "ops_surfaces": {
            "mkmlife_consumer_deck": "https://mkmlife.com/news-deck",
            "jemaai_b2b_showroom": "https://jemaai.cloud/legacy/public_showroom_saving_the_news_matrix_v1.html",
            "vps_sync": "scripts/sync_showroom_to_vps.ps1 (2026-05-29)",
        },
        "counsel_pack_scripts": {
            "submission_chain": "scripts/Run-SavingTheNewsCounselSubmissionPack_v1.ps1",
            "signoff_recorder": "scripts/record_saving_the_news_legal_counsel_signoff_v1.py",
            "zip_meta": ZIP_META.relative_to(ROOT).as_posix(),
            "email_draft": "docs/final/artifacts/saving_the_news_counsel_submission_email_draft_v1_latest.json",
        },
        "boundary_ack": "Handoff manifest only; not legal approval or external send authorization.",
        "counsel_signoff": signoff,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "legal_posture_status": doc["legal_posture_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
