#!/usr/bin/env python3
"""[HYPO] Judges/chasm domain-conditional corpus ablation on masked customer JSONL.

b2b-evaluation + security-review -> spine_binary arm
other domains -> economy token-proxy arm (stateless PoC)
research_only · send_gate HOLD · no ACTIVE promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_latent_codec_v1 import jaccard_text
from scripts.nextgen_verbatim_spine_codec_v1 import (
    verbatim_spine_decode_binary,
    verbatim_spine_encode,
    verbatim_spine_packet_to_binary,
)

DEFAULT_JSONL = ROOT / "data/compression/tactical_b_free_audit_pilot_v1.jsonl"
DEFAULT_BENCH = ROOT / "data/compression/tactical_b_free_audit_spine_bench_v1.json"
DEFAULT_OUT = ROOT / "reports/compression_judges_chasm_corpus_conditional_ablation_v1_latest.json"
POC_OUT = ROOT / "reports/customer_compression_stateless_poc_path-a-masked-cohort-v1_v1_latest.json"
SCHEMA = "compression_judges_chasm_corpus_conditional_ablation_v1"
CHASM_DOMAINS = frozenset({"b2b-evaluation", "security-review"})
TENANT_ID = "path-a-masked-cohort-v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _mean(vals: list[float]) -> float | None:
    return round(sum(vals) / len(vals), 6) if vals else None


def pick_judges_chasm_arm(domain_tag: str | None) -> str:
    if (domain_tag or "").strip() in CHASM_DOMAINS:
        return "spine_binary_chasm"
    return "economy_token_proxy"


def _spine_metrics(raw: str) -> tuple[float, float]:
    pkt = verbatim_spine_encode(raw)
    blob = verbatim_spine_packet_to_binary(pkt)
    recon = verbatim_spine_decode_binary(blob)
    rb = len(raw.encode("utf-8"))
    bb = len(blob)
    saving = 1.0 - (bb / max(1, rb))
    j = jaccard_text(raw, recon)
    return round(saving, 6), round(j, 6)


def _poc_by_suffix(poc_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in poc_doc.get("cases") or []:
        rid = str(row.get("id") or "")
        suffix = rid.rsplit("-", 1)[-1]
        out[suffix] = row
    return out


def build(*, bench_path: Path, poc_path: Path) -> dict[str, Any]:
    bench = _load(bench_path)
    poc_doc = _load(poc_path)
    if not bench:
        raise FileNotFoundError(f"missing bench: {bench_path}")
    if not poc_doc:
        raise FileNotFoundError(f"missing poc: {poc_path} — run path A customer cohort chain first")

    poc_idx = _poc_by_suffix(poc_doc)
    merged_rows: list[dict[str, Any]] = []
    policy_counts: dict[str, int] = {}

    for case in bench.get("compression_cases") or []:
        cid = str(case.get("id"))
        domain = case.get("domain_tag")
        raw = str(case.get("raw_text") or "")
        policy = pick_judges_chasm_arm(domain)
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
        suffix = cid.rsplit("-", 1)[-1]
        if policy == "spine_binary_chasm":
            saving, jaccard = _spine_metrics(raw)
            arm = "spine_binary_chasm"
        else:
            src = poc_idx.get(suffix) or {}
            saving = float(src.get("token_saving_rate_proxy") or poc_doc.get("mean_token_saving_rate_proxy") or 0)
            jaccard = float(src.get("jaccard_proxy") or poc_doc.get("mean_jaccard_proxy") or 0)
            arm = "economy_token_proxy"
        merged_rows.append(
            {
                "id": cid,
                "domain_tag": domain,
                "policy": policy,
                "arm": arm,
                "token_saving_rate_proxy": saving,
                "jaccard_proxy": jaccard,
            }
        )

    def _agg(rows_in: list[dict[str, Any]]) -> dict[str, Any]:
        savings = [float(r["token_saving_rate_proxy"]) for r in rows_in]
        jacs = [float(r["jaccard_proxy"]) for r in rows_in]
        return {
            "case_count": len(rows_in),
            "mean_token_saving_rate_proxy": _mean(savings),
            "mean_jaccard_proxy": _mean(jacs),
        }

    spine_rows = [r for r in merged_rows if r["arm"] == "spine_binary_chasm"]
    economy_rows = [r for r in merged_rows if r["arm"] == "economy_token_proxy"]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "bench_pointer": str(bench_path.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(merged_rows),
        "chasm_domains": sorted(CHASM_DOMAINS),
        "policy_counts": policy_counts,
        "arms": {
            "spine_global_chasm_domains": _agg(spine_rows),
            "economy_global_other_domains": _agg(economy_rows),
            "conditional_merged": _agg(merged_rows),
        },
        "evidence_pointers": {
            "bench": str(bench_path.relative_to(ROOT)).replace("\\", "/"),
            "economy_poc": str(poc_path.relative_to(ROOT)).replace("\\", "/"),
            "path_a_chain": "reports/ng40_path_a_customer_masked_cohort_chain_v1_latest.json",
        },
        "verdict_ko": [
            "Judges/chasm: b2b+security → spine byte path; 나머지 → economy proxy",
            "conditional merge는 연구 헤드라인만 — ACTIVE/latent 47% 합선 금지",
        ],
        "forbidden": [
            "Track A promotion from conditional uplift",
            "merge with MULTILENS_ULTRA_COMPRESSION_ACTIVE headline",
        ],
        "reproducible_command": "py scripts/run_compression_judges_chasm_corpus_conditional_ablation_v1.py",
        "sample_rows": merged_rows[:6],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--poc-json", type=Path, default=POC_OUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bench = args.bench_json if args.bench_json.is_absolute() else ROOT / args.bench_json
    poc = args.poc_json if args.poc_json.is_absolute() else ROOT / args.poc_json

    try:
        doc = build(bench_path=bench, poc_path=poc)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "conditional_saving": doc["arms"]["conditional_merged"]["mean_token_saving_rate_proxy"],
                "policy_counts": doc["policy_counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
