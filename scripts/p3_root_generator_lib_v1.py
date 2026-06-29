#!/usr/bin/env python3
"""Shared helpers for P3 Root Generator bench/build (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARDS_ROOT = ROOT / "codebook" / "shards"
ROUTER_PROBE = ROOT / "tests/fixtures/p3_root_router_probe_v1.json"
SHALLOW_SLICE = ROOT / "tests/fixtures/p3_shallow_router_golden_slice_v1.json"
SHALLOW_BENCH = ROOT / "scripts/run_ollama_shallow_router_bench_v1.py"


def router_probe_metrics(lexicon_path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    from scripts.core.domain_router import DomainSpecificRouter
    from scripts.core.master_codebook_lexicon_v1_bridge import lexicon_hits_for_text, unicode_word_tokens

    router = DomainSpecificRouter(SHARDS_ROOT)
    rows = []
    domain_hits = 0
    total_tokens = 0
    lexicon_token_hits = 0

    for probe in fixture.get("probes") or []:
        text = str(probe.get("input") or "")
        expected = str(probe.get("expected_shard_domain") or "")
        route = router.route(text)
        domain_ok = route.domain == expected
        if domain_ok:
            domain_hits += 1
        toks = unicode_word_tokens(text)
        hits, _ = lexicon_hits_for_text(text, lexicon_path)
        n_tok = len(toks)
        n_hit = len(hits)
        total_tokens += n_tok
        lexicon_token_hits += n_hit
        rows.append(
            {
                "id": probe.get("id"),
                "expected_shard_domain": expected,
                "routed_domain": route.domain,
                "routed_shard_id": route.shard_id,
                "domain_router_hit": domain_ok,
                "token_count": n_tok,
                "lexicon_hit_count": n_hit,
                "lexicon_hit_ratio": round(n_hit / n_tok, 4) if n_tok else 0.0,
            }
        )

    n = len(rows)
    return {
        "probe_count": n,
        "domain_router_hit_rate": round(domain_hits / n, 4) if n else 0.0,
        "lexicon_token_hit_rate": round(lexicon_token_hits / total_tokens, 4) if total_tokens else 0.0,
        "rows": rows,
    }


def shallow_router_slice(*, skip_ollama: bool = True, out_json: Path | None = None) -> dict[str, Any]:
    out = out_json or (ROOT / "reports/p3_root_shallow_router_slice_v1_latest.json")
    cmd = [
        sys.executable,
        str(SHALLOW_BENCH),
        "--fixtures",
        str(SHALLOW_SLICE),
        "--out-json",
        str(out),
    ]
    if skip_ollama:
        cmd.append("--skip-ollama")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if not out.is_file():
        return {
            "status": "error",
            "exit_code": proc.returncode,
            "stderr": (proc.stderr or "")[:500],
            "router_hit_rate": None,
            "skipped": True,
        }
    doc = json.loads(out.read_text(encoding="utf-8"))
    raw = doc.get("raw") or doc.get("metrics") or {}
    skipped = bool(doc.get("skip_reason") or doc.get("error") or doc.get("mode") in {"skipped", "unreachable"})
    return {
        "status": doc.get("mode") or ("ok" if proc.returncode == 0 else "error"),
        "exit_code": proc.returncode,
        "router_hit_rate": raw.get("router_hit_rate"),
        "parse_ok_rate": raw.get("parse_ok_rate"),
        "rows": raw.get("rows"),
        "report_path": str(out.relative_to(ROOT)).replace("\\", "/"),
        "skipped": skipped,
        "live_attempted": not skip_ollama,
    }
