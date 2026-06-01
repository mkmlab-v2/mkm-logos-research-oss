#!/usr/bin/env python3
"""Refresh Evidence Pack v0 index JSON from W0 artifacts (local, no network)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_public_evidence_pack_v0_index_latest.json"
TEMPLATE = DEFAULT_OUT
W0_POC = ROOT / "reports/customer_compression_stateless_poc_v1_latest.json"
TENANT_POC = ROOT / "reports/customer_compression_stateless_poc_enterprise_50_v1_latest.json"
READINESS = ROOT / "reports/compression_enterprise_summary_readiness_v1_latest.json"
METERING_APPENDIX = ROOT / "docs/final/artifacts/compression_b2b_pilot_metering_appendix_latest.json"
W0_CORPUS = ROOT / "data/compression/stateless_poc_smoke_v1.jsonl"
TENANT_CORPUS = ROOT / "data/compression/stateless_poc_enterprise_50_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _poc_summary(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {}
    agg = doc.get("aggregate") or {}
    return {
        "poc_generated_at_utc": doc.get("generated_at_utc"),
        "case_count": doc.get("case_count"),
        "cases_passed_jaccard_floor": (
            f"{doc.get('cases_passed_jaccard_floor', doc.get('cases_passed'))}/"
            f"{doc.get('case_count')}"
            if doc.get("case_count")
            else None
        ),
        "mean_token_saving_rate_proxy": agg.get("mean_token_saving_rate_proxy"),
        "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
    }


def build() -> dict[str, Any]:
    base = _load_json(TEMPLATE) or {}
    w0 = _load_json(W0_POC)
    tenant = _load_json(TENANT_POC)
    readiness = _load_json(READINESS) or {}

    w0_sum = _poc_summary(w0)
    tenant_sum = _poc_summary(tenant)

    w0_ssot = dict(base.get("w0_ssot") or {})
    w0_ssot.update(
        {
            "corpus_path": W0_CORPUS.relative_to(ROOT).as_posix(),
            "corpus_sha256": _sha256(W0_CORPUS),
            "poc_report_path": W0_POC.relative_to(ROOT).as_posix(),
            **{k: v for k, v in w0_sum.items() if v is not None},
        }
    )

    tenant_poc = dict(base.get("tenant_poc") or {})
    tenant_poc.update(
        {
            "tenant_id": "virtual-tenant-poc-01",
            "corpus_path": TENANT_CORPUS.relative_to(ROOT).as_posix(),
            "corpus_sha256": _sha256(TENANT_CORPUS),
            "poc_report_path": TENANT_POC.relative_to(ROOT).as_posix(),
            **{k: v for k, v in tenant_sum.items() if v is not None},
        }
    )
    metrics = dict(tenant_poc.get("metrics_guardrail") or {})
    if tenant_sum.get("mean_token_saving_rate_proxy") is not None:
        metrics["mean_token_saving_rate_proxy"] = tenant_sum["mean_token_saving_rate_proxy"]
    if tenant_sum.get("mean_jaccard_proxy") is not None:
        metrics["mean_jaccard_proxy"] = tenant_sum["mean_jaccard_proxy"]
    if tenant_sum.get("cases_passed_jaccard_floor"):
        metrics["cases_passed_jaccard_floor"] = tenant_sum["cases_passed_jaccard_floor"]
    tenant_poc["metrics_guardrail"] = metrics

    gov = dict(base.get("governance") or {})
    gov["ready_internal_pointer"] = READINESS.relative_to(ROOT).as_posix()
    if readiness.get("ready_for_internal_oem_draft") is not None:
        gov["ready_for_internal_oem_draft"] = readiness.get("ready_for_internal_oem_draft")

    out = dict(base)
    out["schema"] = "compression_public_evidence_pack_v0_index_v1"
    out["generated_at_utc"] = _utc_now()
    out["w0_ssot"] = w0_ssot
    out["tenant_poc"] = tenant_poc
    out["governance"] = gov
    out["index_refresh_script"] = "scripts/build_compression_public_evidence_pack_v0_index_v1.py"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "generated_at_utc": doc.get("generated_at_utc"),
                "tenant_poc_at": (doc.get("tenant_poc") or {}).get("poc_generated_at_utc"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
