#!/usr/bin/env python3
"""Universal Root OSS Cursor smoke — fixture-only, no HF/Ollama required [HYPO].

Reproduce for external clones:
  py scripts/run_universal_root_oss_cursor_smoke_v1.py
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
OUT = ROOT / "reports/universal_root_oss_cursor_smoke_v1_latest.json"


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
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:],
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
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-path-audit", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_path_audit:
        steps.append(
            _run(
                "launch_gate_1_path_audit",
                [PY, "scripts/check_hardcoded_workspace_paths_v1.py", "--scope", "oss", "--strict"],
            )
        )
    steps.append(_run("topology_crosswalk_build", [PY, "scripts/build_universal_root_topology_crosswalk_v1.py"]))
    steps.append(_run("topology_crosswalk_gate", [PY, "scripts/check_universal_root_topology_crosswalk_v1.py"]))
    steps.append(_run("wall_divergence_cards", [PY, "scripts/build_universal_root_wall_divergence_exception_cards_v1.py"]))

    if not args.skip_gate_spec:
        steps.append(
            _run(
                "gate_spec_check",
                [PY, "scripts/check_universal_root_gate_spec_v1.py"],
                optional=True,
            )
        )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_topology_crosswalk",
                [PY, "-m", "pytest", "tests/test_universal_root_topology_crosswalk_v1.py", "-q", "--tb=short"],
            )
        )
        steps.append(
            _run(
                "pytest_wall_divergence_cards",
                [PY, "-m", "pytest", "tests/test_universal_root_wall_divergence_exception_cards_v1.py", "-q", "--tb=short"],
            )
        )

    topo = _read_json(ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json")
    wall = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json")
    summary = topo.get("summary") or {}
    lexicon = topo.get("lexicon_plane") or {}
    topology = topo.get("topology_plane") or {}

    all_ok = all(s.get("ok") for s in steps)
    doc = {
        "schema": "universal_root_oss_cursor_smoke_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "requires_hf_gate": False,
        "requires_ollama": False,
        "all_ok": all_ok,
        "ok": all_ok,
        "metrics": {
            "raw_lexicon_prime_hit_rate": lexicon.get("prime_hit_rate"),
            "raw_lexicon_english_only_distortion_rate": lexicon.get("english_only_distortion_rate"),
            "topology_verse_reachable_rate": summary.get("verse_reachable_rate"),
            "wall_exception_count": wall.get("summary", {}).get("exception_count"),
            "delta_topology_minus_lexicon": (topo.get("delta_topology_minus_lexicon") or {}).get(
                "verse_reachable_minus_prime_hit_rate"
            ),
        },
        "steps": steps,
        "reproduce": "py scripts/run_universal_root_oss_cursor_smoke_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "metrics": doc["metrics"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
