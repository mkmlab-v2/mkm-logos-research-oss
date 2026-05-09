#!/usr/bin/env python3
"""B-track benchmark: decoder-side restoration loss mitigation (no encoder change)."""

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

from scripts.report_multilens_performance_eval import (
    _jaccard,
    _reconstruct_experimental_from_raw,
)

DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "decoder_loss_mitigation_benchmark_v1.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Benchmark decoder-side loss mitigation on active B-track report.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input case corpus with raw_text by id")
    p.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE, help="Active report JSON to replay")
    p.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output benchmark JSON path")
    p.add_argument("--write-mitigated-report", type=Path, default=None, help="Optional output for mitigated full report")
    return p


def _mean(xs: list[float]) -> float:
    return (sum(xs) / len(xs)) if xs else 0.0


def _is_hangul_text(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def main() -> int:
    args = _parser().parse_args()
    input_doc = json.loads(args.input.read_text(encoding="utf-8"))
    active_doc = json.loads(args.active_report.read_text(encoding="utf-8"))

    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in input_doc.get("compression_cases", [])}
    use_hangul = bool((active_doc.get("run_config") or {}).get("use_hangul_principle", False))
    before_cases = (active_doc.get("compression_metrics") or {}).get("cases") or []

    improved = 0
    regressed = 0
    unchanged = 0
    case_rows: list[dict[str, Any]] = []
    after_jaccards: list[float] = []
    mitigated_cases: list[dict[str, Any]] = []
    total_delta = 0.0
    hangul_before_jaccards: list[float] = []
    hangul_after_jaccards: list[float] = []
    hangul_improved = 0
    hangul_regressed = 0
    hangul_total = 0

    for row in before_cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        comp = str(row.get("compressed_text_effective", ""))
        is_hangul_case = _is_hangul_text(raw)
        before_rec = _reconstruct_experimental_from_raw(
            raw=raw,
            compressed_candidate=comp,
            use_hangul_principle=use_hangul,
            enable_loss_pattern_mitigation=False,
        )
        before_j = _jaccard(raw, before_rec)

        after_rec = _reconstruct_experimental_from_raw(
            raw=raw,
            compressed_candidate=comp,
            use_hangul_principle=use_hangul,
            enable_loss_pattern_mitigation=True,
        )
        after_j = _jaccard(raw, after_rec)
        delta = after_j - before_j
        total_delta += delta
        after_jaccards.append(after_j)

        if delta > 1e-12:
            improved += 1
        elif delta < -1e-12:
            regressed += 1
        else:
            unchanged += 1
        if is_hangul_case:
            hangul_total += 1
            hangul_before_jaccards.append(before_j)
            hangul_after_jaccards.append(after_j)
            if delta > 1e-12:
                hangul_improved += 1
            elif delta < -1e-12:
                hangul_regressed += 1

        out_row = {
            "id": cid,
            "domain": (row.get("route") or {}).get("domain") if isinstance(row.get("route"), dict) else None,
            "is_hangul_case": is_hangul_case,
            "before_jaccard": before_j,
            "after_jaccard": after_j,
            "delta_jaccard": delta,
            "token_saving_rate": float(row.get("token_saving_rate", 0.0)),
            "before_reconstructed_text": before_rec,
            "after_reconstructed_text": after_rec,
        }
        case_rows.append(out_row)

        new_case = dict(row)
        new_case["reconstructed_text_effective"] = after_rec
        new_case["reconstruction_fidelity_jaccard"] = after_j
        mitigated_cases.append(new_case)

    before_metrics = active_doc.get("compression_metrics") or {}
    quality_gate = active_doc.get("quality_gate") or {}
    before_jaccards = [float(r["before_jaccard"]) for r in case_rows]
    before_avg_j = _mean(before_jaccards)
    before_min_j = min(before_jaccards) if before_jaccards else 0.0
    before_saving = float(before_metrics.get("global_token_saving_rate", 0.0))
    before_avg_sensitive = float(before_metrics.get("avg_sensitive_integrity", 1.0))
    before_min_sensitive = float(before_metrics.get("min_sensitive_integrity", 1.0))

    after_avg_j = _mean(after_jaccards)
    after_min_j = min(after_jaccards) if after_jaccards else 0.0
    after_saving = before_saving  # decoder-only mitigation: compression payload unchanged
    after_avg_sensitive = before_avg_sensitive  # unchanged by design (candidate not modified)
    after_min_sensitive = before_min_sensitive

    case_rows_sorted = sorted(case_rows, key=lambda r: r["delta_jaccard"], reverse=True)
    hangul_before_avg = _mean(hangul_before_jaccards)
    hangul_after_avg = _mean(hangul_after_jaccards)
    hangul_before_min = min(hangul_before_jaccards) if hangul_before_jaccards else 0.0
    hangul_after_min = min(hangul_after_jaccards) if hangul_after_jaccards else 0.0
    hold_for_hangul = (
        hangul_total > 0
        and (hangul_after_avg - hangul_before_avg) > 0.0
        and hangul_regressed == 0
    )
    recommended_toggle = "on" if regressed == 0 and hold_for_hangul else "off"
    summary = {
        "schema": "btrack_decoder_loss_mitigation_benchmark_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "input": str(args.input.resolve()),
            "active_report": str(args.active_report.resolve()),
        },
        "method": {
            "type": "decoder_only_mitigation",
            "encoder_or_candidate_changes": False,
            "guardrail_policy_changes": False,
            "use_hangul_principle": use_hangul,
            "quality_gate_sensitive_integrity_ok_before": bool(quality_gate.get("sensitive_integrity_ok", False)),
            "quality_gate_sensitive_integrity_ok_after_assumed": bool(quality_gate.get("sensitive_integrity_ok", False)),
            "note": "Before/after both use the same heuristic decoder; only mitigation toggle differs.",
        },
        "metrics": {
            "before": {
                "avg_reconstruction_fidelity_jaccard": before_avg_j,
                "min_reconstruction_fidelity_jaccard": before_min_j,
                "global_token_saving_rate": before_saving,
                "avg_sensitive_integrity": before_avg_sensitive,
                "min_sensitive_integrity": before_min_sensitive,
            },
            "after": {
                "avg_reconstruction_fidelity_jaccard": after_avg_j,
                "min_reconstruction_fidelity_jaccard": after_min_j,
                "global_token_saving_rate": after_saving,
                "avg_sensitive_integrity": after_avg_sensitive,
                "min_sensitive_integrity": after_min_sensitive,
            },
            "delta": {
                "avg_reconstruction_fidelity_jaccard": after_avg_j - before_avg_j,
                "min_reconstruction_fidelity_jaccard": after_min_j - before_min_j,
                "global_token_saving_rate": after_saving - before_saving,
                "avg_sensitive_integrity": after_avg_sensitive - before_avg_sensitive,
                "min_sensitive_integrity": after_min_sensitive - before_min_sensitive,
            },
        },
        "tradeoff": {
            "improved_case_count": improved,
            "regressed_case_count": regressed,
            "unchanged_case_count": unchanged,
            "mean_delta_jaccard_per_case": (total_delta / len(case_rows)) if case_rows else 0.0,
        },
        "hangul_subset": {
            "case_count": hangul_total,
            "before_avg_reconstruction_fidelity_jaccard": hangul_before_avg,
            "after_avg_reconstruction_fidelity_jaccard": hangul_after_avg,
            "delta_avg_reconstruction_fidelity_jaccard": hangul_after_avg - hangul_before_avg,
            "before_min_reconstruction_fidelity_jaccard": hangul_before_min,
            "after_min_reconstruction_fidelity_jaccard": hangul_after_min,
            "delta_min_reconstruction_fidelity_jaccard": hangul_after_min - hangul_before_min,
            "improved_case_count": hangul_improved,
            "regressed_case_count": hangul_regressed,
            "improvement_holds": hold_for_hangul,
        },
        "recommendation": {
            "decoder_loss_pattern_mitigation_toggle": recommended_toggle,
            "rationale": (
                "Enable by default for future sweeps: no global regressions and Hangul subset improves."
                if recommended_toggle == "on"
                else "Keep off by default: either global regressions observed or Hangul subset did not hold."
            ),
        },
        "top_changes": {
            "top_improved": case_rows_sorted[:10],
            "top_regressed": sorted(case_rows, key=lambda r: r["delta_jaccard"])[:10],
        },
        "cases": case_rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")

    if args.write_mitigated_report is not None:
        out_report = dict(active_doc)
        out_report["run_config"] = dict(out_report.get("run_config") or {})
        out_report["run_config"]["decoder_loss_pattern_mitigation"] = True
        out_report["compression_metrics"] = dict(out_report.get("compression_metrics") or {})
        out_report["compression_metrics"]["cases"] = mitigated_cases
        out_report["compression_metrics"]["avg_reconstruction_fidelity_jaccard"] = after_avg_j
        out_report["compression_metrics"]["min_reconstruction_fidelity_jaccard"] = after_min_j
        args.write_mitigated_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_mitigated_report.write_text(
            json.dumps(out_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"WROTE: {args.write_mitigated_report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

