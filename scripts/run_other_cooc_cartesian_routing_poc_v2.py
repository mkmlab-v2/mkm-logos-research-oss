#!/usr/bin/env python3
"""B-track [HYPO] v2: prefix-gated cooc — route/isolate only within other:: atoms."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"
BIGRAM_DIM = 32


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
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


def _centroid(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Prefix-gated cooc routing PoC v2")
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--isolate-quantile", type=float, default=0.75, help="Top quartile of other:: -> isolate tier")
    args = ap.parse_args()

    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 2

    other_vecs: list[list[float]] = []
    rest_vecs: list[list[float]] = []
    other_rows: list[tuple[str, str, float]] = []

    for row in _load_json(args.lexicon).get("entries") or []:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id:
            continue
        nf = str(row.get("normalized_form") or "")
        vec = _bigram_vec(nf)
        is_other = atom_id.startswith("other::")
        if is_other:
            other_vecs.append(vec)
        else:
            rest_vecs.append(vec)

    other_mean = _mean_vec(other_vecs)
    rest_mean = _mean_vec(rest_vecs)

    non_other_high_affinity: list[tuple[str, float]] = []
    for row in _load_json(args.lexicon).get("entries") or []:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id or atom_id.startswith("other::"):
            continue
        nf = str(row.get("normalized_form") or "")
        aff = _cosine(_bigram_vec(nf), other_mean) - _cosine(_bigram_vec(nf), rest_mean)
        if aff >= 0.04:
            non_other_high_affinity.append((atom_id, aff))

    for row in _load_json(args.lexicon).get("entries") or []:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id.startswith("other::"):
            continue
        nf = str(row.get("normalized_form") or "")
        vec = _bigram_vec(nf)
        aff = _cosine(vec, other_mean) - _cosine(vec, rest_mean)
        other_rows.append((atom_id, nf, aff))

    affinities = sorted(a for _, _, a in other_rows)
    if not affinities:
        print("no other:: atoms", file=sys.stderr)
        return 2

    q_idx = min(len(affinities) - 1, int(len(affinities) * args.isolate_quantile))
    threshold = affinities[q_idx]
    high = [(aid, nf, a) for aid, nf, a in other_rows if a >= threshold]
    low = [(aid, nf, a) for aid, nf, a in other_rows if a < threshold]

    high_aff = [a for _, _, a in high]
    low_aff = [a for _, _, a in low]
    between = abs(_centroid(high_aff) - _centroid(low_aff))
    spread_high = (
        math.sqrt(sum((a - _centroid(high_aff)) ** 2 for a in high_aff) / max(len(high_aff), 1)) if high_aff else 0.0
    )
    spread_low = (
        math.sqrt(sum((a - _centroid(low_aff)) ** 2 for a in low_aff) / max(len(low_aff), 1)) if low_aff else 0.0
    )
    separation_ratio = between / (spread_high + spread_low + 1e-9)

    proceed = (
        len(high) >= 100
        and len(low) >= 100
        and between >= 0.02
        and separation_ratio >= 0.35
        and _centroid(high_aff) - _centroid(low_aff) >= 0.02
    )

    doc: dict[str, Any] = {
        "schema": "other_cooc_cartesian_routing_poc_v2",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "feature_set": "prefix-gated other:: only; bigram cooc_affinity tiers",
        "prefix_gate": "atom_id.startswith('other::')",
        "other_atom_count": len(other_rows),
        "isolate_quantile": args.isolate_quantile,
        "isolate_threshold_affinity": round(threshold, 6),
        "tiers": {
            "isolate_high": {"count": len(high), "mean_affinity": round(_centroid(high_aff), 6)},
            "merge_candidate_low": {"count": len(low), "mean_affinity": round(_centroid(low_aff), 6)},
        },
        "within_other_separation": {
            "between_tier_mean_delta": round(between, 6),
            "high_tier_spread": round(spread_high, 6),
            "low_tier_spread": round(spread_low, 6),
            "separation_ratio": round(separation_ratio, 6),
        },
        "non_other_high_affinity_reference": {
            "count": len(non_other_high_affinity),
            "note": "greek/hebrew with cooc>=0.04 — NOT routed (prefix gate)",
            "top5": [{"atom_id": a, "affinity": round(v, 6)} for a, v in sorted(non_other_high_affinity, key=lambda x: -x[1])[:5]],
        },
        "proceed_to_bench_hook": proceed,
        "routing_policy_draft": {
            "gate": "other:: prefix required",
            "isolate_when": f"cooc_affinity >= p{int(args.isolate_quantile * 100)} ({threshold:.4f})",
            "lane": "other_isolated_high_affinity_v1",
            "non_gating": True,
        },
        "samples": {
            "top_isolate": [{"atom_id": a, "affinity": round(v, 6)} for a, _, v in sorted(high, key=lambda x: -x[2])[:8]],
            "top_merge_candidate": [{"atom_id": a, "affinity": round(v, 6)} for a, _, v in sorted(low, key=lambda x: x[2])[:5]],
        },
        "promotion": "HOLD — no Track A / ACTIVE / MS KPI update",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {args.out} proceed={proceed} isolate={len(high)} merge_cand={len(low)} "
        f"sep_ratio={separation_ratio:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
