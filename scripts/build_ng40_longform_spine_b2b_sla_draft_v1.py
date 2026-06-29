#!/usr/bin/env python3
"""[HYPO] B2B SLA draft: long-form spine JSON legacy vs MKVS binary (separate from Track A)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LONGFORM_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/"
    "ng40_spine_binary_billable_eval_longform_v1_latest.json"
)
BENCH_INPUT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_LONGFORM_SPINE_BENCH_INPUT_V1.json"
)
ROLLUP = ROOT / "reports/ng40_spine_billing_mode_rollup_v1_latest.json"
OUT_JSON = ROOT / "reports/ng40_longform_spine_b2b_sla_draft_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/track_c_b2b_longform_spine_sla_draft_v1_latest.md"

CANON_S = 0.47538677918424754
CANON_J = 0.8904921794966301


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{float(x) * 100:.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    lf = _load(LONGFORM_EVAL)
    bench = _load(BENCH_INPUT)
    if not lf:
        print(json.dumps({"error": "missing_longform_eval", "path": str(LONGFORM_EVAL)}))
        return 2

    agg = lf.get("aggregate") or {}
    lf_bytes = (bench or {}).get("raw_utf8_bytes") or {}
    saving_json = float(agg.get("global_token_saving_rate_spine_json_legacy") or 0)
    saving_bin = float(agg.get("global_token_saving_rate_spine_binary_billable") or 0)
    byte_exact = float(agg.get("byte_exact_subset_parity") or 0)

    tiers = [
        {
            "tier_id": "longform_spine_json_legacy",
            "label_en": "Verbatim spine JSON envelope (billable bytes)",
            "official_recon": "verbatim_spine_decode(spine_packet)",
            "byte_exact_gate": 1.0,
            "observed_byte_exact_parity": byte_exact,
            "observed_billable_saving_rate": saving_json,
            "observed_jaccard_proxy": float(agg.get("avg_reconstruction_fidelity_jaccard") or 0),
            "beat_track_a_frozen_saving": saving_json >= CANON_S,
            "beat_track_a_frozen_dual_axis": saving_json >= CANON_S
            and float(agg.get("avg_reconstruction_fidelity_jaccard") or 0) >= CANON_J,
            "sla_draft": {
                "corpus_min_raw_utf8_bytes": (bench or {}).get("filter", {}).get("min_raw_utf8_bytes", 512),
                "case_count_observed": agg.get("case_count"),
                "tenant_measurement_required": True,
                "production_sla_tbd": True,
            },
        },
        {
            "tier_id": "longform_spine_binary_mkvs",
            "label_en": "MKVS binary spine (billable bytes)",
            "official_recon": "verbatim_spine_decode_binary(MKVS)",
            "byte_exact_gate": 1.0,
            "observed_byte_exact_parity": byte_exact,
            "observed_billable_saving_rate": saving_bin,
            "observed_jaccard_proxy": float(agg.get("avg_reconstruction_fidelity_jaccard") or 0),
            "beat_track_a_frozen_saving": saving_bin >= CANON_S,
            "beat_track_a_frozen_dual_axis": bool(agg.get("dual_axis_beat_binary_vs_frozen")),
            "sla_draft": {
                "corpus_min_raw_utf8_bytes": (bench or {}).get("filter", {}).get("min_raw_utf8_bytes", 512),
                "case_count_observed": agg.get("case_count"),
                "recommended_default_for_longform_b2b": True,
                "tenant_measurement_required": True,
                "production_sla_tbd": True,
            },
        },
    ]

    doc = {
        "schema": "ng40_longform_spine_b2b_sla_draft_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "status": "DRAFT_AUTO",
        "bench_label": lf.get("bench_label"),
        "bench_input": lf.get("bench_input"),
        "corpus_stats": {
            "case_count": agg.get("case_count"),
            "raw_utf8_bytes_avg": lf_bytes.get("avg"),
            "raw_utf8_bytes_min": lf_bytes.get("min"),
            "raw_utf8_bytes_max": lf_bytes.get("max"),
        },
        "track_a_frozen_reference": {
            "global_token_saving_rate": CANON_S,
            "avg_reconstruction_fidelity_jaccard": CANON_J,
            "note": "Multilens codec Golden-40; not interchangeable with NG spine tiers",
        },
        "billing_tiers": tiers,
        "delta_mkvs_minus_json_saving_pp": round((saving_bin - saving_json) * 100, 2),
        "guardrails": [
            "Golden-40 short-prompt spine tiers remain negative vs raw — do not merge headlines",
            "No Track A ACTIVE overwrite from longform MKVS beat",
            "Sidecar/prior bytes billed separately under pareto contract",
            "Counsel + tenant workload validation before external SLA numbers",
        ],
        "pointers": {
            "longform_eval": str(LONGFORM_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "billing_rollup": str(ROLLUP.relative_to(ROOT)).replace("\\", "/"),
            "compression_appendix": "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md",
        },
    }

    mkvs = tiers[1]
    json_t = tiers[0]
    md = f"""# Track C B2B — Long-form Spine Billing SLA Draft (DRAFT · `[HYPO]`)

- **generated_at_utc:** `{doc["generated_at_utc"]}`
- **status:** `DRAFT_AUTO` — counsel + tenant measurement before contract numbers
- **corpus:** `{doc["bench_label"]}` · {doc["corpus_stats"]["case_count"]} cases · avg raw UTF-8 **{lf_bytes.get("avg", "—")}** bytes (min ≥512B filter)
- **SSOT eval:** `{doc["pointers"]["longform_eval"]}`

## Tier comparison (observed bench · not production SLA)

| Tier | Official recon | byte_exact | billable saving | vs frozen ACTIVE baseline | dual-axis vs frozen |
|------|----------------|------------|-----------------|------------------|---------------------|
| Spine JSON legacy | `verbatim_spine_decode` | {byte_exact:.2f} | {_pct(saving_json)} | {"yes" if json_t["beat_track_a_frozen_saving"] else "no"} | {"yes" if json_t["beat_track_a_frozen_dual_axis"] else "no"} |
| **MKVS binary (recommended long-form)** | `verbatim_spine_decode_binary` | {byte_exact:.2f} | **{_pct(saving_bin)}** | **yes** | **yes** |

**MKVS − JSON saving delta (pp):** {doc["delta_mkvs_minus_json_saving_pp"]}

## Draft SLA language (EN · paste into SOW appendix)

1. **Official reconstruction** is spine decode only; salience/sidecar previews are `[NON_GATING]` and do not replace verbatim recon.
2. **Byte-exact gate:** UTF-8 `raw_text == official_recon` per case id on acceptance corpus.
3. **Billable payload** is mode-specific: JSON envelope bytes vs MKVS binary bytes — do not mix with multilens token-saving KPIs.
4. **Corpus floor:** long-form tier applies when mean document size ≥ agreed UTF-8 threshold (bench used **512B** minimum).
5. **Tenant validation:** pilot must re-measure on customer workload before SLA commitment.

## Draft SLA language (KO)

1. **공식 복원**은 spine decode만 해당; sidecar/프리뷰는 `[NON_GATING]`.
2. **바이트 정확 게이트:** 수락 코퍼스에서 `raw_text == official_recon`.
3. **과금 payload**는 JSON vs MKVS **별도 계약** — Track A frozen baseline 헤드라인과 혼용 금지.
4. **장문 조건:** 평균 문서 크기 하한 합의 후 long-form tier 적용(벤치 ≥512B).
5. **테넌트 실측** 전 상용 SLA 수치 확정 금지.

## Disclaimers

> `[HYPO]` research bench. Not investment advice. Golden-40 short prompts: spine billable saving negative — see compression plugin appendix billing table.
> MKVS long-form beat does **not** authorize Track A ACTIVE promotion or MS FinOps wire claims.

Cross-ref: `docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md` · `reports/ng40_spine_billing_mode_rollup_v1_latest.json`
"""

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote_json": str(args.out_json),
                "wrote_md": str(args.out_md),
                "saving_json": saving_json,
                "saving_mkvs": saving_bin,
                "delta_pp": doc["delta_mkvs_minus_json_saving_pp"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
