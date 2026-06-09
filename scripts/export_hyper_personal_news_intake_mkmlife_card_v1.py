#!/usr/bin/env python3
"""Export §10 hyper-personal intake as mkmlife news-deck slot card (research_only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from mkm_consumer_facade_v1 import facade_hyper_personal_card  # noqa: E402
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_INTAKE = ART / "hyper_personal_news_intake_v1_latest.json"
DEFAULT_HP_BENCH = ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json"
DEFAULT_RAW_BENCH = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
DEFAULT_OUT = ART / "hyper_personal_news_intake_mkmlife_card_v1_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects" / "mkm" / "mkm-life" / "public" / "data"


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


def build_card(
    intake: dict[str, Any],
    hp_bench: dict[str, Any],
    raw_bench: dict[str, Any],
) -> dict[str, Any]:
    field = intake.get("field") or {}
    priors = field.get("priors") or {}
    final = intake.get("final") or {}
    hp_kpi = hp_bench.get("kpi") or {}
    raw_kpi = raw_bench.get("kpi") or raw_bench.get("contract_kpi") or {}

    raw_saving = raw_kpi.get("token_saving_ratio")
    if raw_saving is None:
        raw_saving = raw_bench.get("token_saving_ratio")

    hp_saving = hp_kpi.get("token_saving_ratio_hp_weighted")
    delta = (hp_bench.get("delta_vs_news_rt_baseline") or {}).get(
        "token_saving_ratio_delta_hp_minus_baseline"
    )

    prior_rows = [
        {"key": "sasang_scalar", "label_ko": "사상 큐레이션 강도", "value": priors.get("sasang_scalar")},
        {
            "key": "myeongni_day_pillar_prior_hypo",
            "label_ko": "명리 일주 prior",
            "value": priors.get("myeongni_day_pillar_prior_hypo"),
        },
        {"key": "wellness_hypo_budget", "label_ko": "웰니스 예산 [HYPO]", "value": priors.get("wellness_hypo_budget")},
    ]

    return {
        "schema": "hyper_personal_news_intake_mkmlife_card_v1",
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": intake.get("generated_at_utc") or _utc_now(),
        "regime_id": field.get("regime_id"),
        "decision_label": final.get("decision_label", "WATCH"),
        "cms_publish_allowed": final.get("cms_publish_allowed", False),
        "one_line_ko": final.get("one_line_ko"),
        "disclaimer_ko": final.get("disclaimer_ko")
        or "§10 shadow 산출물; 실서비스·소비자 앱·투자 권유 아님.",
        "priors_display": prior_rows,
        "lenses_summary_ko": {
            "sasang": (intake.get("lenses") or {}).get("sasang", {}).get("summary_ko"),
            "myeongni": (intake.get("lenses") or {}).get("myeongni", {}).get("summary_ko"),
            "logos": (intake.get("lenses") or {}).get("logos", {}).get("summary_ko"),
        },
        "dual_compression": {
            "raw_token_saving": raw_saving,
            "hp_token_saving": hp_saving,
            "delta_hp_minus_baseline": delta,
            "interpretation_ko": "operational(HP)은 research_only; raw와 합쳐 승격 근거로 쓰지 않음.",
            "measurement_status": hp_bench.get("measurement_status"),
        },
        "refs": {
            "intake": _rel(DEFAULT_INTAKE),
            "hp_bench": _rel(DEFAULT_HP_BENCH) if hp_bench else None,
            "raw_bench": _rel(DEFAULT_RAW_BENCH) if raw_bench else None,
        },
        "forbidden": [
            "Not Track A or CMS promotion proof.",
            "Not live trading or consumer app launch.",
            "Logos lens is NON_GATING auxiliary only.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake-json", type=Path, default=DEFAULT_INTAKE)
    ap.add_argument("--hp-bench-json", type=Path, default=DEFAULT_HP_BENCH)
    ap.add_argument("--raw-bench-json", type=Path, default=DEFAULT_RAW_BENCH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    args = ap.parse_args()

    intake = _read(args.intake_json.resolve())
    if not intake or intake.get("schema") != "hyper_personal_news_intake_v1":
        raise SystemExit(f"missing or invalid intake: {args.intake_json}")

    card = facade_hyper_personal_card(
        build_card(intake, _read(args.hp_bench_json.resolve()), _read(args.raw_bench_json.resolve()))
    )
    out = args.output_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": _rel(out), "decision_label": card["decision_label"]}, ensure_ascii=False))

    if args.copy_mkmlife_public:
        MKMLIFE_PUBLIC.mkdir(parents=True, exist_ok=True)
        dest = MKMLIFE_PUBLIC / "hyper_personal_news_intake_card_v1.json"
        dest.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(dest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
