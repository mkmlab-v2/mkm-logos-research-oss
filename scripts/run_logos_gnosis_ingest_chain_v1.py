#!/usr/bin/env python3
"""Gnosis KG ingest → graph bridge refresh → subgraph router → manifest [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_gnosis_ingest_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gnosis-dir", type=Path, default=None)
    ap.add_argument(
        "--use-fixture-sample",
        action="store_true",
        help="Offline fixture ingest (default when --gnosis-dir omitted)",
    )
    ap.add_argument("--ack-license-cc-by-sa-4", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    use_fixture = args.use_fixture_sample or args.gnosis_dir is None
    ingest_cmd = [PY, "scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py"]
    if use_fixture:
        ingest_cmd.append("--use-fixture-sample")
    else:
        ingest_cmd.extend(["--gnosis-dir", str(args.gnosis_dir)])
        if not args.ack_license_cc_by_sa_4:
            raise SystemExit("real gnosis ingest requires --ack-license-cc-by-sa-4")
        ingest_cmd.append("--ack-license-cc-by-sa-4")

    steps: list[dict] = []
    for row in (
        _run("gnosis_ingest", ingest_cmd),
        _run("cosmic_anchor_graph_bridge", [PY, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"]),
        _run("subgraph_graphrag_router", [PY, "scripts/run_logos_subgraph_graphrag_router_v1.py"]),
        _run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]),
    ):
        steps.append(row)
        if not row["ok"]:
            break

    if steps[-1]["ok"] and not args.skip_pytest:
        steps.append(
            _run(
                "pytest_gnosis_ingest",
                [PY, "-m", "pytest", "tests/test_ingest_logos_gnosis_kg_lemma_edges_v1.py", "-q", "--tb=short"],
            )
        )

    report = {
        "schema": "logos_gnosis_ingest_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "use_fixture_sample": use_fixture,
        "steps": steps,
        "all_ok": all(s.get("ok") for s in steps),
        "reproduce": "py scripts/run_logos_gnosis_ingest_chain_v1.py --use-fixture-sample",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["all_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
