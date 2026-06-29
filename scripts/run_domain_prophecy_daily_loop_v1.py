#!/usr/bin/env python3
"""Config-driven domain prophecy daily loop dispatcher [B-track · tier_0].

Routes by archetype from domain_prophecy_registry_v1:
  price_direction  -> run_kospi_daily_prophecy_evolution_loop_v1.py
  general_prophecy -> per-domain pack generate + Brier eval

research_only · send_gate HOLD
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
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
OUT = ROOT / "reports/domain_prophecy_daily_loop_v1_latest.json"
SAMPLE_IN = ROOT / "tests/fixtures/general_prophecy_registry_sample_v1.json"

sys.path.insert(0, str(ROOT))
from scripts.domain_prophecy_lib_v1 import (  # noqa: E402
    find_domain,
    load_domain_config,
    load_json,
    load_registry,
    pack_path_for_domain,
    rel,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:],
    }


def _dispatch_price(domain_id: str, config: dict[str, Any], phase: str, *, dry_run: bool) -> list[dict[str, Any]]:
    sched = config.get("scheduler") or {}
    loop = sched.get("daily_loop_script")
    if not loop:
        loop = "scripts/run_kospi_daily_prophecy_evolution_loop_v1.py" if domain_id == "kospi_direction" else (
            (config.get("eval") or {}).get("eval_script") or "scripts/run_kospi_daily_prophecy_evolution_loop_v1.py"
        )
    ym = sched.get("year_month") or datetime.now().strftime("%Y-%m")
    if "btc_direction" in domain_id or "run_btc_direction" in loop:
        cmd = [PY, str(loop).replace("/", "\\")]
        if phase == "evening":
            cmd.append("--allow-fetch")
    else:
        cmd = [PY, str(loop).replace("/", "\\"), "--phase", phase, "--year-month", str(ym), "--skip-heavy"]
    if dry_run:
        if "btc_direction" in domain_id or "run_btc_direction" in str(loop):
            cmd.append("--dry-run")
        return [{"name": f"{domain_id}_price_dry", "cmd": cmd, "exit_code": 0, "optional": False, "tail": "dry_run"}]
    return [_run(f"{domain_id}_price_loop", cmd)]


def _dispatch_ground_truth(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if phase not in ("evening", "weekend", "all"):
        return [{"name": f"{domain_id}_gt_skip", "cmd": [], "exit_code": 0, "optional": True, "tail": f"phase={phase}"}]
    eval_script = (config.get("eval") or {}).get("eval_script") or "scripts/run_weather_synthetic_120d_chain_and_brier_v1.py"
    cmd = [PY, str(eval_script).replace("/", "\\"), "--stub-only"]
    if dry_run:
        return [{"name": f"{domain_id}_gt_dry", "cmd": cmd, "exit_code": 0, "optional": False, "tail": "dry_run"}]
    return [_run(f"{domain_id}_ground_truth", cmd)]


def _dispatch_news_join(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if phase not in ("evening", "weekend", "all"):
        return [{"name": f"{domain_id}_news_skip", "cmd": [], "exit_code": 0, "optional": True, "tail": f"phase={phase}"}]
    smoke = (config.get("eval") or {}).get("eval_script") or "scripts/Run-NewsObservationContractSmoke.ps1"
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(smoke).replace("/", "\\")]
    if dry_run:
        return [{"name": f"{domain_id}_news_dry", "cmd": cmd, "exit_code": 0, "optional": False, "tail": "dry_run"}]
    return [_run(f"{domain_id}_news_join", cmd)]


def _dispatch_briefing_only(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    eval_script = (config.get("eval") or {}).get("eval_script") or "scripts/check_general_prophecy_logos_june_resolve_preflight_v1.py"
    cmd = [PY, str(eval_script).replace("/", "\\")]
    if dry_run:
        return [{"name": f"{domain_id}_briefing_dry", "cmd": cmd, "exit_code": 0, "optional": False, "tail": "dry_run"}]
    return [_run(f"{domain_id}_briefing_preflight", cmd, optional=True)]


def _dispatch_observation_only(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if phase not in ("evening", "weekend", "all"):
        return [{"name": f"{domain_id}_obs_skip", "cmd": [], "exit_code": 0, "optional": True, "tail": f"phase={phase}"}]
    eval_script = (config.get("eval") or {}).get("eval_script") or "scripts/validate_showroom_trust_slice_local_v1.py"
    cmd = [PY, str(eval_script).replace("/", "\\")]
    if dry_run:
        return [{"name": f"{domain_id}_obs_dry", "cmd": cmd, "exit_code": 0, "optional": False, "tail": "dry_run"}]
    return [_run(f"{domain_id}_observation_validate", cmd)]


def _dispatch_personalized_general(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if phase not in ("evening", "weekend", "all"):
        return [{"name": f"{domain_id}_pers_skip", "cmd": [], "exit_code": 0, "optional": True, "tail": f"phase={phase}"}]
    steps: list[dict[str, Any]] = []
    ingest_script = (config.get("ingest") or {}).get("ingest_chain_script")
    if ingest_script and str(ingest_script).endswith(".py"):
        ingest_cmd = [PY, str(ingest_script).replace("/", "\\")]
        if dry_run:
            steps.append(
                {"name": f"{domain_id}_ingest_gate_dry", "cmd": ingest_cmd, "exit_code": 0, "optional": True, "tail": "dry_run"}
            )
        else:
            steps.append(_run(f"{domain_id}_ingest_gate", ingest_cmd, optional=True))
    gp_config = dict(config)
    gp_eval = dict(gp_config.get("eval") or {})
    gp_eval["eval_script"] = "scripts/eval_general_prophecy_brier_score.py"
    gp_config["eval"] = gp_eval
    steps.extend(_dispatch_general(domain_id, gp_config, phase, dry_run=dry_run))
    gate_script = (config.get("eval") or {}).get("eval_script")
    brier_default = "scripts/eval_general_prophecy_brier_score.py"
    if gate_script and str(gate_script).endswith(".py") and str(gate_script) != brier_default:
        gate_cmd = [PY, str(gate_script).replace("/", "\\")]
        if dry_run:
            steps.append({"name": f"{domain_id}_adapter_gate_dry", "cmd": gate_cmd, "exit_code": 0, "optional": True, "tail": "dry_run"})
        else:
            steps.append(_run(f"{domain_id}_adapter_gate", gate_cmd, optional=True))
    return steps


def _dispatch_general(
    domain_id: str,
    config: dict[str, Any],
    phase: str,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if phase not in ("evening", "weekend", "all"):
        return [
            {
                "name": f"{domain_id}_gp_skip",
                "cmd": [],
                "exit_code": 0,
                "optional": True,
                "tail": f"general_prophecy noop for phase={phase}",
            }
        ]
    pack = pack_path_for_domain(domain_id)
    if not pack or not pack.is_file():
        legacy = config.get("legacy_pointers") or []
        for item in legacy:
            p = ROOT / str(item).replace("/", "\\")
            if p.is_file() and "domain_packs" in str(p):
                pack = p
                break
    if not pack or not pack.is_file():
        return [
            {
                "name": f"{domain_id}_gp_missing_pack",
                "cmd": [],
                "exit_code": 0 if dry_run else 1,
                "optional": dry_run,
                "tail": "no pack path; sample-only dry_run" if dry_run else "no pack path",
            }
        ]

    reg_out = ROOT / f"reports/{domain_id}_general_prophecy_registry_latest.json"
    brier_out = ROOT / f"reports/{domain_id}_general_prophecy_brier_latest.json"
    gen_cmd = [
        PY,
        "scripts/generate_general_prophecy_v1.py",
        "-i",
        str(SAMPLE_IN),
        "--merge-from",
        str(pack),
        "--no-default-merge",
        "--stub-forecasts",
        "-o",
        str(reg_out),
    ]
    eval_script = (config.get("eval") or {}).get("eval_script") or "scripts/eval_general_prophecy_brier_score.py"
    brier_cmd = [PY, str(eval_script).replace("/", "\\"), "--input", str(reg_out), "--output", str(brier_out)]

    ingest = config.get("ingest") or {}
    premarket = ingest.get("premarket_config_path")
    steps: list[dict[str, Any]] = []
    if phase in ("morning", "weekend", "all") and premarket:
        fetch_cmd = [
            PY,
            "scripts/fetch_naver_openapi_signals_v1.py",
            "--allow-cache-fallback",
        ]
        premarket_path = ROOT / str(premarket).replace("/", "\\")
        if premarket_path.is_file():
            doc = load_json(premarket_path)
            profile = doc.get("profile_id")
            if profile:
                fetch_cmd.extend(["--profile", "kospi_premarket"])
        if dry_run:
            steps.append({"name": f"{domain_id}_ingest_dry", "cmd": fetch_cmd, "exit_code": 0, "optional": True, "tail": "dry_run"})
        else:
            steps.append(_run(f"{domain_id}_premarket_fetch", fetch_cmd, optional=True))

    if dry_run:
        steps.append({"name": f"{domain_id}_gp_gen_dry", "cmd": gen_cmd, "exit_code": 0, "optional": False, "tail": "dry_run"})
        steps.append({"name": f"{domain_id}_gp_brier_dry", "cmd": brier_cmd, "exit_code": 0, "optional": False, "tail": "dry_run"})
        return steps

    steps.append(_run(f"{domain_id}_gp_generate", gen_cmd))
    steps.append(_run(f"{domain_id}_gp_brier", brier_cmd))
    return steps


def _select_domains(registry: dict[str, Any], domain_ids: list[str] | None) -> list[dict[str, Any]]:
    rows = [r for r in (registry.get("domains") or []) if isinstance(r, dict)]
    if domain_ids:
        wanted = set(domain_ids)
        return [r for r in rows if r.get("domain_id") in wanted]
    return [
        r
        for r in rows
        if r.get("status") in ("active", "active_shadow", "active_regression", "active_smoke")
        and r.get("phase") in ("P0", "P1", "P2", "P3")
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain-id", action="append", default=[], dest="domain_ids")
    ap.add_argument("--phase", choices=("morning", "evening", "weekend", "all"), default="evening")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    registry = load_registry(REGISTRY)
    targets = _select_domains(registry, args.domain_ids or None)
    if not targets:
        print("no domains selected", file=sys.stderr)
        return 2

    all_steps: list[dict[str, Any]] = []
    domain_results: list[dict[str, Any]] = []

    for row in targets:
        domain_id = str(row.get("domain_id"))
        archetype = str(row.get("archetype"))
        steps: list[dict[str, Any]] = []
        config: dict[str, Any] = {}
        try:
            if row.get("config_path"):
                config = load_domain_config(row)
            if archetype == "price_direction":
                steps = _dispatch_price(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "general_prophecy":
                steps = _dispatch_general(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "ground_truth_triplet":
                steps = _dispatch_ground_truth(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "news_join":
                steps = _dispatch_news_join(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "briefing_only":
                steps = _dispatch_briefing_only(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "personalized_general":
                steps = _dispatch_personalized_general(domain_id, config, args.phase, dry_run=args.dry_run)
            elif archetype == "observation_only":
                steps = _dispatch_observation_only(domain_id, config, args.phase, dry_run=args.dry_run)
            else:
                steps = [
                    {
                        "name": f"{domain_id}_unsupported_archetype",
                        "cmd": [],
                        "exit_code": 0,
                        "optional": True,
                        "tail": f"skip archetype={archetype}",
                    }
                ]
        except FileNotFoundError as exc:
            steps = [
                {
                    "name": f"{domain_id}_config_error",
                    "cmd": [],
                    "exit_code": 1,
                    "optional": False,
                    "tail": str(exc),
                }
            ]
        all_steps.extend(steps)
        req_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
        domain_results.append(
            {
                "domain_id": domain_id,
                "archetype": archetype,
                "quality_ok": len(req_fail) == 0,
                "steps": steps,
            }
        )

    required_fail = [s for s in all_steps if not s.get("optional") and s["exit_code"] != 0]
    quality_ok = len(required_fail) == 0

    doc = {
        "schema": "domain_prophecy_daily_loop_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "phase": args.phase,
        "dry_run": args.dry_run,
        "quality_ok": quality_ok,
        "domains": domain_results,
        "reproduce": f"py scripts/run_domain_prophecy_daily_loop_v1.py --phase {args.phase}",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/domain_prophecy_daily_loop_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": quality_ok, "domains": len(domain_results), "phase": args.phase}, ensure_ascii=False))
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
