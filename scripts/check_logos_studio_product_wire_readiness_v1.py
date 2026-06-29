#!/usr/bin/env python3
"""Fuse June eval + July band + WF digest into product wire readiness [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AB_BENCH = ROOT / "docs/final/artifacts/logos_studio_graphrag_insight_ab_bench_v1_latest.json"
BAND_GATE = ROOT / "docs/final/artifacts/myeongni_sasang_graphrag_ollama_live_bench_gate_v1_latest.json"
WF_DIGEST = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_studio_product_wire_readiness_v1_latest.json"
REPORT_OUT = ROOT / "reports/logos_studio_product_wire_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    ab = _read(AB_BENCH)
    band = _read(BAND_GATE)
    wf = _read(WF_DIGEST)

    ab_ok = ab.get("schema") == "logos_studio_graphrag_insight_ab_bench_v1"
    band_ok = band.get("ok") is True and band.get("wires_to_scoring_core") is False
    wf_ok = wf.get("schema") == "kospi_lens_ablation_backtest_v1" and wf.get("graphrag_sidebar_wires_scoring") is False

    out = {
        "schema": "logos_studio_product_wire_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ab_ok and band_ok and wf_ok,
        "checks": {
            "june_eval_ab_present": ab_ok,
            "july_band_gate_present": band_ok,
            "wf_digest_present": wf_ok,
        },
        "june_eval": {
            "rows": (ab.get("summary") or {}).get("rows"),
            "on_win_rate": (ab.get("summary") or {}).get("on_win_rate"),
            "mean_total_delta_on_minus_off": (ab.get("summary") or {}).get("mean_total_delta_on_minus_off"),
            "artifact": str(AB_BENCH),
        },
        "july_band": {
            "router_hit_all": (band.get("summary") or {}).get("router_hit_all"),
            "mean_live_char_savings_ratio": (band.get("summary") or {}).get("mean_live_char_savings_ratio"),
            "wires_to_scoring_core": band.get("wires_to_scoring_core"),
            "artifact": str(BAND_GATE),
        },
        "wf_digest": {
            "best_arm": ((wf.get("best_arm") or {}).get("arm_id")),
            "best_soft_hit_rate": (((wf.get("best_arm") or {}).get("metrics") or {}).get("soft_hit_rate")),
            "graphrag_sidebar_wires_scoring": wf.get("graphrag_sidebar_wires_scoring"),
            "artifact": str(WF_DIGEST),
        },
        "public_facing_contract": {
            "tag": "[NON_GATING]",
            "copy_ko": "GraphRAG는 해설·감사 보조 레일이며 scoring core에 비주입입니다. 제품 UI는 research_only 문맥에서만 노출합니다.",
            "track_a_promotion_allowed": False,
        },
        "reproduce": "py scripts/check_logos_studio_product_wire_readiness_v1.py",
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": out["ok"], "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
