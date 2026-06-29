#!/usr/bin/env python3
"""Ingest SciSpace-style CSV exports from Downloads → docs/research/raw + digest JSON."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DL = Path(r"C:\Users\PRO\Downloads")
OUT_DIR = ROOT / "docs/research/raw/scispace_exports_2026-06-24"
DIGEST = ROOT / "docs/research/raw/SCISPACE_CSV_EXPORTS_DIGEST_2026-06-24.json"

# (downloads filename, workspace slug, lane, utility, note)
MANIFEST: list[tuple[str, str, str, str, str]] = [
    (
        "Historical-Development-of-사상체질-표리병증_2025-11-10_00_28_26_export.csv",
        "sasang_pyobyeong_historical_76.csv",
        "sasang_btrack",
        "high",
        "표리병증·동의수세보원 2차; superset of 20-row export",
    ),
    (
        "Technical-methods-in-음성-and-얼굴-analysis-for-사상체질감별,-including-scientific-basis,-technological-tools-used,-and-accuracy-of-these-methods_2025-09-11_22_04_26_export.csv",
        "sasang_voice_face_constitution_66.csv",
        "sasang_clinical_btrack",
        "high",
        "SCAT·SVM·facial morphometrics; no Track A clinical claims",
    ),
    (
        "사상체질-머신러닝-개인화-의학,-맞춤형-치료-시스템,-사상체질-AI-모델-정확도,-사상체질-딥러닝-분류,-사상체질을-머신러닝으로-정확히-분류하는-방법,-사상체질-기반-개인화-의학에서-AI의-역할_2025-11-10_07_04_41_export.csv",
        "sasang_ml_personalized_medicine_40.csv",
        "sasang_btrack",
        "medium",
        "Many Ayurveda/TCM analog papers; methodology reference only",
    ),
    (
        "Intraday-Trading-Strategy-using-Reinforcement-Learning-and-LLM-based-Sentiment-for-High-Sharpe-Ratio_2025-11-10_07_03_55_export.csv",
        "trading_rl_llm_sentiment_160.csv",
        "ms_btrack_research",
        "medium",
        "RL+LLM sentiment; research_only — not live trading",
    ),
    (
        "Exploring-quantitative-trading-strategies-with-a-focus-on-effective-ML-models-in-the-context-of-equities_2025-11-05_08_03_05_export.csv",
        "trading_equities_ml_20.csv",
        "ms_btrack_research",
        "low",
        "Subset largely duplicated in 160-row intraday export",
    ),
    (
        "ARC-Prize-2024-winning-solution-by-ARChitects-team_-complete-implementation-code-for-Test-Time-Training-using-Mistral-NeMo-Minitron-8B-model.-Focus-on_-1.-Full-source-code-in-Python-2.-LoRA-fine-tuning-implementation.csv",
        "arc_prize_ttt_lora_20.csv",
        "infra_control_integrity",
        "medium_high",
        "TTT+LoRA; cross-ref mkm_control_integrity golden/LoRA eval",
    ),
]

SKIP_DUPLICATE = "Historical-Development-of-사상체질-표리병증_2025-11-10_00_20_08_export.csv"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _title_set(rows: list[dict[str, str]]) -> set[str]:
    return {r.get("title", "").strip() for r in rows if r.get("title", "").strip()}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundles: list[dict] = []
    all_titles: dict[str, str] = {}

    for src_name, slug, lane, utility, note in MANIFEST:
        src = DL / src_name
        if not src.is_file():
            print(json.dumps({"ok": False, "error": f"missing {src}"}))
            return 1
        dst = OUT_DIR / slug
        shutil.copy2(src, dst)
        rows = _read_rows(dst)
        titles = _title_set(rows)
        for t in titles:
            all_titles.setdefault(t, slug)
        bundles.append(
            {
                "slug": slug,
                "source_downloads": src_name,
                "workspace_path": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "lane": lane,
                "utility": utility,
                "note": note,
                "row_count": len(rows),
                "unique_titles": len(titles),
                "columns": list(rows[0].keys()) if rows else [],
                "sample_titles": list(titles)[:4],
            }
        )

    skip_path = DL / SKIP_DUPLICATE
    skip_note = None
    if skip_path.is_file():
        sub = _title_set(_read_rows(skip_path))
        sup = _title_set(_read_rows(OUT_DIR / "sasang_pyobyeong_historical_76.csv"))
        skip_note = {
            "file": SKIP_DUPLICATE,
            "verdict": "skip_duplicate",
            "rows": len(sub),
            "contained_in_76_row": len(sub - sup) == 0,
        }

    intra = _title_set(_read_rows(OUT_DIR / "trading_rl_llm_sentiment_160.csv"))
    eq = _title_set(_read_rows(OUT_DIR / "trading_equities_ml_20.csv"))

    doc = {
        "schema": "scispace_csv_exports_digest_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "source": "C:/Users/PRO/Downloads SciSpace exports",
        "ingest_dir": str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        "bundles": bundles,
        "skipped": [skip_note] if skip_note else [],
        "dedup": {
            "pyobyeong_20_vs_76": skip_note,
            "intraday_vs_equities_overlap": len(intra & eq),
            "cross_bundle_duplicate_titles": len(all_titles),
        },
        "lane_summary": {
            "sasang_btrack": "표리병증 역사 + ML 개인화(약식) — IJEOMA/사상 레일 2차",
            "sasang_clinical_btrack": "음성·얼굴 체질감별 — 임상 보조 연구만",
            "ms_btrack_research": "RL·LLM·퀀트 — bitcoin-trading 연구 격벽",
            "infra_control_integrity": "ARC TTT/LoRA — GPU 번들·golden eval 참고",
        },
        "not_useful_for": [
            "천유초(闡幽抄) 원전 입수",
            "Track A 승격·live trading",
            "임상 진단 확정(copy)",
        ],
        "recommended_next": [
            "표리병증 76 CSV → NotebookLM IJEOMA 또는 사상 레일 소스 추가(용량 여유 시)",
            "voice_face 66 → SCAT 정확도 벤치 표와 CONSTITUTION control-integrity 분리 유지",
            "arc 20 → ARChitects repo URL Tier2 grep (코드만, 승격 금지)",
            "trading 160 → pre_news_shadow / sentiment B-track 큐와 제목 dedup",
        ],
        "reproduce": "py scripts/ingest_scispace_csv_exports_v1.py",
    }
    DIGEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "bundles": len(bundles), "digest": str(DIGEST)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
