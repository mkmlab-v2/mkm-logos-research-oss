#!/usr/bin/env python3
"""Logos hybrid middleware chain: shallow E2E → UMR → gateway stub metadata [HOLD].

  py scripts/run_logos_hybrid_middleware_chain_v1.py
  py scripts/run_logos_hybrid_middleware_chain_v1.py --run-ollama --query "성경 gematria GraphRAG"
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
REGISTRY_V2 = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_hybrid_middleware_chain_v1_latest.json"
E2E_OUT = ROOT / "reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json"
HANDOFF = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
UMR_OUT = ROOT / "docs/final/artifacts/universal_multi_res_router_logos_hybrid_chain_v1_latest.json"
API_SMOKE = ROOT / "reports/universal_multi_res_router_api_stub_smoke_v1_latest.json"
REPLAY_OUT = ROOT / "reports/universal_multi_res_router_logos_hybrid_replay_stub_v1_latest.json"
ENVELOPE_OUT = ROOT / "docs/final/artifacts/jema_os_coordinate_envelope_v1_latest.json"

MKMLIFE_SKU_POINTER = {
    "domain": "mkmlife.com",
    "sku_lane": "one_question_premium",
    "product_surface": "/oracle-sphere",
    "policy_ref": "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",
    "gateway_route": "/api/v1/lens/route",
    "metering_enabled": False,
    "send_gate": "HOLD",
    "track_a_promotion_allowed": False,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _run(cmd: list[str], *, timeout: int = 180) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    tail = (proc.stdout or "") + (proc.stderr or "")
    return int(proc.returncode), tail.strip()


def _write(path: Path, steps: dict[str, Any], *, ok: bool, coordinate_envelope_ref: str | None = None) -> None:
    doc = {
        "schema": "logos_hybrid_middleware_chain_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "track_a_promotion_allowed": False,
        "cloud_llm_called": False,
        "ok": ok,
        "steps": steps,
        "b2c_commercial_surface": MKMLIFE_SKU_POINTER,
        "reproduce": "py scripts/run_logos_hybrid_middleware_chain_v1.py",
    }
    if coordinate_envelope_ref:
        doc["coordinate_envelope_ref"] = coordinate_envelope_ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-ollama", action="store_true")
    ap.add_argument("--query", default="성경 gematria GraphRAG sidecar lookup")
    ap.add_argument("--skip-api-stub-smoke", action="store_true")
    ap.add_argument("--read-depth", choices=("skim", "deep", "hold"), default="skim")
    ap.add_argument("--envelope-lane", default="oracle")
    args = ap.parse_args()

    steps: dict[str, Any] = {}

    e2e_cmd = [
        PY,
        str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
        "--include-deep-chain-dry-run",
    ]
    if args.run_ollama:
        e2e_cmd.extend(["--run-ollama", "--query", args.query, "--expected-domain", "logos"])
    rc, tail = _run(e2e_cmd, timeout=300 if args.run_ollama else 120)
    steps["shallow_e2e"] = {
        "ok": rc == 0,
        "exit_code": rc,
        "artifact": str(E2E_OUT),
        "tail": tail[-400:] if rc else None,
    }
    if rc != 0:
        _write(args.out, steps, ok=False)
        return 1

    handoff = _read_json(HANDOFF)
    ctx = handoff.get("logos_lookup_context") or {}
    steps["handoff_logos_context"] = {
        "ok": bool(ctx.get("stack_ok")),
        "artifact": str(HANDOFF),
        "sidecar_verse_count": (ctx.get("sidecar_v2_stats") or {}).get("verse_count"),
        "graphrag_audit_pass": (ctx.get("graphrag_regression") or {}).get("overall_pass"),
    }
    if not steps["handoff_logos_context"]["ok"]:
        _write(args.out, steps, ok=False)
        return 1

    umr_cmd = [
        PY,
        str(ROOT / "scripts/universal_multi_res_router_v1.py"),
        "--query",
        args.query,
        "--shallow-json",
        str(HANDOFF),
        "--infrastructure-mode",
        "headless_ci",
        "-o",
        str(UMR_OUT),
    ]
    rc, tail = _run(umr_cmd)
    umr = _read_json(UMR_OUT)
    umr_ctx = umr.get("logos_lookup_context") or {}
    slot_v2 = umr.get("domain_plugin_slot_v2")
    registry_v2_ref = umr.get("jema_os_plugin_registry_v2_ref")
    slot_v2_ok = True
    if REGISTRY_V2.is_file():
        slot_v2_ok = isinstance(slot_v2, dict) and bool(slot_v2.get("slot_id"))
    steps["umr_route"] = {
        "ok": rc == 0 and umr_ctx.get("stack_ok") is True and slot_v2_ok,
        "exit_code": rc,
        "artifact": str(UMR_OUT),
        "resolution_tier": umr.get("resolution_tier"),
        "domain_tag": umr.get("domain_tag"),
        "inference_provider": (umr.get("inference_adapter") or {}).get("provider"),
        "jema_os_plugin_registry_v2_ref": registry_v2_ref,
        "domain_plugin_slot_v2": slot_v2 if isinstance(slot_v2, dict) else None,
        "tail": tail[-300:] if rc != 0 or not slot_v2_ok else None,
    }
    if not steps["umr_route"]["ok"]:
        _write(args.out, steps, ok=False)
        return 1

    rc, _tail = _run([PY, str(ROOT / "scripts/run_universal_multi_res_router_logos_hybrid_replay_stub_v1.py")])
    replay = _read_json(REPLAY_OUT)
    steps["hybrid_replay_stub"] = {
        "ok": rc == 0 and replay.get("overall_pass") is True,
        "exit_code": rc,
        "overall_pass": replay.get("overall_pass"),
    }
    if not steps["hybrid_replay_stub"]["ok"]:
        _write(args.out, steps, ok=False)
        return 1

    if not args.skip_api_stub_smoke:
        rc, _tail = _run([PY, str(ROOT / "scripts/run_universal_multi_res_router_api_stub_smoke_v1.py")])
        smoke = _read_json(API_SMOKE)
        smoke_pass = smoke.get("overall_pass") is True or smoke.get("ok") is True
        steps["api_gateway_stub_smoke"] = {
            "ok": rc == 0 and smoke_pass,
            "exit_code": rc,
            "artifact": str(API_SMOKE),
            "metering_enabled": smoke.get("metering_enabled")
            or ((smoke.get("steps") or {}).get("health") or {}).get("body", {}).get("metering_enabled"),
        }
        if not steps["api_gateway_stub_smoke"]["ok"]:
            _write(args.out, steps, ok=False)
            return 1

    env_cmd = [
        PY,
        str(ROOT / "scripts/build_jema_os_coordinate_envelope_v1.py"),
        "--out",
        str(ENVELOPE_OUT),
        "--read-depth",
        args.read_depth,
        "--lane",
        args.envelope_lane,
        "--hybrid-json",
        str(args.out),
        "--umr-json",
        str(UMR_OUT),
    ]
    rc, tail = _run(env_cmd)
    envelope = _read_json(ENVELOPE_OUT)
    steps["coordinate_envelope"] = {
        "ok": rc == 0 and envelope.get("schema") == "jema_os_coordinate_envelope_v1",
        "exit_code": rc,
        "artifact": str(ENVELOPE_OUT),
        "read_depth": envelope.get("read_depth"),
        "resolution_tier": (envelope.get("umr_binding") or {}).get("resolution_tier"),
        "tail": tail[-300:] if rc != 0 else None,
    }
    if not steps["coordinate_envelope"]["ok"]:
        _write(args.out, steps, ok=False)
        return 1

    _write(
        args.out,
        steps,
        ok=True,
        coordinate_envelope_ref=str(ENVELOPE_OUT.relative_to(ROOT)).replace("\\", "/"),
    )
    print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
