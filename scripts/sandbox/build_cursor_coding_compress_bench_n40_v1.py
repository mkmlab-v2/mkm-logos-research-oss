#!/usr/bin/env python3
"""Extend n20 dogfooding corpus → n40 (append 20 heavy/dynamic-diff cases)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N20 = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n20.jsonl"
DEFAULT_OUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl"

EXTRA_ROWS: list[dict[str, str]] = [
    {
        "id": "cc_n21",
        "lane": "code_context",
        "raw_text": "async def drain_queue(path: Path) -> list[dict]:\n    pending = export_pending_json(path)\n    for job in pending:\n        run_premium_multilens_report(job)\n    return pending\n\nAdd --allow-missing-queue without changing promotion gate semantics.",
    },
    {
        "id": "cc_n22",
        "lane": "stack_trace",
        "raw_text": "jsonschema.ValidationError: 'meta_channel' is a required property\n  tests/test_prism_meta_channel_parallel_v1.py:88\n  Fix schema fixture only — do not enable prepend injection.",
    },
    {
        "id": "cc_n23",
        "lane": "long_multifile",
        "raw_text": "Dogfood n40: run_prism_dynamic_pinset_bench_v1.py on data/btrack/cursor_coding_compress_bench_v1_n40.jsonl. Expect py_coding_dynamic pinset_ids_differ > 0. Files: scripts/sandbox/*.py, experiments/no_guard_limit_test/results/*_latest.json. Verify staging bundle strict exit 0 mechanical.",
    },
    {
        "id": "cc_n24",
        "lane": "agent_rules_excerpt",
        "raw_text": "ALWAYS: meta_channel_post_gatekeeper only. NEVER: inject pinset into compressed user text (prepend). MKM_PRISM_META_CHANNEL_BTRACK default off. Prism axes S+K+L for py_coding_dynamic.",
    },
    {
        "id": "cc_n25",
        "lane": "code_context",
        "raw_text": "def select_pinset(*, task_profile: str, selection_mode: str) -> dict:\n    entries = score_registry(registry, context_text, max_entries=3)\n    return {'entries': entries[:3], 'task_profile': task_profile}\n\nUnit test: context_scored must differ from fixed_preferred on code_context lane.",
    },
    {
        "id": "cc_n26",
        "lane": "stack_trace",
        "raw_text": "SystemExit: phase2 missing=['lane_b2_dynamic_heavy'] — re-run run_prism_dynamic_pinset_heavy_bench_v1.py before build_archive --require-phase2.",
    },
    {
        "id": "cc_n27",
        "lane": "code_context",
        "raw_text": "report = evaluate_report(doc, must_keep=must_keep | build_coding_must_keep(text), jaccard_drop_threshold_pp=1.5)\n# corpus_expansion +5000 must_keep is research-only — never default hardening path.",
    },
    {
        "id": "cc_n28",
        "lane": "long_multifile",
        "raw_text": "Wire staging: check_prism_meta_channel_staging_readiness_v1.py + signoff JSON. Constraints: B-track only, rollback unset env. Files: experiments/no_guard_limit_test/prism_meta_channel_staging_checklist_v1.json. Verify: py -m pytest tests/test_check_prism_meta_channel_staging_readiness_v1.py -q",
    },
    {
        "id": "cc_n29",
        "lane": "user_query_short",
        "raw_text": "archive trilogy Lane B dynamic_unique_sets?",
    },
    {
        "id": "cc_n30",
        "lane": "code_context",
        "raw_text": "class MetaSidecar(BaseModel):\n    pinset: dict[str, Any]\n    meta_channel_block: str\n    injection_mode: Literal['meta_channel_post_gatekeeper']\n\nExpose effective_context_tokens = raw_tokens + meta_channel_tokens.",
    },
    {
        "id": "cc_n31",
        "lane": "stack_trace",
        "raw_text": "KeyError: 'dynamic_advantage_proven'\n  build_archive_limitless_trilogy_report_v1.py:99\n  b2_agg referenced before assignment — reorder phase2 load.",
    },
    {
        "id": "cc_n32",
        "lane": "agent_rules_excerpt",
        "raw_text": "Fact-Lock: CONSTITUTION + exit code only. Compression Track A 47.5% frozen — FAIL-COMP-004. Sandbox limitless trilogy is [HYPO] research_only.",
    },
    {
        "id": "cc_n33",
        "lane": "code_context",
        "raw_text": "def enrich_with_meta_sidecar(result, text, *, lane=None):\n    if not meta_channel_enabled():\n        result['meta_channel'] = None\n        return result\n    sidecar = build_meta_sidecar(text, task_profile='py_coding_dynamic')\n    result['meta_channel'] = sidecar\n    return result",
    },
    {
        "id": "cc_n34",
        "lane": "long_multifile",
        "raw_text": "n40 bench: compare fixed vs dynamic on 40 cases. Output prism_dynamic_pinset_bench_n40_v1_latest.json. No MISSION_LOG. No active report edit. pytest smoke after bench.",
    },
    {
        "id": "cc_n35",
        "lane": "stack_trace",
        "raw_text": "RecursionError: maximum recursion depth\n  coding_proxy_compress_with_meta → coding_proxy_compress_surface → enrich_with_meta_sidecar\n  Guard: skip double attach when meta_channel already set.",
    },
    {
        "id": "cc_n36",
        "lane": "code_context",
        "raw_text": "for case in load_cases(input_path):\n    off = coding_proxy_compress_surface(raw, profile, lane=lane)\n    os.environ['MKM_PRISM_META_CHANNEL_BTRACK']='1'\n    on = coding_proxy_compress_surface(raw, profile, lane=lane)\n    assert off['reconstruction_fidelity_jaccard'] == on['reconstruction_fidelity_jaccard']",
    },
    {
        "id": "cc_n37",
        "lane": "user_query_short",
        "raw_text": "staging_enable_ok false — where is signoff JSON?",
    },
    {
        "id": "cc_n38",
        "lane": "agent_rules_excerpt",
        "raw_text": "Logos lens [NON_GATING]. Field → Lens → Conflict → Final Action. Regime_map primary; biblical_regime_matrix report-only.",
    },
    {
        "id": "cc_n39",
        "lane": "code_context",
        "raw_text": "HEAVY_LANES = frozenset({'stack_trace','code_context','agent_rules_excerpt','long_multifile'})\n\ndef filter_cases(cases, *, lanes=None):\n    return [c for c in cases if c.get('lane') in lanes]",
    },
    {
        "id": "cc_n40",
        "lane": "stack_trace",
        "raw_text": "AssertionError: wire_poc_pass is False\n  run_prism_proxy_meta_wire_bench_v1.py\n  cc_n17 long_multifile Jaccard 0.48 under no-guard — guarded path must preserve baseline with meta flag.",
    },
]


def build_n40(*, n20_path: Path, out_path: Path) -> dict[str, int]:
    lines: list[str] = []
    for line in n20_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            lines.append(line.strip())
    for row in EXTRA_ROWS:
        lines.append(json.dumps(row, ensure_ascii=False))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"n20_rows": len(lines) - len(EXTRA_ROWS), "extra_rows": len(EXTRA_ROWS), "total": len(lines)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build n40 coding compress bench JSONL.")
    ap.add_argument("--n20", default=str(N20))
    ap.add_argument("--out-jsonl", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    n20 = Path(args.n20)
    if not n20.is_absolute():
        n20 = ROOT / n20
    out = Path(args.out_jsonl)
    if not out.is_absolute():
        out = ROOT / out
    stats = build_n40(n20_path=n20, out_path=out)
    print(str(out))
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
