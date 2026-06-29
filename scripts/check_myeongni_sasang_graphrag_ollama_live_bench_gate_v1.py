#!/usr/bin/env python3
"""Gate: myeongni+sasang GraphRAG Ollama live bench artifact (no Ollama re-run)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports/myeongni_sasang_graphrag_ollama_live_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/myeongni_sasang_graphrag_ollama_live_bench_gate_v1_latest.json"

PRODUCT_POLICY_KO = (
    "GraphRAG=사이드카·라우팅·감사 레일(wires_to_scoring_core:false). "
    "Ollama live bench=효율·router 근거. 킬러UX·답변 고급통찰 미결선."
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-char-savings", type=float, default=0.5)
    args = ap.parse_args(argv)

    if not args.input_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing_{args.input_json}"}))
        return 1

    doc = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
    summary = doc.get("summary") or {}
    cases = doc.get("cases") or []

    checks = {
        "schema_ok": doc.get("schema") == "myeongni_sasang_graphrag_ollama_live_bench_v1",
        "research_only": doc.get("research_only") is True,
        "send_gate_hold": doc.get("send_gate") == "HOLD",
        "all_ok": summary.get("all_ok") is True,
        "router_hit_all": summary.get("router_hit_all") is True,
        "cases_min_2": len(cases) >= 2,
        "char_savings_ok": (summary.get("mean_live_char_savings_ratio") or 0) >= args.min_char_savings,
    }
    passed = all(checks.values())

    out = {
        "ok": passed,
        "schema": "myeongni_sasang_graphrag_ollama_live_bench_gate_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": checks,
        "source_artifact": str(args.input_json),
        "summary": summary,
        "product_policy_ko": PRODUCT_POLICY_KO,
        "wires_to_scoring_core": False,
        "reproduce": "py scripts/check_myeongni_sasang_graphrag_ollama_live_bench_gate_v1.py",
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": passed, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
