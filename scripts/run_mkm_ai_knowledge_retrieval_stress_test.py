from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def main() -> int:
    root = Path("C:/workspace")
    artifacts_dir = root / "docs" / "final" / "artifacts"

    corpus_paths = [
        root / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md",
        root / ".cursorrules",
        artifacts_dir / "mkm_ai_status_pointer_latest.json",
        artifacts_dir / "mkm_ai_v2_promotion_decision_latest.json",
        artifacts_dir / "mkm_ai_v2_weekly_readiness_report_latest.json",
        artifacts_dir / "mkm_ai_final_ops_bundle_latest.json",
    ]

    corpora: Dict[str, str] = {str(p): _load(p) for p in corpus_paths}

    # Query set focuses on mission-critical retrieval anchors.
    queries: List[Dict[str, str]] = [
        {"id": "q1_status", "pattern": r"APPROVED_FINAL_V2"},
        {"id": "q2_label", "pattern": r"MKM AI v2\.0 \(Final\)"},
        {"id": "q3_decision", "pattern": r"GO_FINAL_V2"},
        {"id": "q4_weekly", "pattern": r"weekly_pass_rate_percent"},
        {"id": "q5_guard", "pattern": r"MkmAiFinalOpsGuard|final ops guard"},
        {"id": "q6_ltm", "pattern": r"MKM12_LTM_DB_TYPE=file"},
        {"id": "q7_mirror", "pattern": r"sync_notebooklm_sources_to_mkm_data_vault"},
    ]

    results = []
    total_hits = 0
    latency_samples_ms: List[float] = []

    for q in queries:
        t0 = time.perf_counter()
        hits = []
        regex = re.compile(q["pattern"], flags=re.IGNORECASE)
        for path, body in corpora.items():
            if not body:
                continue
            if regex.search(body):
                hits.append(path)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        latency_samples_ms.append(elapsed_ms)
        total_hits += 1 if hits else 0
        results.append(
            {
                "query_id": q["id"],
                "pattern": q["pattern"],
                "hit": bool(hits),
                "hit_count": len(hits),
                "hit_paths": hits,
                "latency_ms": elapsed_ms,
            }
        )

    sample_count = len(results)
    hit_rate = round((total_hits / sample_count) * 100.0, 2) if sample_count else 0.0
    avg_latency = round(sum(latency_samples_ms) / len(latency_samples_ms), 3) if latency_samples_ms else 0.0
    p95_latency = round(sorted(latency_samples_ms)[int((len(latency_samples_ms) - 1) * 0.95)], 3) if latency_samples_ms else 0.0

    # Pass gate: all critical anchors found and retrieval is sub-50ms on this local corpus test.
    passed = hit_rate == 100.0 and avg_latency <= 50.0

    payload = {
        "schema": "mkm_ai_knowledge_retrieval_stress_v1",
        "generated_at_utc": _utc_now(),
        "corpus_count": len(corpora),
        "query_count": sample_count,
        "hit_rate_percent": hit_rate,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "passed": passed,
        "queries": results,
    }

    out_json = artifacts_dir / "mkm_ai_knowledge_retrieval_stress_latest.json"
    out_md = artifacts_dir / "mkm_ai_knowledge_retrieval_stress_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM AI Knowledge Retrieval Stress (Latest)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- hit_rate_percent: `{hit_rate}`",
        f"- avg_latency_ms: `{avg_latency}`",
        f"- p95_latency_ms: `{p95_latency}`",
        f"- passed: `{str(passed).lower()}`",
        "",
        "## Query Results",
    ]
    for row in results:
        md_lines.append(
            f"- {row['query_id']}: hit=`{str(row['hit']).lower()}` latency_ms=`{row['latency_ms']}` paths=`{row['hit_count']}`"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"knowledge stress written: {out_json}")
    print(f"hit_rate_percent={hit_rate} avg_latency_ms={avg_latency} passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
