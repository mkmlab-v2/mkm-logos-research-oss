#!/usr/bin/env python3
"""Logos OSS premarket smoke — fixture-only, no KRV/Gnosis full corpus required.

Reproduce for external clones:
  py scripts/run_logos_oss_premarket_smoke_v1.py
  py scripts/run_logos_oss_premarket_smoke_v1.py --skip-secret-check
"""
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
OUT = ROOT / "reports/logos_oss_premarket_smoke_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/logos_oss_public_export_manifest_v1.json"
SOLO_POLICY = ROOT / "docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-secret-check", action="store_true")
    ap.add_argument("--skip-export-verify", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if SOLO_POLICY.is_file():
        policy = json.loads(SOLO_POLICY.read_text(encoding="utf-8-sig"))
        oss_open = (policy.get("send_gate_scope") or {}).get("oss_github_release") == "OPEN"
        steps.append({"label": "solo_oss_policy", "ok": oss_open, "oss_github_release": "OPEN" if oss_open else "other"})
        if not oss_open:
            raise SystemExit("solo OSS policy: oss_github_release not OPEN")

    if not args.skip_secret_check:
        steps.append(_run("secret_pattern_check", [PY, "scripts/check_mkm_secret_patterns_v1.py"], optional=True))

    steps.append(
        _run(
            "gnosis_fixture_ingest",
            [
                PY,
                "scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py",
                "--use-fixture-sample",
                "--min-edges",
                "3",
            ],
        )
    )
    steps.append(_run("conflict_sidecar_build", [PY, "scripts/build_bigset_studio_conflict_sidecar_v1.py"]))
    steps.append(_run("conflict_retrieval_gate", [PY, "scripts/check_logos_studio_conflict_retrieval_gate_v1.py"]))
    steps.append(_run("lemma_neighbor_index", [PY, "scripts/build_logos_studio_lemma_neighbor_index_v1.py"]))
    steps.append(_run("lemma_bridge_gate", [PY, "scripts/check_logos_studio_lemma_bridge_gate_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_synthesis",
                [PY, "-m", "pytest", "tests/test_logos_studio_dynamic_synthesis_v1.py", "-q", "--tb=short"],
            )
        )
        steps.append(
            _run(
                "pytest_lemma_bridge",
                [PY, "-m", "pytest", "tests/test_logos_studio_lemma_bridge_oss_v1.py", "-q", "--tb=short"],
            )
        )
        steps.append(
            _run(
                "pytest_verse_canonical",
                [PY, "-m", "pytest", "tests/test_logos_verse_ref_canonical_v1.py", "-q", "--tb=short"],
            )
        )
        if (ROOT / "tests/test_logos_oss_l5_bench_chain_v1.py").is_file():
            steps.append(
                _run(
                    "pytest_l5_bench_chain",
                    [PY, "-m", "pytest", "tests/test_logos_oss_l5_bench_chain_v1.py", "-q", "--tb=short"],
                    optional=True,
                )
            )

    if not args.skip_export_verify:
        steps.append(
            _run(
                "export_manifest_verify",
                [PY, "scripts/build_logos_oss_public_export_bundle_v1.py", "--verify-only"],
            )
        )

    l5_script = ROOT / "scripts/run_logos_oss_l5_bench_chain_v1.py"
    if l5_script.is_file():
        l5_cmd = [PY, "scripts/run_logos_oss_l5_bench_chain_v1.py"]
        if args.skip_pytest:
            l5_cmd.append("--skip-pytest")
        steps.append(_run("l5_bench_chain", l5_cmd, optional=True))

    failed = [s["label"] for s in steps if not s.get("ok") and not s.get("optional")]
    doc = {
        "schema": "logos_oss_premarket_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "release_gate": "OPEN_SOURCE_PREP",
        "send_gate_scope": {
            "oss_github_release": "OPEN",
            "grants_customer_contracts": "HOLD",
            "track_a_live_trading": "LOCKED",
        },
        "ok": not failed,
        "failed_steps": failed,
        "steps": steps,
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "guide": "docs/final/artifacts/logos_oss_premarket_smoke_guide_v1.md",
        "reproduce": "py scripts/run_logos_oss_premarket_smoke_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "failed": failed, "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
