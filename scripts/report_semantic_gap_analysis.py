#!/usr/bin/env python3
"""Generate semantic gap analysis pilot report for Deut 32:8."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_SYMBOLS = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_latest.jsonl"
IN_ANCHOR = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_anchor_matrix_latest.json"
OUT_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "semantic_gap_analysis_v1.json"
IN_DSS_LEXICON = ROOT / "reports" / "constitution" / "btrack_pilot" / "dss_variant_lexicon_deut32_8_latest.json"

WORD_RE = re.compile(r"[A-Za-z]+|[\u0590-\u05FF]+")
TOKEN_ALIASES: dict[str, tuple[str, ...]] = {
    "sons": ("sons", "בני"),
    "god": ("god", "אלהים", "אל"),
    "israel": ("israel", "ישראל"),
    "divine": ("divine", "עליון"),
    "nations": ("nations", "עמים", "גוים"),
    "nation": ("nation", "גוי"),
    "inheritance": ("inheritance", "נחלה"),
    "boundary": ("boundary", "גבול"),
    "tribes": ("tribes", "שבט", "שבטים"),
    "heaven": ("heaven", "שמים"),
}


@dataclass(frozen=True)
class ReadingProfile:
    reading_id: str
    label: str
    terms: tuple[str, ...]


READINGS = (
    ReadingProfile(
        reading_id="sons_of_god",
        label="bene elohim / sons of God",
        terms=("sons", "god", "divine", "heaven", "nations", "inheritance"),
    ),
    ReadingProfile(
        reading_id="sons_of_israel",
        label="bene yisrael / sons of Israel",
        terms=("sons", "israel", "tribes", "nation", "inheritance", "boundary"),
    ),
)


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


def _load_anchor_tokens(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    bag: set[str] = set()
    if not isinstance(rows, list):
        return bag
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = " ".join(
            str(row.get(k, ""))
            for k in ("entry_id", "canonical_ref", "satellite_ref", "corpus_type", "evidence_ref")
        )
        for m in WORD_RE.finditer(text.lower()):
            tok = m.group(0).strip()
            if len(tok) >= 3:
                bag.add(tok)
    return bag


def _load_symbol_weights(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in _iter_jsonl(path):
        symbol = str(row.get("symbol", "")).strip().lower()
        if not symbol:
            continue
        tfidf = float(row.get("score_tfidf_like", 0.0) or 0.0)
        mix = row.get("source_mix", {})
        if not isinstance(mix, dict):
            mix = {}
        dss = float(mix.get("dss", 0.0) or 0.0)
        apo = float(mix.get("apocrypha", 0.0) or 0.0)
        total = dss + apo
        dss_ratio = (dss / total) if total > 0 else 0.0
        out[symbol] = {
            "tfidf": tfidf,
            "dss_ratio": dss_ratio,
            "source_count": total,
        }
    return out


def _load_dss_overlay(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    term_map = payload.get("term_map", {})
    if not isinstance(term_map, dict):
        return {}
    out: dict[str, float] = {}
    for token, spec in term_map.items():
        if not isinstance(token, str) or not isinstance(spec, dict):
            continue
        w = spec.get("dss_weight", 0.0)
        if isinstance(w, (int, float)) and float(w) > 0:
            out[token.lower()] = float(w)
    return out


def _token_score(
    token: str,
    symbol_weights: dict[str, dict[str, float]],
    anchor_tokens: set[str],
    dss_overlay: dict[str, float],
) -> dict[str, float]:
    aliases = TOKEN_ALIASES.get(token, (token,))
    lexical = 0.0
    dss_align = 0.0
    anchor_affinity = 0.0
    for key in aliases:
        row = symbol_weights.get(key, {"tfidf": 0.0, "dss_ratio": 0.0, "source_count": 0.0})
        lexical = max(lexical, float(row["tfidf"]))
        dss_align = max(dss_align, float(row["dss_ratio"]))
        if key in anchor_tokens:
            anchor_affinity = 1.0
    if token in dss_overlay:
        dss_align = max(dss_align, float(dss_overlay[token]))
    total = lexical * 0.70 + (dss_align * 100.0) * 0.20 + (anchor_affinity * 10.0) * 0.10
    return {
        "lexical": round(lexical, 6),
        "dss_align": round(dss_align, 6),
        "anchor_affinity": round(anchor_affinity, 6),
        "score": round(total, 6),
    }


def _as_4d(reading_id: str, normalized: float) -> dict[str, float]:
    if reading_id == "sons_of_god":
        s = min(1.0, 0.48 + normalized * 0.35)
        l = min(1.0, 0.42 + normalized * 0.20)
        k = min(1.0, 0.44 + normalized * 0.25)
        m = min(1.0, 0.36 + normalized * 0.10)
    else:
        s = min(1.0, 0.38 + normalized * 0.22)
        l = min(1.0, 0.50 + normalized * 0.30)
        k = min(1.0, 0.41 + normalized * 0.18)
        m = min(1.0, 0.46 + normalized * 0.24)
    return {
        "S": round(s, 6),
        "L": round(l, 6),
        "K": round(k, 6),
        "M": round(m, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build semantic gap analysis report for Deut 32:8")
    ap.add_argument("--symbols", default=str(IN_SYMBOLS))
    ap.add_argument("--anchor", default=str(IN_ANCHOR))
    ap.add_argument("--dss-lexicon", default=str(IN_DSS_LEXICON))
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument(
        "--per-token-cap-ratio",
        type=float,
        default=0.35,
        help="Max share per token in a reading score (0..1).",
    )
    args = ap.parse_args()

    symbols_path = _abs(args.symbols)
    anchor_path = _abs(args.anchor)
    dss_lexicon_path = _abs(args.dss_lexicon)
    out_path = _abs(args.out)
    for p in (symbols_path, anchor_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    symbol_weights = _load_symbol_weights(symbols_path)
    anchor_tokens = _load_anchor_tokens(anchor_path)
    dss_overlay = _load_dss_overlay(dss_lexicon_path)

    reading_rows: list[dict[str, Any]] = []
    max_score = 0.0
    for reading in READINGS:
        term_rows = []
        total = 0.0
        for token in reading.terms:
            ts = _token_score(token, symbol_weights, anchor_tokens, dss_overlay)
            total += ts["score"]
            term_rows.append({"token": token, **ts})
        # Cap dominant token contribution to reduce single-token sensitivity.
        cap_base = total * float(args.per_token_cap_ratio)
        if cap_base > 0:
            capped_total = 0.0
            for t in term_rows:
                raw = float(t["score"])
                capped = min(raw, cap_base)
                t["score_raw"] = round(raw, 6)
                t["score_capped"] = round(capped, 6)
                capped_total += capped
            total = capped_total
        else:
            for t in term_rows:
                t["score_raw"] = round(float(t["score"]), 6)
                t["score_capped"] = round(float(t["score"]), 6)
        max_score = max(max_score, total)
        reading_rows.append(
            {
                "reading_id": reading.reading_id,
                "label": reading.label,
                "terms": list(reading.terms),
                "term_scores": term_rows,
                "per_token_cap_ratio": float(args.per_token_cap_ratio),
                "raw_score": round(total, 6),
            }
        )

    for row in reading_rows:
        normalized = (row["raw_score"] / max_score) if max_score > 0 else 0.0
        row["normalized_score"] = round(normalized, 6)
        row["lambda_deviation_from_sep_0_25"] = round(abs(0.25 - normalized), 6)
        row["profile_4d"] = _as_4d(str(row["reading_id"]), float(normalized))
        dss_terms = 0
        for t in row["term_scores"]:
            if float(t.get("dss_align", 0.0)) > 0:
                dss_terms += 1
        row["dss_supported_terms"] = dss_terms

    sorted_rows = sorted(reading_rows, key=lambda x: float(x["normalized_score"]), reverse=True)
    winner = sorted_rows[0]
    loser = sorted_rows[1] if len(sorted_rows) > 1 else None
    margin = round(float(winner["normalized_score"]) - float(loser["normalized_score"]), 6) if loser else 0.0
    winner_dss_terms = int(winner.get("dss_supported_terms", 0))
    decision = "provisional_accept" if margin >= 0.05 else "hold_for_review"
    if winner_dss_terms == 0:
        decision = "hold_for_review"
    if decision == "hold_for_review":
        decision_tier = "contested"
    elif margin >= 0.20 and winner_dss_terms >= 3:
        decision_tier = "strong_provisional"
    else:
        decision_tier = "provisional"

    report = {
        "schema": "semantic_gap_analysis_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": {
            "reference": "Deut.32:8",
            "scope": "textual_variant_pilot",
            "note": "Pilot scoring only. This report does not generate scripture text.",
        },
        "inputs": {
            "symbol_candidates_source": str(symbols_path),
            "anchor_matrix": str(anchor_path),
            "dss_lexicon_overlay": str(dss_lexicon_path) if dss_overlay else None,
            "anchor_token_count": len(anchor_tokens),
        },
        "readings": sorted_rows,
        "decision": {
            "status": decision,
            "tier": decision_tier,
            "winner_reading_id": winner["reading_id"],
            "winner_label": winner["label"],
            "margin": margin,
            "winner_dss_supported_terms": winner_dss_terms,
            "policy": {
                "accept_if_margin_gte": 0.05,
                "require_winner_dss_supported_terms_gte": 1,
                "else": "hold_for_review",
            },
            "communication_guardrail": {
                "forbidden_terms_when_tier_not_strong": ["정답", "확정", "final accept"],
                "preferred_terms": ["우세 가설", "provisional", "추가 검증 필요"],
            },
        },
        "boundaries": {
            "fact": [
                "Uses only local curated symbol candidates and anchor matrix artifacts.",
                "Produces deterministic numeric score with visible token-level contributions.",
            ],
            "hypothesis": [
                "4D profile mapping from normalized score is a pilot heuristic.",
                "Decision is for semantic triage, not final theological restoration.",
            ],
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: semantic gap analysis generated")
    print(f"out={out_path}")
    print(f"winner={winner['reading_id']} margin={margin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
