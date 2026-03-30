#!/usr/bin/env python3
"""Run allowlist ON/OFF benchmark for symbol-gematria alignment pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports" / "constitution" / "btrack_pilot"

EXTRACT = ROOT / "scripts" / "extract_btrack_symbol_candidates.py"
CURATE = ROOT / "scripts" / "curate_btrack_symbol_candidates.py"
BUILD_VEC = ROOT / "scripts" / "build_symbol_vectors_from_verse_distilled.py"
ALIGN = ROOT / "scripts" / "report_symbol_gematria_alignment.py"

DSS = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed.jsonl"
APO = ROOT / "data" / "logos" / "manuscripts" / "apocrypha_std.jsonl"
ALLOWLIST = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
ALLOWLIST_OFF = ROOT / "_tmp_allowlist_off_missing.jsonl"


def _run(args: list[str]) -> None:
    res = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"Command failed ({res.returncode}): {' '.join(args)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _variant(tag: str, allowlist_path: Path) -> dict:
    sym = REPORTS / f"symbol_candidates_{tag}.jsonl"
    sym_summary = REPORTS / f"symbol_candidates_summary_{tag}.json"
    curated = REPORTS / f"symbol_candidates_curated_{tag}.jsonl"
    curated_summary = REPORTS / f"symbol_candidates_curated_summary_{tag}.json"
    vec = REPORTS / f"symbol_candidates_with_vectors_{tag}.jsonl"
    vec_summary = REPORTS / f"symbol_vectors_summary_{tag}.json"
    align = REPORTS / f"symbol_gematria_alignment_test_{tag}.json"
    align_nz = REPORTS / f"symbol_gematria_alignment_test_nonzero_{tag}.json"

    _run(
        [
            sys.executable,
            str(EXTRACT),
            "--dss",
            str(DSS),
            "--apo",
            str(APO),
            "--token-allowlist-jsonl",
            str(allowlist_path),
            "--out",
            str(sym),
            "--summary",
            str(sym_summary),
        ]
    )
    _run(
        [
            sys.executable,
            str(CURATE),
            "--in-jsonl",
            str(sym),
            "--out-jsonl",
            str(curated),
            "--out-summary",
            str(curated_summary),
        ]
    )
    _run(
        [
            sys.executable,
            str(BUILD_VEC),
            "--symbols",
            str(sym),
            "--out-jsonl",
            str(vec),
            "--out-summary",
            str(vec_summary),
        ]
    )
    _run([sys.executable, str(ALIGN), "--input", str(vec), "--out", str(align)])
    _run([sys.executable, str(ALIGN), "--input", str(vec), "--sample-mode", "gematria_nonzero", "--out", str(align_nz)])

    s = _read_json(sym_summary)
    vs = _read_json(vec_summary)
    a = _read_json(align)
    an = _read_json(align_nz)
    return {
        "tag": tag,
        "artifacts": {
            "symbols_summary": str(sym_summary),
            "vector_summary": str(vec_summary),
            "alignment": str(align),
            "alignment_nonzero": str(align_nz),
        },
        "metrics": {
            "symbols_after_filter": int(s.get("stats", {}).get("unique_symbols_after_filter", 0)),
            "top_k": int(s.get("stats", {}).get("top_k", 0)),
            "curated_count": int(_read_json(curated_summary).get("curated_count", 0)),
            "vector_coverage_rate": float(vs.get("stats", {}).get("vector_coverage_rate", 0.0)),
            "resonance_rate_random": float(a.get("summary", {}).get("resonance_rate", 0.0)),
            "avg_cosine_random": float(a.get("summary", {}).get("avg_cosine_symbol_vs_gematria_4d", 0.0)),
            "resonance_rate_nonzero": float(an.get("summary", {}).get("resonance_rate", 0.0)),
            "avg_cosine_nonzero": float(an.get("summary", {}).get("avg_cosine_symbol_vs_gematria_4d", 0.0)),
        },
    }


def main() -> int:
    on = _variant("allowlist_on", ALLOWLIST)
    off = _variant("allowlist_off", ALLOWLIST_OFF)
    off_m = off["metrics"]
    on_m = on["metrics"]

    def _delta(key: str) -> float:
        return float(on_m[key]) - float(off_m[key])

    summary = {
        "schema": "symbol_allowlist_ab_bench_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "variants": {"allowlist_on": on, "allowlist_off": off},
        "comparison": {
            "delta_symbols_after_filter": _delta("symbols_after_filter"),
            "delta_curated_count": _delta("curated_count"),
            "delta_vector_coverage_rate": _delta("vector_coverage_rate"),
            "delta_resonance_rate_random": _delta("resonance_rate_random"),
            "delta_avg_cosine_random": _delta("avg_cosine_random"),
            "delta_resonance_rate_nonzero": _delta("resonance_rate_nonzero"),
            "delta_avg_cosine_nonzero": _delta("avg_cosine_nonzero"),
        },
        "note": "Positive deltas mean allowlist_on performed higher than allowlist_off.",
    }
    out = REPORTS / "symbol_allowlist_ab_bench_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
