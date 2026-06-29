#!/usr/bin/env python3
"""Token/char proxy bench — myeongni+sasang GraphRAG sidebar vs full-corpus proxy [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_lens_ablation_graphrag_sidebar_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_ROUTER,
    DEFAULT_SASANG_ROUTER,
    build_graphrag_sidebar_pack,
)
from scripts.build_sasang_corpus_graphrag_sidebar_pool_v1 import (  # noqa: E402
    DEFAULT_BUNDLE,
    DEFAULT_ROUTER as DEFAULT_SASANG_POOL_ROUTER,
    build_pool,
)

DEFAULT_OUT = ROOT / "reports/myeongni_sasang_graphrag_token_proxy_bench_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/myeongni_sasang_graphrag_token_proxy_bench_v1_latest.json"
LOGOS_WIRE_REF = ROOT / "reports/constitution/btrack_pilot/mkm_graph_wire_rag_poc_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pool_chars(pool: dict[str, Any]) -> int:
    n = 0
    pools = pool.get("candidate_pools") or {}
    for entries in pools.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict):
                n += len(str(e.get("summary") or ""))
                n += sum(len(str(s)) for s in (e.get("steps") or []))
    return n


def build_bench(
    *,
    myeongni_router: Path,
    sasang_router: Path,
    bundle: Path,
) -> dict[str, Any]:
    sidebar = build_graphrag_sidebar_pack(
        myeongni_router=myeongni_router,
        sasang_router=sasang_router,
        enabled=True,
    )
    bundle_doc = _read(bundle)
    sasang_pool = build_pool(bundle=bundle_doc or {}, router=_read(sasang_router))
    sidebar_chars = int((sidebar.get("token_budget_proxy") or {}).get("estimated_sidebar_chars") or 0)
    pool_chars = _pool_chars(sasang_pool)
    combined_sidebar = sidebar_chars + pool_chars
    full_proxy = int((sidebar.get("token_budget_proxy") or {}).get("estimated_full_corpus_chars_proxy") or 0)
    full_proxy += max(pool_chars * 4, 2400)
    savings = round(max(0.0, 1.0 - (combined_sidebar / full_proxy)), 4) if full_proxy else 0.0

    logos_ref = _read(LOGOS_WIRE_REF)
    logos_savings = None
    if logos_ref and isinstance(logos_ref.get("honest_metrics"), dict):
        logos_savings = logos_ref["honest_metrics"].get("payload_savings_ratio")

    return {
        "schema": "myeongni_sasang_graphrag_token_proxy_bench_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "prophecy_vote": "none",
        "myeongni_sasang_sidebar": sidebar,
        "sasang_pool_counts": sasang_pool.get("pool_counts"),
        "char_budget": {
            "myeongni_sasang_sidebar_chars": sidebar_chars,
            "sasang_pool_chars": pool_chars,
            "combined_sidebar_chars": combined_sidebar,
            "full_corpus_chars_proxy": full_proxy,
            "estimated_char_savings_ratio": savings,
            "reference_logos_wire_savings_ratio": logos_savings,
        },
        "verdict_ko": (
            f"명리+사상 sidebar char 절감 프록시 {savings:.1%} — 실측 토큰은 Ollama wire bench 별도"
        ),
        "reproduce": "py scripts/run_myeongni_sasang_graphrag_token_proxy_bench_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--myeongni-router", type=Path, default=DEFAULT_MYEONGNI_ROUTER)
    ap.add_argument("--sasang-router", type=Path, default=DEFAULT_SASANG_ROUTER)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_bench(
        myeongni_router=args.myeongni_router,
        sasang_router=args.sasang_router,
        bundle=args.bundle_json,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    ratio = (doc.get("char_budget") or {}).get("estimated_char_savings_ratio")
    print(json.dumps({"ok": True, "char_savings_ratio": ratio, "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
