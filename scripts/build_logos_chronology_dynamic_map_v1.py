#!/usr/bin/env python3
"""Map macro observation snapshot -> Logos chronology era candidates ([HYPO], NON_GATING).

Uses tag/bridge overlap + optional regime_map cosine probe. Does not assert theology or price direction.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logos_chronology_map_core_v1 import (
    POLICY,
    confidence_band,
    infer_tags_from_macro,
    load_json,
    rank_eras,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_MACRO = ROOT / "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json"
DEFAULT_REGIME_MAP = ROOT / "data/regimes/regime_map.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_dynamic_map_v1_latest.json"
PROBE = ROOT / "scripts/logos_vector_resonance_probe.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _optional_probe(regime: str, regime_map: Path) -> dict[str, Any] | None:
    if not PROBE.is_file() or not regime_map.is_file():
        return None
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "probe.json"
        cmd = [
            sys.executable,
            str(PROBE),
            "--rank-by-regime",
            "--regime",
            regime,
            "--regime-map",
            str(regime_map),
            "--top-k",
            "5",
            "--output",
            str(out),
        ]
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        if cp.returncode != 0 or not out.is_file():
            return {"status": "probe_failed", "stderr": (cp.stderr or cp.stdout or "")[:300]}
        return load_json(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--macro-json", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--regime-map-json", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-probe", action="store_true", help="Optional cosine probe for top inferred tag")
    args = ap.parse_args()

    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    macro_path = args.macro_json if args.macro_json.is_absolute() else ROOT / args.macro_json
    regime_map = args.regime_map_json if args.regime_map_json.is_absolute() else ROOT / args.regime_map_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not chrono_path.is_file():
        print(f"MISSING: {chrono_path}", file=sys.stderr)
        return 2
    if not macro_path.is_file():
        print(f"MISSING: {macro_path}", file=sys.stderr)
        return 2

    chrono = load_json(chrono_path)
    macro = load_json(macro_path)
    inferred = infer_tags_from_macro(macro)
    ranking = rank_eras(chrono, inferred)
    for r in ranking:
        matched = r.get("matched_tags") or []
        r["narrative_hint_ko"] = (
            f"[HYPO] 매크로 태그 {inferred}와 관측 태그 {matched or '—'} 정렬(비게이팅)."
        )
    if not ranking:
        print("No eras in chronology", file=sys.stderr)
        return 2

    top = ranking[0]
    band = confidence_band(float(top["score"]))
    primary = {
        "era_id": top["era_id"],
        "label_ko": top["label_ko"],
        "confidence_band": band,
        "interpretation_class": "[HYPO]",
        "operator_line_ko": (
            f"[HYPO·NON_GATING] 현재 매크로 스냅샷은 연대기 후보 '{top['label_ko']}'({top['era_id']})와 "
            f"구조적 유사도 점수 {top['score']:.3f}로 정렬됩니다. 신학·가격 확정·실매매 트리거 아님."
        ),
    }

    doc: dict[str, Any] = {
        "schema": "logos_chronology_dynamic_map_v1",
        "generated_at_utc": _now(),
        "policy": POLICY,
        "hypothesis_tier": "[HYPO]",
        "inputs": {
            "chronology_json": str(chrono_path.relative_to(ROOT)).replace("\\", "/"),
            "macro_json": str(macro_path.relative_to(ROOT)).replace("\\", "/"),
            "regime_map_json": str(regime_map.relative_to(ROOT)).replace("\\", "/"),
        },
        "inferred_regime_tags": inferred,
        "era_ranking": ranking[:12],
        "primary_match": primary,
    }

    if args.run_probe and inferred:
        probe_regime = inferred[0]
        for prefer in ("covid", "lehman", "imf", "it_bubble", "risk"):
            if prefer in inferred:
                probe_regime = prefer
                break
        doc["probe_optional"] = _optional_probe(probe_regime, regime_map)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"primary={primary['era_id']} score={top['score']} band={band} tags={inferred}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
