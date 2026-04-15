# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.3, M:0.2}
# Balance: 91
# Purpose: Extract Track A low-fidelity missing-token rule candidates.
# Keywords: track_a, failure, must_keep, rules, ssot
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_v1.json"
DEFAULT_EVALSET = ROOT / "docs" / "final" / "artifacts" / "track_a_low_fidelity_evalset_v1.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
STOPWORDS = {
    "the",
    "and",
    "or",
    "to",
    "in",
    "of",
    "a",
    "is",
    "for",
    "on",
    "this",
    "that",
    "with",
    "as",
    "be",
    "by",
    "it",
    "are",
}
RISK_TOKENS = {
    "not",
    "no",
    "never",
    "cannot",
    "must",
    "policy",
    "track",
    "state",
    "phase",
    "risk",
    "gate",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE)
    ap.add_argument("--evalset", type=Path, default=DEFAULT_EVALSET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-jaccard", type=float, default=0.6)
    ap.add_argument("--target-domains", type=str, default="ssot,timing")
    ap.add_argument("--top-n", type=int, default=30)
    args = ap.parse_args()

    active_path = args.active_report if args.active_report.is_absolute() else ROOT / args.active_report
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = json.loads(active_path.read_text(encoding="utf-8"))
    evalset_path = args.evalset if args.evalset.is_absolute() else ROOT / args.evalset
    evalset_doc = json.loads(evalset_path.read_text(encoding="utf-8")) if evalset_path.exists() else {"cases": []}
    evalset_map = {str(row.get("id") or ""): row for row in evalset_doc.get("cases", [])}
    cases: list[dict[str, Any]] = (report.get("compression_metrics", {}) or {}).get("cases", [])
    target_domains = {d.strip() for d in args.target_domains.split(",") if d.strip()}

    missing_tokens = Counter()
    risk_tokens = Counter()
    selected_cases: list[dict[str, Any]] = []

    for row in cases:
        domain = str(((row.get("route") or {}).get("domain")) or "unknown")
        jaccard = _safe_float(row.get("reconstruction_fidelity_jaccard"))
        if domain not in target_domains or jaccard > args.max_jaccard:
            continue

        case_id = str(row.get("id") or "")
        eval_row = evalset_map.get(case_id, {})
        raw_text = str(eval_row.get("raw_text") or row.get("raw_text_effective") or row.get("raw_text") or "")
        # Active report V1 stores compressed/reconstructed fields consistently.
        # Use compressed text as fallback source when raw text is not present.
        if not raw_text:
            raw_text = str(row.get("compressed_text_effective") or row.get("compressed_text") or "")
        recon_text = str(eval_row.get("reconstructed_text_effective") or row.get("reconstructed_text_effective") or row.get("reconstructed_text") or "")

        raw_tokens = _tokenize(raw_text)
        recon_set = set(_tokenize(recon_text))
        missing = [t for t in raw_tokens if t not in recon_set and t not in STOPWORDS and len(t) >= 2]

        compressed_tokens = _tokenize(raw_text)
        risk_tokens.update(
            t for t in compressed_tokens if (t in RISK_TOKENS or any(ch.isdigit() for ch in t))
        )
        missing_tokens.update(missing)
        selected_cases.append(
            {
                "id": case_id,
                "domain": domain,
                "reconstruction_fidelity_jaccard": jaccard,
                "token_saving_rate": _safe_float(row.get("token_saving_rate")),
                "missing_tokens_sample": missing[:12],
            }
        )

    top_missing = [
        {"token": token, "missing_count": count}
        for token, count in missing_tokens.most_common(max(1, args.top_n))
    ]
    if top_missing:
        top_candidates = top_missing
        candidate_mode = "missing_token_frequency"
    else:
        top_candidates = [
            {"token": token, "risk_count": count}
            for token, count in risk_tokens.most_common(max(1, args.top_n))
        ]
        candidate_mode = "risk_token_frequency_fallback"

    out_doc = {
        "schema": "track_a_failure_pattern_rules_v1",
        "generated_at_utc": _utc_now(),
        "input": str(active_path),
        "selection": {
            "target_domains": sorted(target_domains),
            "max_jaccard": args.max_jaccard,
            "selected_case_count": len(selected_cases),
            "candidate_mode": candidate_mode,
        },
        "must_keep_candidates": top_candidates,
        "selected_cases": selected_cases[:50],
        "next_action": "Use must_keep_candidates as Day2 rule seed, then run Track A A/B regression.",
    }

    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "selected_case_count": len(selected_cases),
                "top_candidate": (top_candidates[0] if top_candidates else None),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
