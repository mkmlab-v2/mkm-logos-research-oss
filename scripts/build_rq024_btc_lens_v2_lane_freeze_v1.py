#!/usr/bin/env python3
"""[HYPO] RQ-024 v2 prediction lane freeze record — ablation readout from nf5 smoke."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DEFAULT = ROOT / "reports/rq024_btc_lens_v2_nf5_wf_smoke_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/rq024_btc_lens_v2_prediction_lane_freeze_v1_latest.json"
SCHEMA = "rq024_btc_lens_v2_prediction_lane_freeze_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def build(*, smoke_path: Path) -> dict[str, Any]:
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    v1 = smoke.get("v1_aggregate") or {}
    v2 = smoke.get("v2_aggregate") or {}
    v1_mean = float(v1.get("mean_test_accuracy") or 0)
    v2_mean = float(v2.get("mean_test_accuracy") or 0)
    delta = float(smoke.get("delta_mean_v2_minus_v1") or (v2_mean - v1_mean))

    freeze = delta < 0.0 or v2_mean < v1_mean
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "lane": "v2_volume_intraday_features",
        "status": "frozen_r_and_d" if freeze else "continue_ablation",
        "smoke_pointer": _rel(smoke_path),
        "v1_mean_test_accuracy_nf5": v1_mean,
        "v2_mean_test_accuracy_nf5": v2_mean,
        "delta_v2_minus_v1": round(delta, 6),
        "gate_055": {
            "v1_pass": v1_mean >= 0.55,
            "v2_pass": v2_mean >= 0.55,
            "note": "research_only — not Track A promotion",
        },
        "ablation_verdict_ko": (
            "v2 7축 full grid는 v1 대비 성능 감쇠 — volume/intraday 피처 단순 주입 중단·동결. "
            "후속은 피처 선택·v1+1축 또는 별도 가설 lane에서만."
            if freeze
            else "v2가 v1 이상 — 제한적 ablation 계속 가능"
        ),
        "forbidden": [
            "Track A or live trading auto-merge from v2",
            "0.55 gate success claim from v2 smoke alone",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke-json", type=Path, default=SMOKE_DEFAULT)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args(argv)

    smoke_path = args.smoke_json if args.smoke_json.is_absolute() else ROOT / args.smoke_json
    if not smoke_path.is_file():
        raise SystemExit(f"missing smoke: {smoke_path}")

    doc = build(smoke_path=smoke_path)
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"status={doc['status']} delta={doc['delta_v2_minus_v1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
