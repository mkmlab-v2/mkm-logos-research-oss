#!/usr/bin/env python3
"""Classify raw vs reconstructed mismatches for Fact-Lock (bench hygiene).

For baseline MULTILENS reports, reconstructed_text_effective comes from the input
JSON's reconstructed_text — mismatches are largely *benchmark authoring* (paraphrase),
not runtime LLM output. For experimental reports, rec is from the pipeline decoder.

Outputs docs/final/artifacts/EXACT_MATCH_FAILURE_TAXONOMY_V1.json by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_BASELINE_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "EXACT_MATCH_FAILURE_TAXONOMY_V1.json"

_WS_RE = re.compile(r"\s+")


def _norm_ws(s: str) -> str:
    return _WS_RE.sub(" ", s.strip())


def classify(raw: str, rec: str) -> tuple[list[str], dict[str, Any]]:
    flags: list[str] = []
    detail: dict[str, Any] = {}

    if raw == rec:
        flags.append("exact")
        return flags, detail

    r_nfc = unicodedata.normalize("NFC", raw)
    c_nfc = unicodedata.normalize("NFC", rec)
    if r_nfc == c_nfc:
        flags.append("nfc_fixable")
        return flags, detail

    if raw.strip() == rec.strip():
        flags.append("strip_only_mismatch")
        return flags, detail

    if r_nfc.strip() == c_nfc.strip():
        flags.append("nfc_and_strip_fixable")
        return flags, detail

    if _norm_ws(raw) == _norm_ws(rec):
        flags.append("whitespace_normalize_fixable")
        return flags, detail

    if _norm_ws(r_nfc) == _norm_ws(c_nfc):
        flags.append("nfc_whitespace_normalize_fixable")
        return flags, detail

    ratio = SequenceMatcher(a=raw, b=rec).ratio()
    wratio = SequenceMatcher(a=raw.split(), b=rec.split()).ratio()
    detail["sequence_matcher_char_ratio"] = round(ratio, 6)
    detail["sequence_matcher_word_ratio"] = round(wratio, 6)

    if ratio >= 0.98:
        flags.append("near_identical_chars")
    elif wratio >= 0.85:
        flags.append("likely_paraphrase_or_reorder")
    else:
        flags.append("substantive_mismatch")

    return flags, detail


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact-match failure taxonomy from MULTILENS report + input.")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-diff-lines", type=int, default=12)
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    mode = (report.get("run_config") or {}).get("mode", "")

    failures: list[dict[str, Any]] = []
    exact_n = 0
    flag_counter: Counter[str] = Counter()
    shard_flag: dict[str, Counter[str]] = defaultdict(Counter)

    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")

        if raw == rec:
            exact_n += 1
            continue

        flags, detail = classify(raw, rec)
        for f in flags:
            flag_counter[f] += 1
            shard_flag[shard][f] += 1

        diff_lines = list(
            unified_diff(
                raw.splitlines(keepends=True),
                rec.splitlines(keepends=True),
                fromfile="raw",
                tofile="reconstructed",
                n=2,
            )
        )
        preview = "".join(diff_lines[: args.max_diff_lines])
        if len(diff_lines) > args.max_diff_lines:
            preview += "\n... (truncated)\n"

        failures.append(
            {
                "id": cid,
                "shard_id": shard,
                "primary_flags": flags,
                "detail": detail,
                "raw_len": len(raw),
                "rec_len": len(rec),
                "diff_preview": preview,
            }
        )

    payload = {
        "schema": "exact_match_failure_taxonomy_v1",
        "description": (
            "Per-case mismatch taxonomy: normalization vs substantive. "
            "Baseline reports: mismatches usually reflect benchmark authoring (raw vs paraphrase in input). "
            "Experimental reports: mismatches reflect decoder/heuristic reconstruction."
        ),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_mode": mode,
        "interpretation_note": (
            "When run_mode is baseline, reconstructed strings come from the input JSON, not an LLM. "
            "When experimental, they come from the pipeline decoder/heuristic."
        ),
        "summary": {
            "case_count": len(cases),
            "exact_match_count": exact_n,
            "failure_count": len(failures),
        },
        "aggregate_primary_flags_on_failures": dict(flag_counter),
        "aggregate_by_shard": {k: dict(v) for k, v in sorted(shard_flag.items())},
        "failures": failures,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path} ({exact_n} exact, {len(failures)} failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
