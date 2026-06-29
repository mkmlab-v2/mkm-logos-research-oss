#!/usr/bin/env python3
"""Build §10 hyper-personal news intake snapshot ([HYPO], shadow-only)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_COMMANDER = ART / "commander_profile_v1.example.json"
DEFAULT_HEADLINE = ART / "pre_news_shadow_input_latest.json"
OUT_JSON = ART / "hyper_personal_news_intake_v1_latest.json"
LOG_JSONL = ROOT / "reports" / "hyper_personal_news_intake_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def derive_priors(commander: dict[str, Any]) -> dict[str, float]:
    """Deterministic [HYPO] priors — not clinical gating, not news rank override."""
    myeongni = commander.get("myeongni_fact_ref") or {}
    dm = str(myeongni.get("day_master_stem") or "")
    dm_hash = hashlib.sha256(dm.encode("utf-8")).hexdigest()
    myeongni_prior = round(((int(dm_hash[:4], 16) / 65535) - 0.5) * 0.4, 4)

    sasang_label = str((commander.get("sasang_reference") or {}).get("label") or "")
    if sasang_label:
        sh = hashlib.sha256(sasang_label.encode("utf-8")).hexdigest()
        sasang_scalar = round(0.55 + (int(sh[:4], 16) / 65535) * 0.35, 4)
    else:
        sasang_scalar = 0.5

    return {
        "sasang_scalar": min(1.0, max(0.0, sasang_scalar)),
        "myeongni_day_pillar_prior_hypo": min(0.5, max(-0.5, myeongni_prior)),
        "wellness_hypo_budget": 0.25,
    }


def build_intake(
    *,
    commander_path: Path = DEFAULT_COMMANDER,
    headline_path: Path = DEFAULT_HEADLINE,
    news_hp_rt_status: str = "NOT_MEASURED",
) -> dict[str, Any]:
    commander = _read(commander_path)
    headline_doc = _read(headline_path)
    priors = derive_priors(commander)
    headline = ""
    if isinstance(headline_doc.get("headlines"), list) and headline_doc["headlines"]:
        headline = str(headline_doc["headlines"][0].get("headline") or "")[:160]
    elif headline_doc.get("headline"):
        headline = str(headline_doc["headline"])[:160]

    return {
        "schema": "hyper_personal_news_intake_v1",
        "hypothesis_tier": "B",
        "boundary_ack": (
            "research_only; not medical, legal, or investment advice; "
            "no live trading or Track A coupling; no CMS auto-publish; "
            "Logos lens is interpretive only (NON_GATING)."
        ),
        "generated_at_utc": _utc_now(),
        "field": {
            "regime_id": "regime_saving_the_news_hyper_personalization",
            "commander_profile_ref": _rel(commander_path),
            "news_cohort_ref": "docs/final/artifacts/news_observation_v1_latest.jsonl",
            "headline_anchor_ref": _rel(headline_path) if headline_path.is_file() else None,
            "headline_sample": headline or None,
            "priors": priors,
        },
        "lenses": {
            "sasang": {
                "role": "curation_density",
                "summary_ko": (
                    f"큐레이션 강도 sasang_scalar={priors['sasang_scalar']} "
                    "[HYPO] — 진영 내러티브 합선 없음."
                ),
                "confidence_level": "C",
            },
            "myeongni": {
                "role": "day_pillar_prior_blend",
                "summary_ko": (
                    f"day_pillar_prior={priors['myeongni_day_pillar_prior_hypo']} "
                    "[HYPO] — 뉴스 랭킹 단독 확정 아님."
                ),
                "confidence_level": "C",
            },
            "logos": {
                "role": "NON_GATING",
                "summary_ko": "거시 시태·탐욕 패턴 해설 보조 — 송출·매매 트리거 없음.",
                "confidence_level": "C",
            },
        },
        "conflict": {
            "tension_axes": ["user_spacetime_priors_vs_unstructured_news_stream"],
            "notes_ko": (
                "유저 priors와 비정형 뉴스 스트림 매칭 노이즈 — shadow 관측만; "
                "단일 앵커 치환 금지."
            ),
        },
        "final": {
            "decision_label": "WATCH",
            "cms_publish_allowed": False,
            "one_line_ko": "가중 합성 shadow 구간; 자동 송출·매매 없음.",
            "disclaimer_ko": "§10 shadow 산출물; 실서비스·소비자 앱 아님.",
        },
        "audit": {
            "weights": {
                "sasang_scalar": priors["sasang_scalar"],
                "myeongni_day_pillar_prior_hypo": priors["myeongni_day_pillar_prior_hypo"],
                "wellness_hypo_budget": priors["wellness_hypo_budget"],
                "logos": 0.15,
                "matrix_residual": round(
                    max(
                        0.0,
                        1.0
                        - priors["sasang_scalar"] * 0.35
                        - abs(priors["myeongni_day_pillar_prior_hypo"]) * 0.25
                        - 0.25
                        - 0.15,
                    ),
                    4,
                ),
            },
            "model_route": "local_stub_no_llm",
            "evidence_path": _rel(OUT_JSON),
            "validated_at": _utc_now(),
            "bench_axes": {
                "news_rt": "COMPLETE_OFFLINE_COHORT",
                "news_hp_rt": news_hp_rt_status,
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commander-json", type=Path, default=DEFAULT_COMMANDER)
    ap.add_argument("--headline-json", type=Path, default=DEFAULT_HEADLINE)
    ap.add_argument("--news-hp-rt-status", default="NOT_MEASURED")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    doc = build_intake(
        commander_path=args.commander_json,
        headline_path=args.headline_json,
        news_hp_rt_status=args.news_hp_rt_status,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
    log_row = {
        "generated_at_utc": doc.get("generated_at_utc"),
        "decision_label": (doc.get("final") or {}).get("decision_label"),
        "regime_id": (doc.get("field") or {}).get("regime_id"),
        "priors": (doc.get("field") or {}).get("priors"),
        "news_hp_rt": (doc.get("audit") or {}).get("bench_axes", {}).get("news_hp_rt"),
        "path": _rel(args.out_json),
    }
    with LOG_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_row, ensure_ascii=False) + "\n")
    print(f"WROTE: {args.out_json} decision={doc['final']['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
