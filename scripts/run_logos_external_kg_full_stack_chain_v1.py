#!/usr/bin/env python3
"""Full external KG stack: Sinew + OSI expand + Theographic + scriptures-js + Ollama joint eval [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_external_kg_full_stack_chain_v1_latest.json"


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
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-osi-download", action="store_true")
    ap.add_argument("--skip-sinew-download", action="store_true")
    ap.add_argument("--skip-theographic-download", action="store_true")
    ap.add_argument("--skip-scriptures-js-chain", action="store_true")
    ap.add_argument("--skip-scriptures-js-download", action="store_true")
    ap.add_argument("--optional-scriptures-js-chain", action="store_true")
    ap.add_argument("--skip-osi-expand", action="store_true")
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--optional-ollama", action="store_true")
    ap.add_argument("--skip-human-gate", action="store_true")
    ap.add_argument("--optional-human-gate", action="store_true")
    ap.add_argument(
        "--min-gematria-lexicon-lines",
        type=int,
        default=None,
        help="Forward to joint eval; default 1 when scriptures-js chain ran, else 0",
    )
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-gold-eval", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    sinew_cmd = [
        PY,
        "scripts/run_logos_sinew_xref_ingest_chain_v1.py",
        "--sinew-dir",
        "storage/external_kg/sinew_v1",
        "--ack-license-cc-by-4",
        "--skip-pytest",
    ]
    if args.skip_sinew_download:
        sinew_cmd.append("--skip-download")
    steps.append(_run("sinew_xref_chain", sinew_cmd))

    if not args.skip_osi_expand:
        steps.append(
            _run(
                "osi_xref_expand_coverage",
                [PY, "scripts/run_logos_osi_xref_expand_coverage_v1.py", "--ack-license-mit-pd"],
            )
        )

    theo_cmd = [
        PY,
        "scripts/run_logos_theographic_ingest_chain_v1.py",
        "--theographic-dir",
        "storage/external_kg/theographic_v1",
        "--ack-license-cc-by-sa-4",
        "--skip-pytest",
    ]
    if args.skip_theographic_download:
        theo_cmd.append("--skip-download")
    steps.append(_run("theographic_entity_chain", theo_cmd))

    scriptures_chain_ran = False
    if not args.skip_scriptures_js_chain:
        scriptures_cmd = [
            PY,
            "scripts/run_logos_scriptures_js_gematria_ingest_chain_v1.py",
            "--scriptures-js-dir",
            "storage/external_kg/scriptures_js_v1",
            "--ack-license-verify-upstream",
            "--skip-pytest",
        ]
        if args.skip_scriptures_js_download:
            scriptures_cmd.append("--skip-download")
        scriptures_step = _run(
            "scriptures_js_gematria_chain",
            scriptures_cmd,
            optional=args.optional_scriptures_js_chain,
        )
        steps.append(scriptures_step)
        scriptures_chain_ran = scriptures_step.get("ok", False)

    steps.append(_run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]))
    steps.append(_run("graphrag_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_human_gate:
        steps.append(
            _run(
                "concept_bridge_human_gate_chain",
                [PY, "scripts/run_logos_concept_bridge_human_gate_chain_v1.py"],
                optional=args.optional_human_gate,
            )
        )

    if not args.skip_ollama:
        min_gematria = args.min_gematria_lexicon_lines
        if min_gematria is None:
            min_gematria = 1 if scriptures_chain_ran else 0
        joint_cmd = [
            PY,
            "scripts/run_logos_graphrag_ollama_joint_eval_v1.py",
            "--min-gematria-lexicon-lines",
            str(min_gematria),
        ]
        if args.optional_ollama:
            joint_cmd.append("--optional-ollama")
        steps.append(_run("ollama_joint_eval", joint_cmd, optional=args.optional_ollama))

    if not args.skip_gold_eval:
        gold_eval_cmd = [
            PY,
            "scripts/run_logos_subgraph_gold_eval_chain_v1.py",
            "--skip-pytest",
        ]
        steps.append(_run("subgraph_gold_eval_chain", gold_eval_cmd, optional=True))
        steps.append(_run("graphrag_evidence_pack_refresh", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_pytest:
        pytest_targets = [
            "tests/test_ingest_logos_sinew_xref_edges_v1.py",
            "tests/test_ingest_logos_osi_xref_edges_v1.py",
            "tests/test_ingest_logos_theographic_entity_edges_v1.py",
            "tests/test_build_logos_external_kg_ingest_manifest_v1.py",
            "tests/test_build_logos_concept_bridge_human_gate_queue_v1.py",
            "tests/test_run_logos_subgraph_gold_eval_v1.py",
        ]
        scriptures_pytest = ROOT / "tests/test_ingest_logos_scriptures_js_gematria_lexicon_v1.py"
        if scriptures_pytest.is_file():
            pytest_targets.insert(3, str(scriptures_pytest.relative_to(ROOT)).replace("\\", "/"))
        steps.append(
            _run(
                "pytest_external_kg_smoke",
                [PY, "-m", "pytest", *pytest_targets, "-q", "--tb=short"],
            )
        )

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_external_kg_full_stack_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "all_ok": all_ok,
        "steps": steps,
        "reproduce": (
            "py scripts/run_logos_external_kg_full_stack_chain_v1.py "
            "--skip-osi-download --skip-sinew-download --skip-theographic-download "
            "--skip-scriptures-js-download --optional-ollama"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out), "steps": len(steps)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
