#!/usr/bin/env python3
"""B-track [HYPO]: cartesian co-occurrence routing for other:: atoms (no polar transform)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/other_cooc_cartesian_routing_poc_v1_latest.json"
BIGRAM_DIM = 32


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atom_prefix(atom_id: str) -> str:
    if atom_id.startswith("greek::"):
        return "greek"
    if atom_id.startswith("hebrew::"):
        return "hebrew"
    return "other"


def _bigram_vec(nf: str) -> list[float]:
    v = [0.0] * BIGRAM_DIM
    text = (nf or "").strip().lower()
    for i in range(max(0, len(text) - 1)):
        h = (ord(text[i]) * 31 + ord(text[i + 1])) % BIGRAM_DIM
        v[h] += 1.0
    s = sum(v) or 1.0
    return [x / s for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


def _mean_vec(vecs: list[list[float]]) -> list[float]:
    if not vecs:
        return [0.0] * BIGRAM_DIM
    out = [0.0] * BIGRAM_DIM
    for v in vecs:
        for i, x in enumerate(v):
            out[i] += x
    n = float(len(vecs))
    return [x / n for x in out]


def _sweep_threshold(scored: list[tuple[str, str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for t_int in range(-5, 16):
        t = t_int / 100.0
        tp = fp = fn = tn = 0
        for prefix, _aid, aff in scored:
            pred = aff >= t
            is_other = prefix == "other"
            if pred and is_other:
                tp += 1
            elif pred and not is_other:
                fp += 1
            elif not pred and is_other:
                fn += 1
            else:
                tn += 1
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        rows.append(
            {
                "threshold": round(t, 2),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "precision": round(prec, 6),
                "recall": round(rec, 6),
                "f1": round(f1, 6),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Cartesian cooc routing PoC (B-track)")
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-recall", type=float, default=0.85)
    args = ap.parse_args()

    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 2

    scored: list[tuple[str, str, float]] = []
    other_vecs: list[list[float]] = []
    rest_vecs: list[list[float]] = []
    rows_raw: list[tuple[str, str, str]] = []

    for row in _load_json(args.lexicon).get("entries") or []:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id:
            continue
        prefix = _atom_prefix(atom_id)
        nf = str(row.get("normalized_form") or "")
        rows_raw.append((prefix, atom_id, nf))
        vec = _bigram_vec(nf)
        if prefix == "other":
            other_vecs.append(vec)
        else:
            rest_vecs.append(vec)

    other_mean = _mean_vec(other_vecs)
    rest_mean = _mean_vec(rest_vecs)

    for prefix, atom_id, nf in rows_raw:
        vec = _bigram_vec(nf)
        aff = _cosine(vec, other_mean) - _cosine(vec, rest_mean)
        scored.append((prefix, atom_id, aff))

    sweep = _sweep_threshold(scored)
    best_f1 = max(sweep, key=lambda r: r["f1"])
    recall_ok = [r for r in sweep if r["recall"] >= args.min_recall]
    best_constrained = max(recall_ok, key=lambda r: (r["precision"], r["f1"])) if recall_ok else best_f1

    other_aff = [a for p, _, a in scored if p == "other"]
    rest_aff = [a for p, _, a in scored if p != "other"]
    other_mean_aff = sum(other_aff) / max(len(other_aff), 1)
    rest_mean_aff = sum(rest_aff) / max(len(rest_aff), 1)

    proceed = (
        best_constrained["f1"] >= 0.5
        and best_constrained["recall"] >= args.min_recall
        and (other_mean_aff - rest_mean_aff) > 0.04
    )

    top_other = sorted(
        [(aid, a) for p, aid, a in scored if p == "other"],
        key=lambda x: x[1],
        reverse=True,
    )[:8]
    top_false_pos = sorted(
        [(aid, a) for p, aid, a in scored if p != "other" and a >= best_constrained["threshold"]],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    doc: dict[str, Any] = {
        "schema": "other_cooc_cartesian_routing_poc_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "feature_set": "bigram_cooc_affinity (cartesian only; no polar)",
        "atom_counts": {
            "greek": sum(1 for p, _, _ in rows_raw if p == "greek"),
            "hebrew": sum(1 for p, _, _ in rows_raw if p == "hebrew"),
            "other": sum(1 for p, _, _ in rows_raw if p == "other"),
        },
        "affinity_mean": {
            "other": round(other_mean_aff, 6),
            "rest": round(rest_mean_aff, 6),
            "delta": round(other_mean_aff - rest_mean_aff, 6),
        },
        "recommended_threshold": best_constrained["threshold"],
        "recommended_metrics": best_constrained,
        "best_f1_threshold": best_f1,
        "threshold_sweep": sweep,
        "proceed_to_bench_hook": proceed,
        "routing_policy_draft": {
            "isolate_when": f"cooc_affinity >= {best_constrained['threshold']}",
            "lane": "other_isolated_bucket_v1",
            "non_gating": True,
        },
        "samples": {
            "top_other_by_affinity": [{"atom_id": a, "affinity": round(v, 6)} for a, v in top_other],
            "top_false_positive_routes": [{"atom_id": a, "affinity": round(v, 6)} for a, v in top_false_pos],
        },
        "promotion": "HOLD — no Track A / ACTIVE / MS KPI update",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {args.out} proceed={proceed} "
        f"thr={best_constrained['threshold']} f1={best_constrained['f1']} recall={best_constrained['recall']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
