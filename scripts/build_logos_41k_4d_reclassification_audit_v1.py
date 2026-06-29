#!/usr/bin/env python3
"""41k lexicon 4D projection audit + path-gate 4D shadow [HYPO / research_only]."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DEFAULT = ROOT / "reports/logos_41k_4d_reclassification_audit_v1_latest.json"
VERSE_CITE_RE = re.compile(
    r"\b((?:Dan|Jhn|John|1John|Jer|Jas)\.\d+\.\d+)\b",
    re.IGNORECASE,
)
_AXES = ("S", "L", "K", "M")
_TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "track_a_bridge": False,
    "ms_headline_merge_forbidden": True,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _normalize_vid(vid: str) -> str:
    v = vid.strip()
    if v.lower().startswith("john."):
        return "Jhn." + v.split(".", 1)[1]
    return v


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in _AXES))


def _coerce_4d(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    try:
        return {k: float(raw[k]) for k in _AXES}
    except (KeyError, TypeError, ValueError):
        return None


def load_verse_4d_index(verse_jsonl: Path, *, max_rows: int = 0) -> dict[str, dict[str, float]]:
    idx: dict[str, dict[str, float]] = {}
    if not verse_jsonl.is_file():
        return idx
    n = 0
    with verse_jsonl.open(encoding="utf-8") as f:
        for line in f:
            if max_rows and n >= max_rows:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != "logos_verse_4d_v1":
                continue
            vid = str(row.get("verse_id") or "")
            vec = _coerce_4d(row.get("vector_4d"))
            if vid and vec is not None:
                idx[_normalize_vid(vid)] = vec
            n += 1
    return idx


def lexicon_coverage(lexicon_doc: dict[str, Any], codebook_doc: dict[str, Any]) -> dict[str, Any]:
    rows = lexicon_doc.get("rows") or []
    codebook_entries = codebook_doc.get("entries") or []
    codebook_count = int(codebook_doc.get("row_count") or len(codebook_entries) or 0)
    lexicon_rows = len(rows)
    coverage = round(lexicon_rows / codebook_count, 6) if codebook_count else 0.0
    stats = lexicon_doc.get("stats") or {}
    return {
        "codebook_atom_count": codebook_count,
        "lexicon_4d_row_count": lexicon_rows,
        "lexicon_4d_coverage_rate": coverage,
        "min_verse_count_threshold": lexicon_doc.get("min_verse_count"),
        "verse_atom_match_rate": stats.get("verse_atom_match_rate"),
        "token_match_rate": stats.get("token_match_rate"),
        "projection_recipe": (lexicon_doc.get("inputs") or {}).get("overlay_recipe_id"),
    }


def path_four_d_shadow(path_gate: dict[str, Any], verse_index: dict[str, dict[str, float]]) -> dict[str, Any]:
    checks = path_gate.get("checks") or []
    unit_shadows: list[dict[str, Any]] = []
    coherence_scores: list[float] = []

    for chk in checks:
        cites = [_normalize_vid(c) for c in (chk.get("citations") or [])]
        if len(cites) < 2:
            unit_shadows.append(
                {
                    "unit_id": chk.get("unit_id"),
                    "four_d_coherence": 1.0,
                    "reason": "fewer_than_two_cites",
                    "human_review_hint": False,
                }
            )
            coherence_scores.append(1.0)
            continue

        vecs: list[dict[str, float]] = []
        missing: list[str] = []
        for c in cites:
            v = verse_index.get(c)
            if v is None:
                missing.append(c)
            else:
                vecs.append(v)

        if len(vecs) < 2:
            unit_shadows.append(
                {
                    "unit_id": chk.get("unit_id"),
                    "four_d_coherence": None,
                    "reason": "insufficient_verse_4d_index",
                    "missing_verse_ids": missing,
                    "human_review_hint": True,
                }
            )
            continue

        jumps = [_l2(vecs[i], vecs[i + 1]) for i in range(len(vecs) - 1)]
        mean_jump = sum(jumps) / len(jumps)
        coherence = round(max(0.0, 1.0 - mean_jump), 4)
        hint = coherence < 0.8
        unit_shadows.append(
            {
                "unit_id": chk.get("unit_id"),
                "four_d_coherence": coherence,
                "mean_l2_jump": round(mean_jump, 6),
                "jump_count": len(jumps),
                "reason": "verse_4d_path_projection",
                "human_review_hint": hint,
                "v_score_primary": chk.get("v_score"),
            }
        )
        coherence_scores.append(coherence)

    scored = [s for s in coherence_scores if s is not None]
    mean_coherence = round(sum(scored) / len(scored), 4) if scored else None
    below_08 = sum(1 for u in unit_shadows if u.get("human_review_hint") is True)

    return {
        "schema": "logos_path_four_d_shadow_v1",
        "non_gating": True,
        "does_not_affect_gate_pass": True,
        "human_review_threshold": 0.8,
        "units_shadowed": len(unit_shadows),
        "mean_four_d_coherence": mean_coherence,
        "human_review_hint_count": below_08,
        "units": unit_shadows,
    }


def build(
    *,
    lexicon_path: Path,
    codebook_path: Path,
    verse_jsonl_path: Path,
    path_gate_path: Path,
    residual_path: Path | None,
    max_verse_rows: int,
) -> dict[str, Any]:
    lexicon_doc = _load(lexicon_path)
    codebook_doc = _load(codebook_path)
    path_gate = _load(path_gate_path)
    residual = _load(residual_path) if residual_path and residual_path.is_file() else {}

    verse_index = load_verse_4d_index(verse_jsonl_path, max_rows=max_verse_rows)
    coverage = lexicon_coverage(lexicon_doc, codebook_doc)
    shadow = path_four_d_shadow(path_gate, verse_index)

    residual_summary = (residual.get("summary") or {}) if residual else {}
    ok = (
        coverage.get("lexicon_4d_row_count", 0) > 0
        and coverage.get("codebook_atom_count", 0) > 0
        and shadow.get("units_shadowed", 0) >= 0
    )

    return {
        "schema": "logos_41k_4d_reclassification_audit_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "track_wall": dict(_TRACK_WALL),
        "interpretation_guard": (
            "4D coherence is structural shadow on verse vectors — not prophecy, "
            "not B2B headline quality, not Track A compression. "
            "human_review_hint does not block output."
        ),
        "inputs": {
            "lexicon_4d_json": str(lexicon_path.relative_to(ROOT)).replace("\\", "/")
            if lexicon_path.is_relative_to(ROOT)
            else str(lexicon_path),
            "codebook_json": str(codebook_path),
            "verse_jsonl": str(verse_jsonl_path),
            "path_gate_json": str(path_gate_path),
            "residual_json": str(residual_path) if residual_path else None,
        },
        "phase_pa_residual": {
            "exact_match_rate": residual_summary.get("exact_match_rate"),
            "mismatch_rate": residual_summary.get("mismatch_rate"),
            "compared": residual_summary.get("compared"),
        },
        "phase_pb_lexicon_coverage": coverage,
        "phase_pc_path_four_d_shadow": shadow,
        "ok": ok,
        "reproduce": "py scripts/build_logos_41k_4d_reclassification_audit_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--lexicon-4d",
        type=Path,
        default=ROOT / "reports/logos_lexicon_4d_v1_latest.json",
    )
    ap.add_argument("--codebook-json", type=Path, default=None)
    ap.add_argument(
        "--verse-jsonl",
        type=Path,
        default=ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl",
    )
    ap.add_argument(
        "--path-gate",
        type=Path,
        default=ROOT / "reports/logos_path_verification_gate_v1_latest.json",
    )
    ap.add_argument(
        "--residual",
        type=Path,
        default=ROOT / "reports/logos_4d_exact_match_residual_v1_latest.json",
    )
    ap.add_argument("--max-verse-rows", type=int, default=0, help="0 = full verse jsonl index")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    codebook_path = args.codebook_json
    if codebook_path is None:
        from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: WPS433
            resolve_latest_codebook_path,
        )

        codebook_path = resolve_latest_codebook_path()
    if codebook_path is None or not Path(codebook_path).is_file():
        print(json.dumps({"ok": False, "error": "codebook_json missing"}))
        return 2
    codebook_path = Path(codebook_path)

    if not args.lexicon_4d.is_file():
        print(json.dumps({"ok": False, "error": f"missing lexicon_4d: {args.lexicon_4d}"}))
        return 2

    doc = build(
        lexicon_path=args.lexicon_4d,
        codebook_path=codebook_path,
        verse_jsonl_path=args.verse_jsonl,
        path_gate_path=args.path_gate,
        residual_path=args.residual,
        max_verse_rows=max(0, int(args.max_verse_rows)),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cov = doc["phase_pb_lexicon_coverage"]
    sh = doc["phase_pc_path_four_d_shadow"]
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "lexicon_4d_coverage_rate": cov.get("lexicon_4d_coverage_rate"),
                "mean_four_d_coherence": sh.get("mean_four_d_coherence"),
                "human_review_hint_count": sh.get("human_review_hint_count"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
