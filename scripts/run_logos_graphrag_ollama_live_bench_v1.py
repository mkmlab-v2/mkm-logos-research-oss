#!/usr/bin/env python3
"""Live Ollama shallow router + Logos subgraph router joint bench [HYPO]."""

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
DEFAULT_OUT = ROOT / "reports/logos_graphrag_ollama_live_bench_v1_latest.json"
DEFAULT_QUERY = "성경 구절에서 반도체·유리 정제 은유와 연결된 lemma 경로는?"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, check=False)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--model", default="mkm-shallow-router-v1")
    ap.add_argument("--ollama-timeout-sec", type=int, default=180)
    ap.add_argument("--optional-ollama", action="store_true", help="Exit 0 if Ollama unavailable")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: dict[str, Any] = {}

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
        "logos_graphrag_ollama_live",
    ]
    rc, tail = _run(shallow_cmd, timeout=args.ollama_timeout_sec + 60)
    steps["ollama_shallow_e2e"] = {"ok": rc == 0, "exit_code": rc, "tail": tail[-600:]}

    router_rc, router_tail = _run([PY, "scripts/run_logos_subgraph_graphrag_router_v1.py"], timeout=120)
    steps["subgraph_router"] = {"ok": router_rc == 0, "exit_code": router_rc, "tail": router_tail[-400:]}

    router_doc: dict[str, Any] = {}
    router_path = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
    if router_path.is_file():
        router_doc = _read_json(router_path)

    shallow_domain = None
    e2e_path = ROOT / "reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json"
    if e2e_path.is_file():
        shallow_domain = _read_json(e2e_path).get("shallow_domain_tag")

    joint_ok = steps["ollama_shallow_e2e"]["ok"] and steps["subgraph_router"]["ok"]
    if not steps["ollama_shallow_e2e"]["ok"] and args.optional_ollama:
        joint_ok = steps["subgraph_router"]["ok"]

    report = {
        "schema": "logos_graphrag_ollama_live_bench_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "query": args.query,
        "model": args.model,
        "steps": steps,
        "shallow_domain_tag": shallow_domain,
        "router_paths": int((router_doc.get("summary") or {}).get("paths") or 0),
        "joint_ok": joint_ok,
        "reproduce": f"py scripts/run_logos_graphrag_ollama_live_bench_v1.py --query \"{args.query}\"",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": joint_ok, "shallow_domain": shallow_domain, "out": str(args.out)}, ensure_ascii=False))
    if not joint_ok and not args.optional_ollama:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
