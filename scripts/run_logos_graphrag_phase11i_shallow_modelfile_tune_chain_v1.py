#!/usr/bin/env python3
"""Phase 11-I: Modelfile v1.3 adversarial tune + ollama recreate + live stress 32 [HYPO]."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
MODELFILE = ROOT / "docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt"
DEFAULT_MODEL = "mkm-shallow-router-v1"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1_latest.json"
TARGET_FIXTURES = (
    "adv_myeongni_sasang_trap",
    "adv_oracle_advanced_logos",
)


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


def _modelfile_version() -> str | None:
    if not MODELFILE.is_file():
        return None
    head = MODELFILE.read_text(encoding="utf-8").splitlines()[:1]
    m = re.search(r"v(\d+\.\d+)", head[0] if head else "")
    return m.group(0) if m else None


def _target_fixture_hits(bench_doc: dict) -> dict[str, bool]:
    hits: dict[str, bool] = {}
    for row in bench_doc.get("rows") or []:
        fid = row.get("fixture_id")
        if fid in TARGET_FIXTURES:
            hits[fid] = bool(row.get("router_hit"))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    modelfile_version = _modelfile_version()

    if not args.skip_ollama:
        steps.append(
            _run(
                "ollama_create_shallow_router",
                ["ollama", "create", DEFAULT_MODEL, "-f", str(MODELFILE)],
            )
        )

    stress_cmd = [PY, "scripts/run_logos_shallow_oracle_gap_stress_chain_v1.py", "--max-oracle-gap", "0.25"]
    if args.skip_ollama:
        stress_cmd.append("--skip-ollama")
    steps.append(_run("shallow_oracle_gap_stress_32", stress_cmd, optional=args.skip_ollama))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    gap_doc = _read_json(ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json")
    gap_raw = gap_doc.get("raw") if isinstance(gap_doc.get("raw"), dict) else {}
    bench_doc = _read_json(ROOT / "reports/ollama_shallow_router_bench_stress_v1_latest.json")
    target_hits = _target_fixture_hits(bench_doc)
    target_all_hit = all(target_hits.get(fid) for fid in TARGET_FIXTURES if fid in target_hits)

    all_ok = all(s.get("ok") for s in steps) and (args.skip_ollama or target_all_hit)
    report = {
        "schema": "logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "live_ollama": not args.skip_ollama,
        "modelfile": str(MODELFILE.relative_to(ROOT)).replace("\\", "/"),
        "modelfile_version": modelfile_version,
        "model": DEFAULT_MODEL,
        "target_fixtures": list(TARGET_FIXTURES),
        "target_fixture_hits": target_hits,
        "target_all_hit": target_all_hit,
        "router_hit_rate": gap_raw.get("router_hit_rate"),
        "routing_oracle_gap": gap_raw.get("routing_oracle_gap"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "modelfile_version": modelfile_version,
                "target_all_hit": target_all_hit,
                "router_hit_rate": gap_raw.get("router_hit_rate"),
                "routing_oracle_gap": gap_raw.get("routing_oracle_gap"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
