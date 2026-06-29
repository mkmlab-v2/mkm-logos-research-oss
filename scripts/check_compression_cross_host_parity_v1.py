#!/usr/bin/env python3
"""Compare main vs aux compression parity probe metrics (raw + repair_v2 + delta)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAIN_DEFAULT = ROOT / "reports/compression_cross_host_parity_main_baseline_v1_latest.json"
AUX_DEFAULT = ROOT / "reports/compression_cross_host_parity_aux_probe_v1_latest.json"
OUT = ROOT / "reports/compression_cross_host_parity_check_v1_latest.json"

TOL_SAVING = 1e-6
TOL_JACCARD = 1e-5


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num_close(a: Any, b: Any, tol: float) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    b_met = (baseline.get("metrics") or {}).get("raw") or {}
    c_met = (candidate.get("metrics") or {}).get("raw") or {}
    b_rep = (baseline.get("metrics") or {}).get("repair_v2") or {}
    c_rep = (candidate.get("metrics") or {}).get("repair_v2") or {}

    saving_match = _num_close(
        b_met.get("mean_token_saving_rate_proxy"),
        c_met.get("mean_token_saving_rate_proxy"),
        TOL_SAVING,
    )
    jaccard_match = _num_close(
        b_met.get("mean_jaccard_proxy"),
        c_met.get("mean_jaccard_proxy"),
        TOL_JACCARD,
    )
    rows_match = b_met.get("rows") == c_met.get("rows")
    repair_saving_match = _num_close(
        b_rep.get("mean_token_saving_rate_proxy"),
        c_rep.get("mean_token_saving_rate_proxy"),
        TOL_SAVING,
    )
    repair_jaccard_match = _num_close(
        b_rep.get("mean_jaccard_proxy"),
        c_rep.get("mean_jaccard_proxy"),
        TOL_JACCARD,
    )

    parity_ok = (
        baseline.get("status") == "ok"
        and candidate.get("status") == "ok"
        and saving_match
        and jaccard_match
        and rows_match
        and repair_saving_match
        and repair_jaccard_match
    )
    b_env = baseline.get("env_fingerprint") or {}
    c_env = candidate.get("env_fingerprint") or {}
    codebook_parity_hint = None
    if not jaccard_match and b_env.get("codebook_exists") and not c_env.get("codebook_exists"):
        codebook_parity_hint = "candidate_missing_codebook_lexicon_ssot"
    b_py = str(b_env.get("python_version") or "")
    c_py = str(c_env.get("python_version") or "")
    if not jaccard_match and b_py and c_py and b_py.split(".")[:2] != c_py.split(".")[:2]:
        codebook_parity_hint = codebook_parity_hint or "python_version_mismatch"

    return {
        "schema": "compression_cross_host_parity_check_v1",
        "generated_at_utc": _utc(),
        "parity_ok": parity_ok,
        "tolerance": {"saving_rate_abs": TOL_SAVING, "jaccard_abs": TOL_JACCARD},
        "baseline": {
            "path": baseline.get("_path"),
            "host_label": baseline.get("host_label"),
            "hostname": baseline.get("hostname"),
            "status": baseline.get("status"),
            "env_fingerprint": b_env,
            "raw": b_met,
            "repair_v2": b_rep,
        },
        "candidate": {
            "path": candidate.get("_path"),
            "host_label": candidate.get("host_label"),
            "hostname": candidate.get("hostname"),
            "status": candidate.get("status"),
            "env_fingerprint": c_env,
            "raw": c_met,
            "repair_v2": c_rep,
        },
        "checks": {
            "rows_match": rows_match,
            "raw_saving_match": saving_match,
            "raw_jaccard_match": jaccard_match,
            "repair_v2_saving_match": repair_saving_match,
            "repair_v2_jaccard_match": repair_jaccard_match,
        },
        "delta_candidate_minus_baseline": {
            "mean_token_saving_rate_proxy": (
                None
                if c_met.get("mean_token_saving_rate_proxy") is None
                or b_met.get("mean_token_saving_rate_proxy") is None
                else float(c_met["mean_token_saving_rate_proxy"])
                - float(b_met["mean_token_saving_rate_proxy"])
            ),
            "mean_jaccard_proxy": (
                None
                if c_met.get("mean_jaccard_proxy") is None or b_met.get("mean_jaccard_proxy") is None
                else float(c_met["mean_jaccard_proxy"]) - float(b_met["mean_jaccard_proxy"])
            ),
        },
        "disclaimer": "Same locked probe (tenant/input/max_cases). Not headline 20.4% wtt tenant unless probe SSOT changed.",
        "codebook_parity_hint": codebook_parity_hint,
        "status": "ok" if parity_ok else "fail",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, default=MAIN_DEFAULT)
    ap.add_argument("--candidate", type=Path, default=AUX_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if not args.baseline.exists():
        raise SystemExit(f"missing baseline: {args.baseline}")
    if not args.candidate.exists():
        raise SystemExit(f"missing candidate: {args.candidate}")

    baseline = _read(args.baseline)
    baseline["_path"] = str(args.baseline).replace("\\", "/")
    candidate = _read(args.candidate)
    candidate["_path"] = str(args.candidate).replace("\\", "/")

    doc = compare(baseline, candidate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["parity_ok"], "out": str(args.out.relative_to(ROOT))}))
    return 0 if doc["parity_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
