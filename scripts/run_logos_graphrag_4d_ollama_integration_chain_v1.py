#!/usr/bin/env python3
"""One-click Logos GraphRAG + 4D + Ollama shallow integration chain [HYPO].

Serializes existing scripts only — no new theology logic.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_4d_ollama_integration_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lemma-target", type=int, default=60)
    ap.add_argument("--skip-lemma", action="store_true")
    ap.add_argument("--skip-ollama-e2e", action="store_true")
    ap.add_argument("--skip-gnosis-ingest", action="store_true")
    ap.add_argument("--run-ollama-live", action="store_true", help="Live Ollama + subgraph joint bench")
    ap.add_argument("--optional-ollama", action="store_true", help="Do not fail chain if Ollama unavailable")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    ps1 = ROOT / "scripts" / "Run-LogosOlGraphBridgeParallel_v1.ps1"
    steps.append(
        _run(
            "ol_graph_bridge_parallel",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
            ],
        )
    )

    if not args.skip_lemma:
        steps.append(
            _run(
                "lemma_60_chain",
                [PY, "scripts/run_logos_lemma_60_chain_v1.py", "--target", str(args.lemma_target)],
            )
        )

    steps.append(_run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]))

    if not args.skip_gnosis_ingest:
        steps.append(
            _run(
                "gnosis_fixture_ingest_chain",
                [PY, "scripts/run_logos_gnosis_ingest_chain_v1.py", "--use-fixture-sample", "--skip-pytest"],
            )
        )
        steps.append(_run("external_kg_manifest_post_gnosis", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]))

    steps.append(_run("graphrag_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_ollama_e2e:
        steps.append(
            _run(
                "ollama_shallow_semantic_rag_e2e",
                [
                    PY,
                    "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py",
                    "--include-deep-chain-dry-run",
                    "--query-id",
                    "logos_graphrag_4d_integration",
                ],
            )
        )

    if args.run_ollama_live:
        live_cmd = [PY, "scripts/run_logos_graphrag_ollama_live_bench_v1.py"]
        if args.optional_ollama:
            live_cmd.append("--optional-ollama")
        steps.append(_run("ollama_live_subgraph_bench", live_cmd, optional=args.optional_ollama))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_build_logos_external_kg_ingest_manifest_v1.py",
                    "tests/test_ingest_logos_gnosis_kg_lemma_edges_v1.py",
                    "tests/test_ollama_shallow_to_semantic_rag_e2e_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    report = {
        "schema": "logos_graphrag_4d_ollama_integration_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "steps": steps,
        "all_ok": all(s.get("ok") for s in steps),
        "reproduce": f"py scripts/run_logos_graphrag_4d_ollama_integration_chain_v1.py --lemma-target {args.lemma_target}",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["all_ok"], "out": str(args.out), "steps": len(steps)}, ensure_ascii=False))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
