#!/usr/bin/env python3
"""Golden 40-case bench regression gate after zone_* shard changes or ultra re-eval.

Compares active multilens report metrics to floors (decision/bench aligned).
Does not modify MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "reports/compression_golden_bench_regression_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(report: dict[str, Any], key: str) -> float | int | None:
    block = report.get("compression_metrics")
    if not isinstance(block, dict):
        return None
    v = block.get(key)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden bench regression vs Track A floors.")
    ap.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-global-token-saving-rate", type=float, default=0.45)
    ap.add_argument("--min-avg-jaccard", type=float, default=0.87)
    ap.add_argument("--max-sensitive-violations", type=int, default=0)
    ap.add_argument("--min-case-count", type=int, default=40)
    ap.add_argument(
        "--research-lexicon",
        type=Path,
        default=None,
        help="Optional overlay lexicon; records Golden 40 metrics in output (does not gate exit code).",
    )
    args = ap.parse_args()

    active_path = args.active_report.resolve()
    if not active_path.is_file():
        print(f"error: missing active report: {active_path}", file=sys.stderr)
        return 2

    report = _load(active_path)
    saving = _metric(report, "global_token_saving_rate")
    jaccard = _metric(report, "avg_reconstruction_fidelity_jaccard")
    violations = _metric(report, "sensitive_violation_count")
    case_count = _metric(report, "case_count")

    checks: list[dict[str, Any]] = []

    def _add(name: str, ok: bool, observed: Any, floor: Any) -> None:
        checks.append({"check": name, "ok": ok, "observed": observed, "floor": floor})

    if saving is None:
        _add("global_token_saving_rate_present", False, None, args.min_global_token_saving_rate)
    else:
        _add(
            "global_token_saving_rate_floor",
            float(saving) >= args.min_global_token_saving_rate,
            saving,
            args.min_global_token_saving_rate,
        )

    if jaccard is None:
        _add("avg_jaccard_present", False, None, args.min_avg_jaccard)
    else:
        _add(
            "avg_jaccard_floor",
            float(jaccard) >= args.min_avg_jaccard,
            jaccard,
            args.min_avg_jaccard,
        )

    if violations is None:
        _add("sensitive_violations_present", False, None, args.max_sensitive_violations)
    else:
        _add(
            "sensitive_violation_count",
            int(violations) <= args.max_sensitive_violations,
            violations,
            args.max_sensitive_violations,
        )

    if case_count is None:
        _add("case_count_present", False, None, args.min_case_count)
    else:
        _add("case_count_min", int(case_count) >= args.min_case_count, case_count, args.min_case_count)

    all_ok = all(c.get("ok") for c in checks)
    research_block: dict[str, Any] | None = None
    if args.research_lexicon is not None:
        lex = args.research_lexicon.resolve()
        if not lex.is_file():
            print(f"warn: --research-lexicon missing: {lex}", file=sys.stderr)
        else:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: WPS433
                _load_signoff_relaxed,
                _metrics,
                _run_eval,
            )
            from scripts.run_ultra_compression_default import INPUT_V2  # noqa: WPS433

            src_doc = _load(INPUT_V2)
            domain_relaxed, allowlist, exclude = _load_signoff_relaxed()
            research_block = {
                "lexicon_path": str(lex).replace("\\", "/"),
                "metrics": _metrics(
                    _run_eval(
                        src_doc,
                        lexicon_path=lex,
                        domain_relaxed=domain_relaxed,
                        relaxed_case_allowlist=allowlist,
                        relaxed_case_exclude=exclude,
                    )
                ),
                "note": "observability only; regression_ok gates on ACTIVE report only",
            }

    out = {
        "schema": "compression_golden_bench_regression_v1",
        "generated_at_utc": _utc(),
        "active_report": str(active_path).replace("\\", "/"),
        "regression_ok": all_ok,
        "checks": checks,
        "research_lexicon_eval": research_block,
        "note": (
            "Floors gate ACTIVE only. Production bench SSOT 41658 ~49.1%/0.873; 3a overlay ~47.5%/0.890 research."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_json}")
    if not all_ok:
        for c in checks:
            if not c.get("ok"):
                print(f"FAIL {c['check']}: observed={c.get('observed')} floor={c.get('floor')}", file=sys.stderr)
        return 1
    print("compression_golden_bench_regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
