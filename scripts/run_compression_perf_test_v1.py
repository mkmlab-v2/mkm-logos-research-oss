#!/usr/bin/env python3
"""Run Track A compression performance test with logic-aware shadow filter.

This script performs A/B in shadow mode only:
- raw_baseline: existing Track A-like settings
- logic_aware_shadow: adds shadow must_keep terms from extracted logic weights
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_DEFAULT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
WEIGHTS_DEFAULT = ROOT / "reports/tracka_logic_weights_shadow_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/compression_perf_test_v1_latest.json"
WORD_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]{2,}")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _cmp_metrics(report: dict[str, Any]) -> dict[str, float]:
    c = report.get("compression_metrics") or {}
    return {
        "case_count": float(c.get("case_count") or 0),
        "global_token_saving_rate": float(c.get("global_token_saving_rate") or 0.0),
        "avg_reconstruction_fidelity_jaccard": float(c.get("avg_reconstruction_fidelity_jaccard") or 0.0),
        "avg_sensitive_integrity": float(c.get("avg_sensitive_integrity") or 0.0),
        "min_sensitive_integrity": float(c.get("min_sensitive_integrity") or 0.0),
    }


def _corpus_terms(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in (doc.get("compression_cases") or []):
        raw = str(row.get("raw_text") or "")
        for w in WORD_RE.findall(raw.lower()):
            if len(w) >= 2:
                out.add(w)
    return out


def build(*, input_path: Path, weights_path: Path, mode_logic_aware: bool) -> dict[str, Any]:
    doc = _load(input_path)
    wdoc = _load(weights_path) if weights_path.is_file() else {}
    weighted = wdoc.get("weighted_terms") or []
    corpus_terms = _corpus_terms(doc)
    shadow_terms: list[str] = []
    for t in weighted:
        term = str(t.get("term") or "").lower().strip()
        if not term:
            continue
        if term in corpus_terms:
            shadow_terms.append(term)
    if not shadow_terms:
        shadow_terms = [str(t.get("term") or "").lower().strip() for t in weighted[:24] if str(t.get("term") or "").strip()]

    common_cfg = {
        "source_input": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "mode": "baseline",
        "use_domain_router": True,
        "use_master_codebook_lexicon_v1": True,
        "emit_semantic_pointer": True,
    }

    raw = evaluate_report(
        doc,
        source_input=common_cfg["source_input"],
        mode="experimental",
        strategy="C",
        intensity="high",
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        emit_semantic_pointer=True,
    )

    if mode_logic_aware:
        logic_shadow = evaluate_report(
            doc,
            source_input=common_cfg["source_input"],
            mode="experimental",
            strategy="C",
            intensity="high",
            use_domain_router=True,
            use_master_codebook_lexicon_v1=True,
            emit_semantic_pointer=True,
            must_keep=set(shadow_terms),
        )
    else:
        logic_shadow = raw

    raw_m = _cmp_metrics(raw)
    sh_m = _cmp_metrics(logic_shadow)

    return {
        "schema": "compression_perf_test_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "production_policy_unchanged": True,
        },
        "input": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "logic_weights": str(weights_path.relative_to(ROOT)).replace("\\", "/") if weights_path.is_file() else None,
        "logic_aware_mode": "shadow_only" if mode_logic_aware else "off",
        "logic_aware_terms_count": len(shadow_terms),
        "logic_aware_terms_preview": shadow_terms[:20],
        "raw_baseline": {
            "metrics": raw_m,
            "quality_gate": raw.get("quality_gate"),
        },
        "logic_aware_shadow": {
            "metrics": sh_m,
            "quality_gate": logic_shadow.get("quality_gate"),
        },
        "delta_shadow_minus_raw": {
            "global_token_saving_rate": round(sh_m["global_token_saving_rate"] - raw_m["global_token_saving_rate"], 6),
            "avg_reconstruction_fidelity_jaccard": round(
                sh_m["avg_reconstruction_fidelity_jaccard"] - raw_m["avg_reconstruction_fidelity_jaccard"], 6
            ),
            "avg_sensitive_integrity": round(sh_m["avg_sensitive_integrity"] - raw_m["avg_sensitive_integrity"], 6),
        },
        "reports_embedded": {
            "raw_case_count": len((raw.get("compression_metrics") or {}).get("cases") or []),
            "shadow_case_count": len((logic_shadow.get("compression_metrics") or {}).get("cases") or []),
        },
        "reproduce": "py scripts/run_compression_perf_test_v1.py --logic-aware-shadow",
    }


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (ROOT / path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_DEFAULT)
    ap.add_argument("--weights", type=Path, default=WEIGHTS_DEFAULT)
    ap.add_argument("--logic-aware-shadow", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    input_path = _resolve(args.input)
    weights_path = _resolve(args.weights)
    out_path = _resolve(args.out)

    doc = build(
        input_path=input_path,
        weights_path=weights_path,
        mode_logic_aware=bool(args.logic_aware_shadow),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool((doc.get("raw_baseline") or {}).get("metrics", {}).get("case_count", 0)) > 0
    print(
        json.dumps(
            {
                "ok": ok,
                "logic_aware_terms_count": doc.get("logic_aware_terms_count"),
                "delta": doc.get("delta_shadow_minus_raw"),
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
