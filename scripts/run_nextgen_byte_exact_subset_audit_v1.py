#!/usr/bin/env python3
"""[HYPO] Byte-exact restore audit on Golden-40 bench cases (NG-40 evaluate_report path)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    ACTIVE,
    INPUT_V2,
    evaluate_ng40_lane,
)

OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_byte_exact_subset_v1_latest.json"
)
BEST_CAPS = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_best_caps(path: Path) -> tuple[float, float, float, bool]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rc = doc.get("run_config_summary") or {}
    return (
        float(rc.get("general_max_saving_rate", 0.32)),
        float(rc.get("sensitive_max_saving_rate", 0.28)),
        float(rc.get("hangul_max_saving_rate", 0.55)),
        bool(rc.get("with_domain_relaxed", False)),
    )


def _audit_lane(
    *,
    label: str,
    use_lexicon: bool,
    active_parity: bool,
    general_cap: float,
    sensitive_cap: float,
    hangul_cap: float,
    domain_relaxed: bool,
) -> dict[str, Any]:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8-sig"))
    raw_by_id = {
        str(c.get("id", "")): str(c.get("raw_text", ""))
        for c in (doc.get("compression_cases") or [])
    }
    agg, report = evaluate_ng40_lane(
        doc,
        bench_input=INPUT_V2,
        general_cap=general_cap,
        sensitive_cap=sensitive_cap,
        hangul_cap=hangul_cap,
        use_domain_relaxed=domain_relaxed,
        use_master_codebook_lexicon_v1=use_lexicon,
        active_track_parity=active_parity,
    )
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    mismatches: list[dict[str, Any]] = []
    exact = 0
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        ok = raw == rec
        if ok:
            exact += 1
        else:
            mismatches.append(
                {
                    "id": cid,
                    "raw_len": len(raw.encode("utf-8")),
                    "rec_len": len(rec.encode("utf-8")),
                    "jaccard": row.get("reconstruction_fidelity_jaccard"),
                }
            )
    n = len(cases)
    parity = (exact / n) if n else 0.0
    return {
        "arm_label": label,
        "use_master_codebook_lexicon_v1": use_lexicon,
        "active_track_parity": active_parity,
        "case_count": n,
        "byte_exact_count": exact,
        "byte_exact_subset_parity": round(parity, 6),
        "parity_target_met": parity >= 1.0,
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:8],
        "aggregate_metrics": agg,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--best-caps-json", type=Path, default=BEST_CAPS)
    args = parser.parse_args()

    if not INPUT_V2.is_file():
        print(json.dumps({"error": "missing_bench_input", "path": str(INPUT_V2)}))
        return 2

    g, s, h, relaxed = _load_best_caps(args.best_caps_json)
    arms = [
        _audit_lane(
            label="41k OFF · best caps",
            use_lexicon=False,
            active_parity=False,
            general_cap=g,
            sensitive_cap=s,
            hangul_cap=h,
            domain_relaxed=relaxed,
        ),
        _audit_lane(
            label="41k ON · best caps · ACTIVE parity",
            use_lexicon=True,
            active_parity=True,
            general_cap=g,
            sensitive_cap=s,
            hangul_cap=h,
            domain_relaxed=relaxed,
        ),
        _audit_lane(
            label="41k ON · ACTIVE caps · domain_relaxed",
            use_lexicon=True,
            active_parity=True,
            general_cap=0.35,
            sensitive_cap=0.30,
            hangul_cap=0.60,
            domain_relaxed=True,
        ),
    ]

    out = {
        "schema": "nextgen_byte_exact_subset_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "bench_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "best_caps_source": (
            str(args.best_caps_json.relative_to(ROOT)).replace("\\", "/")
            if args.best_caps_json.is_file()
            else None
        ),
        "active_report_present": ACTIVE.is_file(),
        "arms": arms,
        "guardrails": [
            "Byte-exact is separate from Jaccard beat; both required before Exact Restore Parity claim",
            "Does not auto-write ACTIVE or MS headline",
        ],
        "stub_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/"
            "SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "off_parity": arms[0]["byte_exact_subset_parity"],
                "on_best_parity": arms[1]["byte_exact_subset_parity"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
