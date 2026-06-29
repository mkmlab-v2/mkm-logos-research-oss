#!/usr/bin/env python3
"""Phase 11-J: themed_dan aramaic bridge signoff + gold q23/q47 verify [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
THEMED_DAN = ROOT / "docs/final/artifacts/logos_concept_bridge_themed_dan_aramaic_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
GOLD_EVAL = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11j_themed_dan_signoff_chain_v1_latest.json"
GOLD_IDS = ("q23", "q47")


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


def _themed_dan_policy() -> dict:
    doc = _read_json(THEMED_DAN)
    policy = doc.get("policy") if isinstance(doc.get("policy"), dict) else {}
    return policy


def _gold_rows_by_id(gold_doc: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in gold_doc.get("rows") or []:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            out[row["id"]] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-signoff", action="store_true")
    ap.add_argument("--skip-gold-eval", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-sweep-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_signoff:
        steps.append(
            _run(
                "themed_dan_commander_signoff",
                [
                    PY,
                    "scripts/mark_logos_concept_bridge_human_signoff_v1.py",
                    "--commander-direct-signoff",
                    "--signoff-by",
                    "commander",
                ],
            )
        )

    steps.append(_run("concept_bridge_registry", [PY, "scripts/build_logos_concept_bridge_registry_v1.py"]))

    policy = _themed_dan_policy()
    signoff_ok = bool(policy.get("human_signoff_completed") and policy.get("human_reviewed"))

    if not args.skip_gold_eval:
        steps.append(_run("subgraph_gold_eval", [PY, "scripts/run_logos_subgraph_gold_eval_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_sweep_refresh:
        steps.append(
            _run(
                "phase14_sweep_report",
                [PY, "scripts/build_logos_phase14_full_sweep_report_v1.py"],
                optional=True,
            )
        )

    reg_doc = _read_json(REGISTRY)
    gold_doc = _read_json(GOLD_EVAL)
    gold_rows = _gold_rows_by_id(gold_doc)
    gold_pass: dict[str, bool] = {}
    for qid in GOLD_IDS:
        row = gold_rows.get(qid) or {}
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        raw = metrics.get("raw") if isinstance(metrics.get("raw"), dict) else {}
        hit = raw.get("hit_at_k") if isinstance(raw.get("hit_at_k"), dict) else {}
        gold_pass[qid] = bool(hit.get("1"))

    themed_entry = next(
        (
            e
            for e in reg_doc.get("entries") or []
            if isinstance(e, dict) and e.get("concept_id") == "concept:themed_dan_aramaic"
        ),
        {},
    )

    all_ok = (
        all(s.get("ok") for s in steps)
        and signoff_ok
        and themed_entry.get("human_reviewed") is True
        and all(gold_pass.get(qid) for qid in GOLD_IDS)
    )

    report = {
        "schema": "logos_graphrag_phase11j_themed_dan_signoff_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "bridge_artifact": str(THEMED_DAN.relative_to(ROOT)).replace("\\", "/"),
        "concept_id": "concept:themed_dan_aramaic",
        "human_signoff_completed": policy.get("human_signoff_completed"),
        "human_signoff_utc": policy.get("human_signoff_utc"),
        "signoff_lane": policy.get("signoff_lane"),
        "registry_human_reviewed_ratio": reg_doc.get("human_reviewed_ratio"),
        "themed_dan_registry_human_reviewed": themed_entry.get("human_reviewed"),
        "gold_query_ids": list(GOLD_IDS),
        "gold_hit_at_1_pass": gold_pass,
        "gold_summary_hit_at_k_rates": (gold_doc.get("summary") or {}).get("hit_at_k_rates"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11j_themed_dan_signoff_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "signoff_ok": signoff_ok,
                "gold_pass": gold_pass,
                "human_reviewed_ratio": reg_doc.get("human_reviewed_ratio"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
