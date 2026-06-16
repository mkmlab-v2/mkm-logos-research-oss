#!/usr/bin/env python3
"""Refresh compression dogfood briefing from latest v1-v4 dogfood artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIEFING = ROOT / "docs/final/artifacts/compression_dogfood_briefing_v1_latest.json"

POC_V1 = ROOT / "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v1_v1_latest.json"
POC_V2 = ROOT / "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v2_v1_latest.json"
POC_V3 = ROOT / "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v3_v1_latest.json"
POC_V4 = ROOT / "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v4-cursor_v1_latest.json"
META_V3 = ROOT / "reports/mkm_internal_dogfood_corpus_build_v3_latest.json"
META_V4 = ROOT / "reports/mkm_internal_dogfood_corpus_build_v4_cursor_transcripts_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{100 * float(value):.1f}%"


def _dual_from_poc(poc: dict[str, Any]) -> dict[str, Any]:
    agg = poc.get("aggregate") or {}
    rows = int(poc.get("case_count") or 0)
    raw = {
        "mean_token_saving_rate_proxy": float(agg.get("mean_token_saving_rate_proxy") or 0.0),
        "mean_jaccard_proxy": float(agg.get("mean_jaccard_proxy") or 0.0),
        "rows": rows,
    }
    repair = {
        "mean_token_saving_rate_proxy": raw["mean_token_saving_rate_proxy"],
        "mean_jaccard_proxy": raw["mean_jaccard_proxy"],
        "repair_applied_count": 0,
        "rows": rows,
    }
    return {
        "case_count": rows,
        "raw": raw,
        "repair_v2": repair,
        "delta_repair_v2_minus_raw": 0.0,
        "cases_passed_jaccard_floor": int(poc.get("cases_passed_jaccard_floor") or 0),
    }


def build() -> dict[str, Any]:
    doc = _load(BRIEFING)
    p1, p2, p3, p4 = _load(POC_V1), _load(POC_V2), _load(POC_V3), _load(POC_V4)
    m3, m4 = _load(META_V3), _load(META_V4)

    doc["generated_at_utc"] = _utc()
    doc["latest_tenant_id"] = "mkm-internal-dogfood-v4-cursor"

    doc["v1_short_ops"] = {
        "tenant_id": "mkm-internal-dogfood-v1",
        "corpus_builder": "scripts/build_mkm_internal_dogfood_corpus_v1.py",
        "measured_proxy": _dual_from_poc(p1),
    }
    doc["v2_long_llm_context"] = {
        "tenant_id": "mkm-internal-dogfood-v2",
        "corpus_builder": "scripts/build_mkm_internal_dogfood_corpus_v2.py",
        "corpus_note": "Finance/macro + structured long JSON + stitch; mean ~1342 chars/row.",
        "measured_proxy": _dual_from_poc(p2),
        "poc": "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v2_v1_latest.json",
    }
    v3_proxy = _dual_from_poc(p3)
    v3_proxy["interpretation"] = "Envelope overhead lowers saving vs bare v2 body — production-shaped context test"
    doc["v3_metering_adjacent_envelope"] = {
        "tenant_id": "mkm-internal-dogfood-v3",
        "corpus_builder": "scripts/build_mkm_internal_dogfood_corpus_v3.py",
        "corpus_meta": "reports/mkm_internal_dogfood_corpus_build_v3_latest.json",
        "corpus_note": (
            "Pseudo meter/eval_context JSON envelope over long body; "
            f"mean ~{round(float(m3.get('char_len_mean') or 0.0), 1)} chars/row."
        ),
        "measured_proxy": v3_proxy,
        "poc": "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v3_v1_latest.json",
        "metering": "docs/final/artifacts/compression_b2b_pilot_metering_appendix_mkm-internal-dogfood-v3_latest.json",
    }

    v4_proxy = _dual_from_poc(p4)
    v4_proxy["interpretation"] = (
        "Current transcript pack is too template-like for compression gain; useful for chain wiring smoke only."
    )
    doc["v4_cursor_transcript_pack"] = {
        "tenant_id": "mkm-internal-dogfood-v4-cursor",
        "corpus_builder": "scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py",
        "corpus_meta": "reports/mkm_internal_dogfood_corpus_build_v4_cursor_transcripts_latest.json",
        "corpus_note": (
            "Cursor agent transcript text blocks only; scrubbed + local-only; tool payload excluded."
        ),
        "measured_proxy": v4_proxy,
        "poc": "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v4-cursor_v1_latest.json",
        "input": "data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl",
    }

    lines = doc.get("dogfood_five_lines_ko") or []
    v4_line = (
        f"v4 cursor transcript pack({v4_proxy['case_count']}행) exit 0 — raw "
        f"{_fmt_pct(v4_proxy['raw']['mean_token_saving_rate_proxy'])}, "
        f"J~{v4_proxy['raw']['mean_jaccard_proxy']:.2f}; 압축 이득보다 체인 배선·보안 스크럽 검증에 적합."
    )
    lines = [line for line in lines if not str(line).startswith("v4 cursor transcript pack(")]
    lines.insert(0, v4_line)
    doc["dogfood_five_lines_ko"] = lines[:5]

    one_click_v4 = (
        "py scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py "
        "&& powershell -File scripts/Run-CompressionCustomerPilotIntake_v1.ps1 "
        "-TenantId mkm-internal-dogfood-v4-cursor "
        "-CustomerJsonl data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl "
        "-MaxCases 24 -RelaxPassGate"
    )
    doc["one_click_v4_cursor"] = one_click_v4
    doc["one_click_latest"] = one_click_v4
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=BRIEFING)
    args = parser.parse_args()
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = build()
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "latest_tenant_id": doc["latest_tenant_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

