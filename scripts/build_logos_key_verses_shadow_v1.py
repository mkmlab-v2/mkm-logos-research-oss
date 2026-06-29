#!/usr/bin/env python3
"""Build key-verse shadow post-it metadata from Phase O artifacts [HYPO]."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/verse_metadata_shadow_v1_latest.json"
VERSE_JSONL_DEFAULT = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PATH_GATE_DEFAULT = ROOT / "reports/logos_path_verification_gate_v1_latest.json"
PRESETS_DEFAULT = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
ART = ROOT / "docs/final/artifacts"

_AXES = ("S", "L", "K", "M")
_TAG_MAP = {
    "S": {"ko": "태양", "en": "taeyang"},
    "L": {"ko": "소양", "en": "soyang"},
    "K": {"ko": "태음", "en": "taeeum"},
    "M": {"ko": "소음", "en": "soeum"},
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_vid(vid: str) -> str:
    v = (vid or "").strip()
    if v.lower().startswith("john."):
        return "Jhn." + v.split(".", 1)[1]
    return v


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_verse_4d(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != "logos_verse_4d_v1":
                continue
            vid = _normalize_vid(str(row.get("verse_id") or ""))
            vec = row.get("vector_4d") or {}
            if not vid or not isinstance(vec, dict):
                continue
            try:
                out[vid] = {k: float(vec[k]) for k in _AXES}
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _distribution(vec: dict[str, float]) -> dict[str, float]:
    floor = 1e-9
    vals = {k: max(float(vec.get(k, 0.0)), floor) for k in _AXES}
    denom = sum(vals.values()) or 1.0
    return {k: round(vals[k] / denom, 6) for k in _AXES}


def _build_confidence(dist: dict[str, float], top_axis: str) -> float:
    sorted_vals = sorted(dist.values(), reverse=True)
    top = sorted_vals[0] if sorted_vals else 0.0
    second = sorted_vals[1] if len(sorted_vals) > 1 else 0.0
    margin = max(0.0, top - second)
    bonus = min(0.15, top * 0.15)
    return round(min(0.99, max(0.5, top + margin + bonus)), 4)


def _deep_push_freq() -> tuple[Counter[str], dict[str, list[str]]]:
    freq: Counter[str] = Counter()
    reasons: dict[str, list[str]] = {}
    if not PRESETS_DEFAULT.is_file():
        return freq, reasons
    presets = _load(PRESETS_DEFAULT)
    for tid in (presets.get("themes") or {}):
        locked = ART / f"logos_deep_research_distill_{tid}_citation_lock_latest.json"
        doc = _load(locked) if locked.is_file() else _load(ART / f"logos_deep_research_distill_{tid}_latest.json")
        for ref in doc.get("evidence_refs") or []:
            if not isinstance(ref, dict):
                continue
            vid = _normalize_vid(str(ref.get("verse_id") or ""))
            if not vid:
                continue
            freq[vid] += 2
            reasons.setdefault(vid, []).append(f"deep_push:{tid}")
    return freq, reasons


def _anchor_theme_freq(verse_jsonl: Path) -> tuple[Counter[str], dict[str, list[str]]]:
    freq: Counter[str] = Counter()
    reasons: dict[str, list[str]] = {}
    if not PRESETS_DEFAULT.is_file() or not verse_jsonl.is_file():
        return freq, reasons
    presets = _load(PRESETS_DEFAULT)
    prefixes = [str(t.get("verse_prefix") or "") for t in (presets.get("themes") or {}).values() if t.get("verse_prefix")]
    if not prefixes:
        return freq, reasons
    with verse_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != "logos_verse_4d_v1":
                continue
            vid = _normalize_vid(str(row.get("verse_id") or ""))
            if not vid:
                continue
            for pfx in prefixes:
                if vid.startswith(pfx):
                    freq[vid] += 1
                    reasons.setdefault(vid, []).append("theme_prefix_anchor")
                    break
    return freq, reasons


def build(
    *,
    verse_jsonl: Path,
    path_gate: Path,
    top_n: int,
    supplement_deep_push: bool = False,
    supplement_anchor: bool = False,
) -> dict[str, Any]:
    verse_idx = _load_verse_4d(verse_jsonl)
    gate = _load(path_gate)
    checks = gate.get("checks") or []

    freq: Counter[str] = Counter()
    reasons: dict[str, list[str]] = {}
    for chk in checks:
        unit_id = str(chk.get("unit_id") or "")
        for c in (chk.get("citations") or []):
            vid = _normalize_vid(str(c))
            if not vid:
                continue
            freq[vid] += 1
            reasons.setdefault(vid, []).append(unit_id)

    if supplement_deep_push:
        dp_freq, dp_reasons = _deep_push_freq()
        freq.update(dp_freq)
        for vid, units in dp_reasons.items():
            reasons.setdefault(vid, []).extend(units)

    if supplement_anchor:
        an_freq, an_reasons = _anchor_theme_freq(verse_jsonl)
        freq.update(an_freq)
        for vid, units in an_reasons.items():
            reasons.setdefault(vid, []).extend(units)

    key_rows: list[dict[str, Any]] = []
    for verse_id, hit_count in freq.most_common(max(1, top_n)):
        vec = verse_idx.get(verse_id)
        if not vec:
            continue
        dist = _distribution(vec)
        primary_axis = max(_AXES, key=lambda k: dist[k])
        key_rows.append(
            {
                "verse_id": verse_id,
                "tag_distribution": {
                    "태양": dist["S"],
                    "소양": dist["L"],
                    "태음": dist["K"],
                    "소음": dist["M"],
                },
                "primary_tag": _TAG_MAP[primary_axis]["ko"],
                "confidence": _build_confidence(dist, primary_axis),
                "evidence": {
                    "citation_hit_count": int(hit_count),
                    "source_units": sorted(set(reasons.get(verse_id) or []))[:12],
                    "vector_4d": {k: round(vec[k], 6) for k in _AXES},
                    "source": "logos_path_verification_gate_v1.checks.citations",
                },
                "non_gating": True,
                "research_only": True,
            }
        )

    return {
        "schema": "verse_metadata_shadow_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "ms_headline_merge_forbidden": True,
        },
        "inputs": {
            "verse_jsonl": str(verse_jsonl),
            "path_gate_json": str(path_gate),
            "selection": "merged_path_gate_deep_push_theme_anchor",
            "top_n": int(top_n),
            "supplement_deep_push": supplement_deep_push,
            "supplement_anchor": supplement_anchor,
        },
        "summary": {
            "candidate_cited_verses": len(freq),
            "shadow_rows": len(key_rows),
        },
        "rows": key_rows,
        "reproduce": "py scripts/build_logos_key_verses_shadow_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-jsonl", type=Path, default=VERSE_JSONL_DEFAULT)
    ap.add_argument("--path-gate", type=Path, default=PATH_GATE_DEFAULT)
    ap.add_argument("--top-n", type=int, default=128)
    ap.add_argument("--supplement-deep-push", action="store_true")
    ap.add_argument("--supplement-anchor", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build(
        verse_jsonl=args.verse_jsonl,
        path_gate=args.path_gate,
        top_n=max(1, int(args.top_n)),
        supplement_deep_push=args.supplement_deep_push,
        supplement_anchor=args.supplement_anchor,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = int((doc.get("summary") or {}).get("shadow_rows") or 0) > 0
    print(json.dumps({"ok": ok, "shadow_rows": doc["summary"]["shadow_rows"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
