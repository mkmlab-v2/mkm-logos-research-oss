#!/usr/bin/env python3
"""MKMLIFE §11 / 오픈베타 readiness: monorepo route pointers (payment E2E deferred per MISSION_LOG)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSOT_DOC = ROOT / "docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkmlife_section11_readiness_v1_latest.json"
MKMLIFE_CANDIDATES = (
    ROOT / "projects/mkm/mkm-life",
    ROOT / "projects/no1kmedi",
    Path("E:/workspace/mkm-life"),
)

MKMLIFE_MONOREPO_CHECKS = (
    "app/ask-one/page.tsx",
    "app/oracle-sphere/page.tsx",
    "components/magic-orb/LensReportCard.tsx",
    "components/magic-orb/DisclaimerPanel.tsx",
    "app/api/v1/payments/webhook/payapp/route.ts",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="mkmlife §11 route readiness (open beta: payment E2E deferred; pointer + SSOT only)."
    )
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    repo_roots = [str(p) for p in MKMLIFE_CANDIDATES if p.is_dir()]
    mono_root = ROOT / "projects/mkm/mkm-life"
    monorepo_files = [
        {
            "path": rel.replace("\\", "/"),
            "exists": (mono_root / rel).is_file(),
        }
        for rel in MKMLIFE_MONOREPO_CHECKS
    ]
    monorepo_ok = mono_root.is_dir() and all(item["exists"] for item in monorepo_files)
    if monorepo_ok:
        gaps: list[str] = []
    else:
        gaps = ["monorepo routes missing (ask-one, oracle-sphere, decoy components)"]
    doc = {
        "schema": "mkmlife_section11_readiness_v1",
        "mission_id": "MKMLIFE-OOBETA",
        "open_beta_phase": True,
        "payment_e2e_deferred": True,
        "generated_at_utc": _utc_now(),
        "ssot_doc": str(SSOT_DOC.relative_to(ROOT)).replace("\\", "/") if SSOT_DOC.is_file() else None,
        "product_lock_ko": "One-Question Premium · Pay-per-question · NOT unlimited chat buffet",
        "decoy_alignment_ko": (
            "타로/MBTI는 로딩·스킨·체험 레이어만 허용. "
            "랜딩이 '타로 앱'처럼 보이면 §11·mkmlife 도메인 표와 충돌."
        ),
        "repo_roots_found": repo_roots,
        "monorepo_root": str(mono_root) if mono_root.is_dir() else None,
        "monorepo_files": monorepo_files,
        "monorepo_routes_ok": monorepo_ok,
        "implementation_gaps": gaps,
        "post_open_beta_work_ko": [
            "PayApp·Stripe·Toss 실결제·웹훅 멱등·환불 SSOT",
            "npm run smoke:one-question (전체 플로우)",
        ],
        "track_wall": {
            "no_jemaai_showroom_funnel_on_mkmlife": True,
            "no_track_a_trading": True,
            "ms_oracle_merge_forbidden": True,
        },
        "d1_next": (
            "오픈베타: 유입·면책·라우트 유지. 종료 후: PayApp·환불 SSOT·smoke:one-question 전체"
            if monorepo_ok
            else "restore monorepo mkmlife routes (ask-one, oracle-sphere)"
        ),
        "section11_pointer_ok": monorepo_ok and SSOT_DOC.is_file(),
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0 if doc["section11_pointer_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
