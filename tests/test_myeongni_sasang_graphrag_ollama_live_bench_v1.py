"""Live Ollama bench smoke for myeongni+sasang graphrag wire."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_live_bench_schema_offline_shape() -> None:
    from scripts.run_myeongni_sasang_graphrag_ollama_live_bench_v1 import build_report

    cases = [
        {
            "case_id": "myeongni_graphrag",
            "query": "q",
            "expected_domain": "myeongni",
            "parsed_domain": "myeongni",
            "router_hit": True,
            "latency_sec": 1.2,
            "ollama_shallow_bench": {"ok": True, "exit_code": 0},
            "e2e_pipeline": {"ok": True, "exit_code": 0},
            "payload_chars": {"live_char_savings_ratio": 0.75, "wire_total": 900},
        }
    ]
    doc = build_report(cases=cases, model="mkm-shallow-router-v1", proxy_bench_path=None)
    assert doc["schema"] == "myeongni_sasang_graphrag_ollama_live_bench_v1"
    assert doc["prophecy_vote"] == "none"


def test_live_bench_cli_optional() -> None:
    import scripts.run_myeongni_sasang_graphrag_ollama_live_bench_v1 as mod

    rc = mod.main(
        [
            "--optional-ollama",
            "--output-json",
            str(ROOT / "reports/myeongni_sasang_graphrag_ollama_live_bench_smoke_v1.json"),
            "--ollama-timeout-sec",
            "120",
        ]
    )
    assert rc in (0, 1)
    out = ROOT / "reports/myeongni_sasang_graphrag_ollama_live_bench_smoke_v1.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc.get("cases") or []) == 2
