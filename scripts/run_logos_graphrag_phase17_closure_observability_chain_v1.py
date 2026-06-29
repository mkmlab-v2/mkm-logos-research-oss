#!/usr/bin/env python3
"""Phase 17: closure & observability — bridge + memo + drift/readiness + evidence pack [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase17_closure_observability_chain_v1_latest.json"
PHASE16 = ROOT / "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json"
WALL_CARDS = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json"
BRIDGE_QUERY = (
    "Phase16 topology crosswalk closure: 41k lexicon plane prime_hit 99.53% vs "
    "31k verse-atom verse_reachable 99.53%; wall divergence heal/learn "
    "lexicon_only_without_topology — map Logos subgraph bridge paths without collapsing metric planes."
)
BRIDGE_QUERY_ID = "phase16_topology_crosswalk_bridge"


def _utc() -> str:
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
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-bridge", action="store_true")
    ap.add_argument("--skip-memo", action="store_true")
    ap.add_argument("--skip-observability", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    phase16 = _read_json(PHASE16)
    steps.append(
        {
            "label": "phase16_carry_snapshot",
            "cmd": ["read_only"],
            "exit_code": 0,
            "ok": bool(phase16.get("ok")),
            "tail": json.dumps(
                {
                    "phase16_ok": phase16.get("ok"),
                    "verse_reachable_rate": (phase16.get("topology_summary") or {}).get("verse_reachable_rate"),
                    "lexicon_only_without_topology": (phase16.get("wall_divergence") or {}).get(
                        "lexicon_only_without_topology"
                    ),
                },
                ensure_ascii=False,
            )[-500:],
        }
    )

    steps.append(_run("wall_divergence_exception_cards", [PY, "scripts/build_universal_root_wall_divergence_exception_cards_v1.py"]))

    if not args.skip_bridge:
        steps.append(
            _run(
                "semantic_rag_bridge",
                [
                    PY,
                    "scripts/run_question_semantic_rag_bridge_chain_v1.py",
                    "--query",
                    BRIDGE_QUERY,
                    "--query-id",
                    BRIDGE_QUERY_ID,
                    "--expand-graph",
                ],
            )
        )
    else:
        steps.append({"label": "semantic_rag_bridge", "cmd": ["skipped"], "exit_code": 0, "ok": True, "tail": "skip_bridge"})

    if not args.skip_memo:
        steps.append(
            _run(
                "fusion_inference_memo",
                [PY, "scripts/build_logos_job_heavenly_council_fusion_inference_memo_v1.py"],
                optional=True,
            )
        )
    else:
        steps.append({"label": "fusion_inference_memo", "cmd": ["skipped"], "exit_code": 0, "ok": True, "tail": "skip_memo"})

    if not args.skip_observability:
        steps.append(
            _run(
                "narrative_closure_observability",
                [
                    PY,
                    "scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
                    "--skip-vocology",
                ],
            )
        )
    else:
        steps.append(
            {
                "label": "narrative_closure_observability",
                "cmd": ["skipped"],
                "exit_code": 0,
                "ok": True,
                "tail": "skip_observability",
            }
        )

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))
    else:
        steps.append({"label": "build_evidence_pack", "cmd": ["skipped"], "exit_code": 0, "ok": True, "tail": "skip_evidence_pack"})

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_wall_divergence_cards",
                [PY, "-m", "pytest", "tests/test_universal_root_wall_divergence_exception_cards_v1.py", "-q", "--tb=short"],
                optional=True,
            )
        )

    wall_doc = _read_json(WALL_CARDS)
    obs_report = _read_json(ROOT / "reports/logos_oracle_narrative_closure_observability_chain_v1_latest.json")
    bridge_chain = _read_json(ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json")

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase17_closure_observability_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "implementation_status": "closure_observability_v1",
        "all_ok": all_ok,
        "ok": all_ok and bool(wall_doc.get("exceptions") is not None),
        "phase16_carry_ok": bool(phase16.get("ok")),
        "bridge_query_id": BRIDGE_QUERY_ID,
        "bridge_chain_ok": bridge_chain.get("ok"),
        "wall_exception_count": (wall_doc.get("summary") or {}).get("exception_count"),
        "wall_cards_pointer": "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json",
        "observability_chain_pass": obs_report.get("chain_pass"),
        "observations_pass": obs_report.get("observations_pass_count"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase17_closure_observability_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "wall_exception_count": report["wall_exception_count"],
                "observability_chain_pass": report["observability_chain_pass"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
