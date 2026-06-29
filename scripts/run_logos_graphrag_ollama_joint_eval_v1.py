#!/usr/bin/env python3
"""Joint eval: live Ollama shallow router + 309k lemma + Sinew xref subgraph [HYPO]."""

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
DEFAULT_OUT = ROOT / "reports/logos_graphrag_ollama_joint_eval_v1_latest.json"
DEFAULT_QUERY = "성경 구절에서 반도체·유리 정제 은유와 연결된 lemma 경로는?"
LEMMA_JSONL = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
SINEW_JSONL = ROOT / "docs/final/artifacts/logos_sinew_xref_edges_v1.jsonl"
OSI_JSONL = ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl"
THEOGRAPHIC_JSONL = ROOT / "docs/final/artifacts/logos_theographic_entity_edges_v1.jsonl"
GEMATRIA_LEXICON_JSONL = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"
ROUTER_OUT = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _run(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--model", default="mkm-shallow-router-v1")
    ap.add_argument("--ollama-timeout-sec", type=int, default=180)
    ap.add_argument("--optional-ollama", action="store_true")
    ap.add_argument("--min-lemma-lines", type=int, default=100000)
    ap.add_argument("--min-sinew-lines", type=int, default=1000)
    ap.add_argument("--min-osi-lines", type=int, default=1000)
    ap.add_argument("--min-theographic-lines", type=int, default=1000)
    ap.add_argument("--min-gematria-lexicon-lines", type=int, default=0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lemma_lines = _count_jsonl_lines(LEMMA_JSONL)
    sinew_lines = _count_jsonl_lines(SINEW_JSONL)
    osi_lines = _count_jsonl_lines(OSI_JSONL)
    theographic_lines = _count_jsonl_lines(THEOGRAPHIC_JSONL)
    gematria_lexicon_lines = _count_jsonl_lines(GEMATRIA_LEXICON_JSONL)
    corpus_ok = (
        lemma_lines >= args.min_lemma_lines
        and sinew_lines >= args.min_sinew_lines
        and osi_lines >= args.min_osi_lines
        and theographic_lines >= args.min_theographic_lines
        and gematria_lexicon_lines >= args.min_gematria_lexicon_lines
    )

    steps: dict[str, Any] = {
        "corpus_snapshot": {
            "lemma_jsonl_lines": lemma_lines,
            "sinew_xref_jsonl_lines": sinew_lines,
            "osi_xref_jsonl_lines": osi_lines,
            "theographic_entity_jsonl_lines": theographic_lines,
            "scriptures_js_gematria_lexicon_jsonl_lines": gematria_lexicon_lines,
            "gematria_lexicon_sidecar_present": gematria_lexicon_lines > 0,
            "corpus_ok": corpus_ok,
        }
    }

    router_cmd = [
        PY,
        "scripts/run_logos_subgraph_graphrag_router_v1.py",
        "--query",
        args.query,
        "--lemma-jsonl",
        str(LEMMA_JSONL),
        "--sinew-xref-jsonl",
        str(SINEW_JSONL),
        "--osi-xref-jsonl",
        str(OSI_JSONL),
        "--theographic-entity-jsonl",
        str(THEOGRAPHIC_JSONL),
        "--gematria-lexicon-jsonl",
        str(GEMATRIA_LEXICON_JSONL),
        "--output-json",
        str(ROUTER_OUT),
    ]
    router_rc, router_tail = _run(router_cmd, timeout=300)
    steps["subgraph_router_joint"] = {"ok": router_rc == 0, "exit_code": router_rc, "tail": router_tail[-500:]}

    router_doc: dict[str, Any] = {}
    if ROUTER_OUT.is_file():
        router_doc = _read_json(ROUTER_OUT)

    shallow_cmd = [
        PY,
        "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py",
        "--run-ollama",
        "--query",
        args.query,
        "--expected-domain",
        "logos",
        "--model",
        args.model,
        "--ollama-timeout-sec",
        str(args.ollama_timeout_sec),
        "--include-deep-chain-dry-run",
        "--query-id",
        "logos_graphrag_ollama_joint_eval",
    ]
    shallow_rc, shallow_tail = _run(shallow_cmd, timeout=args.ollama_timeout_sec + 60)
    steps["ollama_shallow_e2e"] = {"ok": shallow_rc == 0, "exit_code": shallow_rc, "tail": shallow_tail[-600:]}

    shallow_domain = None
    e2e_path = ROOT / "reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json"
    if e2e_path.is_file():
        shallow_domain = _read_json(e2e_path).get("shallow_domain_tag")

    router_summary = router_doc.get("summary") or {}
    joint_ok = corpus_ok and steps["subgraph_router_joint"]["ok"] and steps["ollama_shallow_e2e"]["ok"]
    if not steps["ollama_shallow_e2e"]["ok"] and args.optional_ollama:
        joint_ok = corpus_ok and steps["subgraph_router_joint"]["ok"]

    report = {
        "schema": "logos_graphrag_ollama_joint_eval_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "query": args.query,
        "model": args.model,
        "steps": steps,
        "shallow_domain_tag": shallow_domain,
        "router_summary": router_summary,
        "lemma_edge_hits": int(router_summary.get("lemma_edge_hits") or 0),
        "sinew_xref_hits": int(router_summary.get("sinew_xref_hits") or 0),
        "osi_xref_hits": int(router_summary.get("osi_xref_hits") or 0),
        "theographic_entity_hits": int(router_summary.get("theographic_entity_hits") or 0),
        "gematria_lexicon_hits": int(router_summary.get("gematria_lexicon_hits") or 0),
        "joint_ok": joint_ok,
        "reproduce": (
            "py scripts/run_logos_graphrag_ollama_joint_eval_v1.py "
            f'--query "{args.query}"'
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": joint_ok,
                "corpus_ok": corpus_ok,
                "lemma_lines": lemma_lines,
                "sinew_lines": sinew_lines,
                "osi_lines": osi_lines,
                "theographic_lines": theographic_lines,
                "gematria_lexicon_lines": gematria_lexicon_lines,
                "gematria_lexicon_hits": int(router_summary.get("gematria_lexicon_hits") or 0),
                "shallow_domain": shallow_domain,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    if not joint_ok and not args.optional_ollama:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
