#!/usr/bin/env python3
"""Research-only fractal sign-reading engine over news_observation JSONL.

Maps current news flow into an aggregate 4D SLKM vector and computes cosine
resonance against archetype vectors from a configurable matrix.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"
DEFAULT_MATRIX = ROOT / "docs" / "final" / "artifacts" / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_fractal_sign_reading_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _score_dim(text: str, pos: list[str], neg: list[str]) -> float:
    pos_hits = sum(1 for t in pos if t in text)
    neg_hits = sum(1 for t in neg if t in text)
    raw = 0.5 + 0.1 * (pos_hits - neg_hits)
    return max(0.0, min(1.0, raw))


def _project_row_slkm(text: str, lex: dict[str, list[str]]) -> dict[str, float]:
    t = text.lower()
    return {
        "S": _score_dim(t, lex.get("S_positive", []), lex.get("S_negative", [])),
        "L": _score_dim(t, lex.get("L_positive", []), lex.get("L_negative", [])),
        "K": _score_dim(t, lex.get("K_positive", []), lex.get("K_negative", [])),
        "M": _score_dim(t, lex.get("M_positive", []), lex.get("M_negative", [])),
    }


def _mean_vec(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5}
    n = float(len(rows))
    return {
        "S": round(sum(r["S"] for r in rows) / n, 6),
        "L": round(sum(r["L"] for r in rows) / n, 6),
        "K": round(sum(r["K"] for r in rows) / n, 6),
        "M": round(sum(r["M"] for r in rows) / n, 6),
    }


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = ("S", "L", "K", "M")
    dot = sum(float(a[k]) * float(b[k]) for k in keys)
    na = math.sqrt(sum(float(a[k]) ** 2 for k in keys))
    nb = math.sqrt(sum(float(b[k]) ** 2 for k in keys))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return round(dot / (na * nb), 6)


def _decision(top_resonance: float, cuts: dict[str, Any], mapping: dict[str, str]) -> str:
    critical_cut = float(cuts.get("critical_resonance_cut", 0.9))
    watch_cut = float(cuts.get("watch_resonance_cut", 0.8))
    if top_resonance >= critical_cut:
        return str(mapping.get("critical", "HOLD"))
    if top_resonance >= watch_cut:
        return str(mapping.get("watch", "WATCH"))
    return str(mapping.get("normal", "OBSERVE"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run fractal sign-reading resonance over news_observation.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    matrix = _load_json(args.matrix_json)
    rows = _load_jsonl(args.news_jsonl)
    lex = matrix.get("projection_lexicon") or {}

    projected = []
    for r in rows:
        txt = str(r.get("canonical_text", ""))
        projected.append(_project_row_slkm(txt, lex))

    current = _mean_vec(projected)
    resonances: list[dict[str, Any]] = []
    for a in matrix.get("archetypes", []):
        vec = a.get("vector_slkm") or {}
        arche = {"S": float(vec.get("S", 0.5)), "L": float(vec.get("L", 0.5)), "K": float(vec.get("K", 0.5)), "M": float(vec.get("M", 0.5))}
        resonances.append(
            {
                "archetype_id": str(a.get("id", "")),
                "label_ko": str(a.get("label_ko", "")),
                "resonance_cosine": _cosine(current, arche),
            }
        )
    resonances.sort(key=lambda x: float(x["resonance_cosine"]), reverse=True)
    top = resonances[0] if resonances else {"archetype_id": "unknown", "label_ko": "unknown", "resonance_cosine": 0.0}

    decision = _decision(
        top_resonance=float(top.get("resonance_cosine", 0.0)),
        cuts=matrix.get("decision_thresholds") or {},
        mapping=matrix.get("decision_mapping") or {},
    )

    out = {
        "schema": "logos_fractal_sign_reading_v1",
        "generated_at_utc": _now(),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "news_jsonl": str(args.news_jsonl).replace("\\", "/"),
            "matrix_json": str(args.matrix_json).replace("\\", "/"),
            "news_row_count": len(rows),
        },
        "current_vector_slkm": current,
        "archetype_resonance": resonances,
        "top_match": top,
        "decision": {
            "signal": decision,
            "critical_cut": float((matrix.get("decision_thresholds") or {}).get("critical_resonance_cut", 0.9)),
            "watch_cut": float((matrix.get("decision_thresholds") or {}).get("watch_resonance_cut", 0.8)),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "news_row_count": len(rows),
                "top_match": out["top_match"],
                "signal": decision,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

