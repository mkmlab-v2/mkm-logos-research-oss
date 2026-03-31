#!/usr/bin/env python3
"""Label symbol candidates into A/B/C grades."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"

IN_STABLE = PILOT / "symbol_candidates_curated_stable_latest.jsonl"
IN_EXPL = PILOT / "symbol_candidates_curated_exploratory_latest.jsonl"
OUT_JSONL = PILOT / "symbol_candidates_abc_labeled_latest.jsonl"
OUT_SUMMARY = PILOT / "symbol_candidates_abc_summary_latest.json"
OUT_C_QUEUE = PILOT / "symbol_c_validation_queue_latest.jsonl"

# A: broadly recognized theological/sectarian anchors (scholarly alignment proxy)
A_ANCHORS = {
    "אלהים", "יהוה", "ברית", "צדק", "משפט", "חכמה", "שלום", "אור", "חסד", "רוח",
    "ירושלים", "ישראל", "בני ישראל", "מלך", "מלחמה", "שמים",
}

# B: project-theory emphasis anchors (our-theory alignment proxy)
B_ANCHORS = {
    "בני אלהים", "עליון", "עליון עמים", "עמים", "גבול", "נחלה", "ישראל עליון",
    "עמים נחלה", "נחלה גבול", "עמים גבול", "יחד", "עדה",
}


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _bucket(row: dict[str, Any]) -> str:
    mix = row.get("source_mix", {})
    if not isinstance(mix, dict):
        mix = {}
    dss = int(mix.get("dss", 0) or 0)
    apo = int(mix.get("apocrypha", 0) or 0)
    if dss > 0 and apo > 0:
        return "mixed"
    if dss > 0 and apo == 0:
        return "dss_only"
    if apo > 0 and dss == 0:
        return "apocrypha_only"
    return "unknown"


def _grade(symbol: str, stable: dict[str, Any] | None, expl: dict[str, Any] | None) -> tuple[str, str]:
    s = symbol.strip()
    s_norm = s.lower()
    in_stable = stable is not None
    in_expl = expl is not None

    # A: scholarly anchor + cross-profile reproducibility
    if s in A_ANCHORS and in_stable and in_expl:
        return "A", "scholarly_anchor_and_cross_profile_reproducible"

    # B: theory anchor OR strong DSS-backed symbol in exploratory profile
    target = expl or stable
    if s in B_ANCHORS:
        return "B", "our_theory_anchor_term"
    if target is not None:
        mix = target.get("source_mix", {})
        dss = int(mix.get("dss", 0) or 0) if isinstance(mix, dict) else 0
        apo = int(mix.get("apocrypha", 0) or 0) if isinstance(mix, dict) else 0
        if dss > 0 and (dss >= apo):
            return "B", "dss_backed_signal"

    # C: statistically strong but unconfirmed semantic grade
    if in_stable or in_expl:
        return "C", "statistical_candidate_pending_semantic_validation"
    return "C", "insufficient_signal"


def _grade_single(symbol: str, row: dict[str, Any]) -> tuple[str, str]:
    s = symbol.strip()
    if s in A_ANCHORS:
        return "A", "scholarly_anchor_term"
    if s in B_ANCHORS:
        return "B", "our_theory_anchor_term"
    mix = row.get("source_mix", {})
    dss = int(mix.get("dss", 0) or 0) if isinstance(mix, dict) else 0
    apo = int(mix.get("apocrypha", 0) or 0) if isinstance(mix, dict) else 0
    if dss > 0 and dss >= apo:
        return "B", "dss_backed_signal"
    return "C", "statistical_candidate_pending_semantic_validation"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Label B-Track symbol candidates into A/B/C")
    ap.add_argument("--stable-jsonl", default=str(IN_STABLE))
    ap.add_argument("--exploratory-jsonl", default=str(IN_EXPL))
    ap.add_argument("--single-jsonl", default="", help="Single profile curated input JSONL")
    ap.add_argument("--profile-tag", default="", help="Profile tag used in single mode")
    ap.add_argument("--out-jsonl", default=str(OUT_JSONL))
    ap.add_argument("--out-summary", default=str(OUT_SUMMARY))
    ap.add_argument("--out-c-queue-jsonl", default=str(OUT_C_QUEUE))
    ap.add_argument("--c-top-k", type=int, default=50)
    args = ap.parse_args()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_jsonl = _abs(args.out_jsonl)
    out_summary = _abs(args.out_summary)
    out_c_queue = _abs(args.out_c_queue_jsonl)

    if args.single_jsonl:
        in_path = _abs(args.single_jsonl)
        if not in_path.is_file():
            print(f"ERROR: missing input: {in_path}")
            return 2
        profile_tag = str(args.profile_tag).strip() or "profile"
        labeled: list[dict[str, Any]] = []
        counts = {"A": 0, "B": 0, "C": 0}
        for row in _iter_jsonl(in_path):
            symbol = str(row.get("symbol", "")).strip()
            if not symbol:
                continue
            grade, reason = _grade_single(symbol, row)
            counts[grade] += 1
            score = float(row.get("score_tfidf_like", 0.0) or 0.0)
            labeled.append(
                {
                    "symbol": symbol,
                    "grade": grade,
                    "grade_reason": reason,
                    "profile_tag": profile_tag,
                    "score_tfidf_like": round(score, 6),
                    "source_bucket": _bucket(row),
                    "source_mix": row.get("source_mix", {}),
                    "generated_at_utc": ts,
                }
            )
        labeled.sort(
            key=lambda r: (
                {"A": 0, "B": 1, "C": 2}.get(str(r.get("grade")), 9),
                -float(r.get("score_tfidf_like", 0.0) or 0.0),
            )
        )
        _write_jsonl(out_jsonl, labeled)

        c_rows = [r for r in labeled if str(r.get("grade")) == "C"]
        c_rows.sort(key=lambda r: float(r.get("score_tfidf_like", 0.0) or 0.0), reverse=True)
        c_rows = c_rows[: args.c_top_k]
        _write_jsonl(out_c_queue, c_rows)

        summary = {
            "schema": "btrack_symbol_abc_label_v1",
            "generated_at_utc": ts,
            "mode": "single",
            "profile_tag": profile_tag,
            "inputs": {"single_jsonl": str(in_path)},
            "counts": counts,
            "total_symbols": len(labeled),
            "output_jsonl": str(out_jsonl),
            "c_queue": {
                "output_jsonl": str(out_c_queue),
                "count": len(c_rows),
                "top_k": args.c_top_k,
            },
            "top_preview": labeled[:20],
            "note": "A/B/C are heuristic operational labels, not doctrinal certainty.",
        }
        out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("OK: symbol A/B/C labeling generated (single mode)")
        print(f"out={out_jsonl}")
        print(f"c_queue={out_c_queue}")
        print(f"summary={out_summary}")
        print(f"counts={counts}")
        return 0

    stable_path = _abs(args.stable_jsonl)
    expl_path = _abs(args.exploratory_jsonl)
    for p in (stable_path, expl_path):
        if not p.is_file():
            print(f"ERROR: missing input: {p}")
            return 2

    stable_map: dict[str, dict[str, Any]] = {}
    expl_map: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(stable_path):
        stable_map[str(row.get("symbol", "")).strip()] = row
    for row in _iter_jsonl(expl_path):
        expl_map[str(row.get("symbol", "")).strip()] = row

    symbols = sorted(set(stable_map.keys()) | set(expl_map.keys()))

    labeled: list[dict[str, Any]] = []
    counts = {"A": 0, "B": 0, "C": 0}
    for symbol in symbols:
        srow = stable_map.get(symbol)
        erow = expl_map.get(symbol)
        grade, reason = _grade(symbol, srow, erow)
        counts[grade] += 1

        target = erow if erow is not None else srow
        bucket = _bucket(target) if target is not None else "unknown"
        score_stable = float(srow.get("score_tfidf_like", 0.0) or 0.0) if srow else 0.0
        score_expl = float(erow.get("score_tfidf_like", 0.0) or 0.0) if erow else 0.0
        row = {
            "symbol": symbol,
            "grade": grade,
            "grade_reason": reason,
            "present_in_stable": srow is not None,
            "present_in_exploratory": erow is not None,
            "score_tfidf_like_stable": round(score_stable, 6),
            "score_tfidf_like_exploratory": round(score_expl, 6),
            "source_bucket": bucket,
            "source_mix": (target or {}).get("source_mix", {}),
            "generated_at_utc": ts,
        }
        labeled.append(row)

    labeled.sort(
        key=lambda r: (
            {"A": 0, "B": 1, "C": 2}.get(str(r.get("grade")), 9),
            -float(r.get("score_tfidf_like_exploratory", 0.0) or 0.0),
            -float(r.get("score_tfidf_like_stable", 0.0) or 0.0),
        )
    )
    _write_jsonl(out_jsonl, labeled)

    c_rows = [r for r in labeled if str(r.get("grade")) == "C"]
    c_rows.sort(key=lambda r: float(r.get("score_tfidf_like_exploratory", 0.0) or 0.0), reverse=True)
    c_rows = c_rows[: args.c_top_k]
    _write_jsonl(out_c_queue, c_rows)

    summary = {
        "schema": "btrack_symbol_abc_label_v1",
        "generated_at_utc": ts,
        "mode": "dual",
        "inputs": {
            "stable_jsonl": str(stable_path),
            "exploratory_jsonl": str(expl_path),
        },
        "counts": counts,
        "total_symbols": len(labeled),
        "output_jsonl": str(out_jsonl),
        "c_queue": {
            "output_jsonl": str(out_c_queue),
            "count": len(c_rows),
            "top_k": args.c_top_k,
        },
        "top_preview": labeled[:20],
        "note": "A/B/C are heuristic operational labels, not doctrinal certainty.",
    }
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: symbol A/B/C labeling generated")
    print(f"out={out_jsonl}")
    print(f"c_queue={out_c_queue}")
    print(f"summary={out_summary}")
    print(f"counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
