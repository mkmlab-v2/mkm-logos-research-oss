#!/usr/bin/env python3
"""Industry SKU PoC gap report — pass rates, ad-readiness guardrails."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_b2b_industry_sku_gap_report_v1_latest.json"
JACCARD_FLOOR = 0.73


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gap_row(step: dict[str, Any]) -> dict[str, Any]:
    case_count = step.get("case_count") or 0
    passed = step.get("cases_passed") or 0
    saving = step.get("mean_token_saving_rate_proxy")
    jac = step.get("mean_jaccard_proxy")
    pass_rate = round(passed / case_count, 4) if case_count else 0.0
    ad_ready = (
        pass_rate >= 0.5
        and isinstance(saving, (int, float))
        and saving >= 0.08
        and isinstance(jac, (int, float))
        and jac >= JACCARD_FLOOR
    )
    return {
        "external_sku": step.get("external_sku"),
        "forced_shard_id": step.get("forced_shard_id"),
        "case_count": case_count,
        "cases_passed_jaccard_floor": passed,
        "pass_rate": pass_rate,
        "raw": {
            "mean_token_saving_rate_proxy": saving,
            "mean_jaccard_proxy": jac,
            "saving_pct": round(float(saving) * 100, 2) if isinstance(saving, (int, float)) else None,
        },
        "repair_v2": {
            "mean_token_saving_rate_proxy": saving,
            "mean_jaccard_proxy": jac,
            "repair_applied_count": 0,
            "note": "stateless PoC — no separate repair processor",
        },
        "delta": {"token_saving_rate_delta_repair_v2_minus_raw": 0.0},
        "internal_demo_ready": pass_rate >= 0.3 and isinstance(jac, (int, float)) and jac >= 0.85,
        "ad_headline_ready": False,
        "ad_headline_blockers": [
            "send_gate HOLD",
            "research_only corpus",
            "pass_rate below 50% or saving below 8%" if not ad_ready else None,
            "not third-party reproduced",
        ],
        "improvement_hints": [
            "must_keep overlay + hydrate compare (B1 B+C)",
            "expand industry corpus to 30+ rows per SKU",
            "loss profile A/B: semantic_general vs code_equivalent",
        ],
    }


def build(bundle_path: Path = BUNDLE) -> dict[str, Any]:
    bundle = _load(bundle_path)
    steps = bundle.get("steps") if isinstance(bundle.get("steps"), list) else []
    rows = [_gap_row(s) for s in steps if isinstance(s, dict)]
    for r in rows:
        r["ad_headline_blockers"] = [b for b in r.get("ad_headline_blockers") or [] if b]
    any_internal = any(r.get("internal_demo_ready") for r in rows)
    return {
        "schema": "compression_b2b_industry_sku_gap_report_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "bundle_ok": bundle.get("bundle_ok"),
        "bundle_path": bundle_path.relative_to(ROOT).as_posix() if bundle_path.is_file() else None,
        "jaccard_floor_ref": JACCARD_FLOOR,
        "sku_rows": rows,
        "summary": {
            "sku_count": len(rows),
            "any_internal_demo_ready": any_internal,
            "any_ad_headline_ready": False,
            "median_pass_rate": round(
                sorted(r["pass_rate"] for r in rows)[len(rows) // 2] if rows else 0.0,
                4,
            ),
            "note_ko": "내부 데모 가능 SKU 있어도 광고·뉴스 헤드라인은 SEND_GATE·재현성 미충족으로 금지",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=BUNDLE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build(args.bundle_json.resolve())
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "sku_count": doc["summary"]["sku_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
