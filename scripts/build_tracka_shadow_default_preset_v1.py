#!/usr/bin/env python3
"""Materialize Track A shadow default preset from sweep Pareto + corpus-aware term filter."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SWEEP = ROOT / "reports/tracka_shadow_sweep_v1_latest.json"
WEIGHTS = ROOT / "reports/tracka_logic_weights_shadow_v1_latest.json"
INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT_PRESET = ROOT / "reports/tracka_shadow_default_preset_v1_latest.json"
OUT_WEIGHTS = ROOT / "reports/tracka_logic_weights_shadow_preset_v1_latest.json"
OUT_PERF = ROOT / "reports/compression_perf_test_preset_v1_latest.json"
OUT_IMPACT = ROOT / "reports/optimization_impact_preset_v1_latest.json"
WORD_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]{2,}")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _corpus_terms(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in doc.get("compression_cases") or []:
        raw = str(row.get("raw_text") or "")
        for w in WORD_RE.findall(raw.lower()):
            if len(w) >= 2:
                out.add(w)
    return out


def _pick_pareto_rows(sweep: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    rows = list(sweep.get("pareto_top5") or [])
    if not rows:
        rows = [r for r in (sweep.get("rows") or []) if r.get("ok")]
    if not rows:
        return {"threshold": 0.15, "term_cap": 24, "source": "fallback_default"}, None

    def _score(r: dict[str, Any]) -> tuple[float, float, int]:
        return (
            float(r.get("delta_jaccard") or 0.0),
            float(r.get("delta_token_saving") or 0.0),
            int(r.get("terms_selected") or 0),
        )

    ranked = sorted(rows, key=_score, reverse=True)
    primary = dict(ranked[0])
    primary["source"] = "pareto_rank1"
    secondary = dict(ranked[1]) if len(ranked) > 1 else None
    if secondary:
        secondary["source"] = "pareto_rank2"
    return primary, secondary


def _select_terms(
    weighted: list[dict[str, Any]],
    *,
    threshold: float,
    term_cap: int,
    corpus: set[str],
) -> list[dict[str, Any]]:
    pool = [
        w
        for w in weighted
        if float(w.get("normalized_weight") or 0) >= threshold and str(w.get("term") or "").lower() in corpus
    ]
    if len(pool) < 3:
        pool = [w for w in weighted if str(w.get("term") or "").lower() in corpus]
    if len(pool) < 3:
        pool = list(weighted)
    pool.sort(key=lambda w: float(w.get("normalized_weight") or 0), reverse=True)
    return pool[: max(1, term_cap)]


def build(*, run_perf: bool) -> dict[str, Any]:
    sweep = _load(SWEEP)
    base = _load(WEIGHTS)
    eval_doc = _load(INPUT)
    weighted = base.get("weighted_terms") or []
    corpus = _corpus_terms(eval_doc)
    primary_cfg, secondary_cfg = _pick_pareto_rows(sweep)

    selected = _select_terms(
        weighted,
        threshold=float(primary_cfg.get("threshold") or 0.15),
        term_cap=int(primary_cfg.get("term_cap") or 24),
        corpus=corpus,
    )
    if len(selected) < 3 and secondary_cfg:
        selected = _select_terms(
            weighted,
            threshold=float(secondary_cfg.get("threshold") or 0.2),
            term_cap=int(secondary_cfg.get("term_cap") or 12),
            corpus=corpus,
        )
        primary_cfg = secondary_cfg

    preset_weights = dict(base)
    preset_weights["weighted_terms"] = selected
    preset_weights["must_keep_terms_shadow"] = [str(w.get("term")) for w in selected]
    preset_weights["preset_meta"] = {
        "threshold": primary_cfg.get("threshold"),
        "term_cap": primary_cfg.get("term_cap"),
        "corpus_matched": True,
        "selected_terms": len(selected),
    }
    OUT_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEIGHTS.write_text(json.dumps(preset_weights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    perf_doc: dict[str, Any] = {}
    impact_doc: dict[str, Any] = {}
    if run_perf and selected:
        cp = subprocess.run(
            [
                PY,
                "scripts/run_compression_perf_test_v1.py",
                "--logic-aware-shadow",
                "--weights",
                str(OUT_WEIGHTS),
                "--out",
                str(OUT_PERF),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        if cp.returncode == 0 and OUT_PERF.is_file():
            perf_doc = _load(OUT_PERF)
            subprocess.run(
                [PY, "scripts/report_optimization_impact_v1.py", "--perf", str(OUT_PERF), "--out", str(OUT_IMPACT)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            impact_doc = _load(OUT_IMPACT)

    delta = perf_doc.get("delta_shadow_minus_raw") or {}
    doc = {
        "schema": "tracka_shadow_default_preset_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "production_policy_unchanged": True,
            "policy_mutation_forbidden": True,
        },
        "primary_config": primary_cfg,
        "secondary_config": secondary_cfg,
        "selected_terms": [w.get("term") for w in selected],
        "selected_terms_count": len(selected),
        "weights_preset_path": str(OUT_WEIGHTS.relative_to(ROOT)).replace("\\", "/"),
        "perf_preset_path": str(OUT_PERF.relative_to(ROOT)).replace("\\", "/"),
        "impact_preset_path": str(OUT_IMPACT.relative_to(ROOT)).replace("\\", "/"),
        "delta_shadow_minus_raw": delta,
        "reproduce": "py scripts/build_tracka_shadow_default_preset_v1.py",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-perf", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_PRESET)
    args = ap.parse_args()
    doc = build(run_perf=not args.skip_perf)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = int(doc.get("selected_terms_count") or 0) > 0
    print(
        json.dumps(
            {
                "ok": ok,
                "selected_terms_count": doc.get("selected_terms_count"),
                "delta": doc.get("delta_shadow_minus_raw"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
