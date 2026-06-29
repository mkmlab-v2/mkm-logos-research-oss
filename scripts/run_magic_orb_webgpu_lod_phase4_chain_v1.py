#!/usr/bin/env python3
"""Phase 4 [HYPO]: WebGPU LOD policy + hero slice tier smoke + pytest."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/magic_orb_webgpu_lod_phase4_chain_v1_latest.json"
POLICY = ROOT / "docs/final/artifacts/magic_orb_webgpu_lod_policy_v1_latest.json"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
BUILD = ROOT / "scripts/build_magic_orb_webgpu_lod_policy_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    report: dict = {
        "schema": "magic_orb_webgpu_lod_phase4_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "steps": [],
        "ok": False,
    }

    def run_step(name: str, cmd: list[str]) -> bool:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        report["steps"].append(
            {
                "name": name,
                "cmd": " ".join(cmd),
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip()[:2000],
                "stderr": proc.stderr.strip()[:500],
            }
        )
        return proc.returncode == 0

    ok = run_step(
        "build_policy",
        [sys.executable, str(BUILD), "--sync-mkmlife"],
    )
    ok = run_step(
        "pytest_lod",
        [sys.executable, "-m", "pytest", "tests/test_magic_orb_webgpu_lod_phase4_v1.py", "-q"],
    ) and ok

    if POLICY.is_file():
        policy = json.loads(POLICY.read_text(encoding="utf-8-sig"))
        report["tier_count"] = len(policy.get("tiers") or [])
        report["has_webgpu_hypo_tier"] = any(
            t.get("tier") == "webgpu_hypo" for t in policy.get("tiers") or []
        )

    if HERO.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location("lod_policy", BUILD)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        resolve_tier = mod.resolve_tier

        bundle = json.loads(HERO.read_text(encoding="utf-8-sig"))
        slice_tiers = []
        for sl in bundle.get("slices") or []:
            bloom = sl.get("graph_bloom") or {}
            n = len(bloom.get("nodes") or [])
            slice_tiers.append(
                {
                    "slice_id": sl.get("slice_id"),
                    "nodes": n,
                    "resolved_tier": resolve_tier(n),
                    "resolved_tier_webgpu": resolve_tier(n, webgpu_available=True),
                }
            )
        report["hero_slice_lod"] = slice_tiers
        ok = ok and all(row["resolved_tier"] for row in slice_tiers)

    report["ok"] = ok
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "tiers": report.get("tier_count")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
