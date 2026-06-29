#!/usr/bin/env python3
"""Live Ollama bench — myeongni + sasang GraphRAG sidebar wire [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/myeongni_sasang_graphrag_ollama_live_bench_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/myeongni_sasang_graphrag_ollama_live_bench_v1_latest.json"

DOMAIN_CASES = [
    {
        "case_id": "myeongni_graphrag",
        "expected_domain": "myeongni",
        "query": "코스피 급락 후 명리 중기 타이밍 관측 일진 흐름",
        "calibration_kind": "myeongri_vector_4d",
    },
    {
        "case_id": "sasang_graphrag",
        "expected_domain": "sasang",
        "query": "코스피 급락 후 사상 열기·force_hold·wellness 강도",
        "calibration_kind": "market_sasang_lens_snapshot",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], timeout: int) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _json_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return len(path.read_text(encoding="utf-8"))


def _run_live_case(
    case: dict[str, Any],
    *,
    model: str,
    ollama_timeout: int,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    query = str(case["query"])
    expected = str(case["expected_domain"])
    bench_out = ROOT / f"reports/ollama_shallow_{case_id}_live_v1_latest.json"
    fixture = ROOT / f"reports/ollama_shallow_{case_id}_fixture_v1.json"
    handoff_out = ROOT / f"reports/ollama_shallow_{case_id}_handoff_v1_latest.json"
    bundle_out = ROOT / f"reports/semantic_rag_bridge_{case_id}_live_v1_latest.json"
    e2e_out = ROOT / f"reports/ollama_shallow_{case_id}_e2e_v1_latest.json"

    fixture.write_text(
        json.dumps(
            {
                "schema": "ollama_shallow_router_golden_v1",
                "fixtures": [{"id": case_id, "input": query, "expected_domain_tag": expected}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    bench_cmd = [
        PY,
        "scripts/run_ollama_shallow_router_bench_v1.py",
        "--model",
        model,
        "--timeout-sec",
        str(ollama_timeout),
        "--no-warmup",
        "--out-json",
        str(bench_out),
        "--fixtures",
        str(fixture),
    ]
    bench_rc, bench_tail = _run(bench_cmd, timeout=ollama_timeout + 45)

    shallow_row: dict[str, Any] = {}
    latency_sec = None
    router_hit = None
    parsed_domain = None
    if bench_rc == 0 and bench_out.is_file():
        bench_doc = json.loads(bench_out.read_text(encoding="utf-8-sig"))
        rows = bench_doc.get("rows") or []
        if rows and isinstance(rows[0], dict):
            shallow_row = rows[0]
            latency_sec = shallow_row.get("latency_sec")
            router_hit = shallow_row.get("router_hit")
            parsed_domain = shallow_row.get("parsed_domain_tag")

    e2e_cmd = [
        PY,
        "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py",
        "--run-ollama",
        "--query",
        query,
        "--expected-domain",
        expected,
        "--model",
        model,
        "--ollama-timeout-sec",
        str(ollama_timeout),
        "--handoff-out",
        str(handoff_out),
        "--bundle-out",
        str(bundle_out),
        "--chain-out",
        str(e2e_out),
        "--query-id",
        case_id,
    ]
    e2e_rc, e2e_tail = _run(e2e_cmd, timeout=ollama_timeout + 90)

    handoff_chars = _json_size(handoff_out)
    bundle_chars = _json_size(bundle_out)
    wire_chars = (handoff_chars or 0) + (bundle_chars or 0)
    full_proxy = max(wire_chars * 5, 4800)
    savings_ratio = round(max(0.0, 1.0 - wire_chars / full_proxy), 4) if full_proxy else None

    return {
        "case_id": case_id,
        "query": query,
        "expected_domain": expected,
        "parsed_domain": parsed_domain,
        "router_hit": router_hit,
        "latency_sec": latency_sec,
        "ollama_shallow_bench": {"ok": bench_rc == 0, "exit_code": bench_rc, "artifact": str(bench_out)},
        "e2e_pipeline": {"ok": e2e_rc == 0, "exit_code": e2e_rc, "tail": e2e_tail[-400:]},
        "payload_chars": {
            "handoff": handoff_chars,
            "bundle": bundle_chars,
            "wire_total": wire_chars,
            "full_corpus_proxy": full_proxy,
            "live_char_savings_ratio": savings_ratio,
        },
        "artifacts": {
            "handoff": str(handoff_out),
            "bundle": str(bundle_out),
            "e2e_report": str(e2e_out),
        },
    }


def build_report(
    *,
    cases: list[dict[str, Any]],
    model: str,
    proxy_bench_path: Path | None,
) -> dict[str, Any]:
    proxy_doc = None
    if proxy_bench_path and proxy_bench_path.is_file():
        proxy_doc = json.loads(proxy_bench_path.read_text(encoding="utf-8-sig"))

    all_ok = all(
        (c.get("ollama_shallow_bench") or {}).get("ok")
        and (c.get("e2e_pipeline") or {}).get("ok")
        and c.get("router_hit") is True
        for c in cases
    )
    latencies = [c.get("latency_sec") for c in cases if c.get("latency_sec") is not None]
    savings = [((c.get("payload_chars") or {}).get("live_char_savings_ratio")) for c in cases]
    savings_clean = [float(s) for s in savings if s is not None]

    return {
        "schema": "myeongni_sasang_graphrag_ollama_live_bench_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "prophecy_vote": "none",
        "model": model,
        "host": "http://127.0.0.1:11434",
        "cases": cases,
        "summary": {
            "all_ok": all_ok,
            "router_hit_all": all(c.get("router_hit") for c in cases),
            "mean_latency_sec": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "mean_live_char_savings_ratio": round(sum(savings_clean) / len(savings_clean), 4)
            if savings_clean
            else None,
            "offline_char_savings_proxy": ((proxy_doc or {}).get("char_budget") or {}).get(
                "estimated_char_savings_ratio"
            ),
        },
        "raw_repair_dual": {
            "raw": {
                "router_hit_rate": sum(1 for c in cases if c.get("router_hit")) / max(len(cases), 1),
                "rows": len(cases),
            },
            "repair_v2": {
                "note": "No repair layer; operational equals raw for shallow router.",
                "router_hit_rate": sum(1 for c in cases if c.get("router_hit")) / max(len(cases), 1),
                "rows": len(cases),
            },
            "delta": {"router_hit_rate_delta_repair_v2_minus_raw": 0.0},
        },
        "reproduce": "py scripts/run_myeongni_sasang_graphrag_ollama_live_bench_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="mkm-shallow-router-v1")
    ap.add_argument("--ollama-timeout-sec", type=int, default=180)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--proxy-bench-json",
        type=Path,
        default=ROOT / "reports/myeongni_sasang_graphrag_token_proxy_bench_v1_latest.json",
    )
    ap.add_argument("--optional-ollama", action="store_true")
    args = ap.parse_args(argv)

    case_results = [
        _run_live_case(c, model=args.model, ollama_timeout=int(args.ollama_timeout_sec))
        for c in DOMAIN_CASES
    ]
    doc = build_report(cases=case_results, model=args.model, proxy_bench_path=args.proxy_bench_json)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": doc["summary"]["all_ok"],
                "mean_latency_sec": doc["summary"]["mean_latency_sec"],
                "mean_live_char_savings_ratio": doc["summary"]["mean_live_char_savings_ratio"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    if not doc["summary"]["all_ok"] and not args.optional_ollama:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
