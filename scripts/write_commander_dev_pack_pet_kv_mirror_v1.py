#!/usr/bin/env python3
"""RQ-027 local KV mirror + optional remote telemetry write [HYPO].

Writes pet telemetry coach_event to reports/pet_companion_kv_mirror/ (local SSOT).
Operator commander-dev slots stay in separate path — never under pet profile.

Remote wrangler put only when MKM_PET_KV_REMOTE_WRITE=1 (telemetry fields only).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUB = ROOT / "reports" / "commander_dev_pack_pet_bridge_kv_stub_latest.json"
DEFAULT_BRIDGE = ROOT / "reports" / "tmp" / "commander_dev_pack_pet_bridge_request_dry_run_latest.json"
DEFAULT_OUT = ROOT / "reports" / "commander_dev_pack_pet_kv_mirror_write_latest.json"
MIRROR_ROOT = ROOT / "reports" / "pet_companion_kv_mirror"
DEFAULT_NS = "2dc41cddcb1e417181bd2876916697bd"
WRANGLER_CWD = ROOT / "projects" / "mkm" / "mkm-life"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str) -> bool:
    v = os.getenv(name)
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)


def _run_wrangler(cmd: List[str], *, use_api_token: bool) -> tuple[int, str, str]:
    if cmd and cmd[0] == "npx":
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        if npx:
            cmd = [npx, *cmd[1:]]
    env = dict(os.environ)
    if not use_api_token:
        env.pop("CLOUDFLARE_API_TOKEN", None)
        env.pop("CF_API_TOKEN", None)
    proc = subprocess.run(
        cmd,
        cwd=str(WRANGLER_CWD),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _telemetry_coach_event(
    *,
    profile_id: str,
    scenario: str,
    bridge_req: Dict[str, Any],
    event_id: str,
) -> Dict[str, Any]:
    q = str(bridge_req.get("raw_user_question_masked") or "")
    inj = bridge_req.get("memory_context_injection") if isinstance(bridge_req.get("memory_context_injection"), dict) else {}
    return {
        "schema": "pet_companion_coach_event_v1",
        "event_id": event_id,
        "ts_utc": _utc_now(),
        "profile_id": profile_id,
        "scenario": scenario if scenario in ("walk", "meal", "behavior", "health_check", "other") else "health_check",
        "status": "GUIDED_CHECKLIST",
        "emergency_signal": False,
        "question_chars": len(q),
        "profile_loaded": True,
        "memory_context_injected": bool(inj.get("extracted_slots")),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "rq027_source": "commander_dev_pack_pet_kv_mirror_v1",
        "bridge_request_id": bridge_req.get("request_id"),
    }


def _profile_telemetry_snapshot(profile_id: str, event_id: str) -> Dict[str, Any]:
    return {
        "schema": "pet_companion_profile_kv_snapshot_v1",
        "profile_id": profile_id,
        "updated_at_utc": _utc_now(),
        "last_event_id": event_id,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "note": "RQ-027 telemetry snapshot only; no commander merge",
    }


def _wrangler_kv_put_file(kv_key: str, file_path: Path, namespace_id: str, *, use_api_token: bool) -> tuple[int, str, str]:
    cmd = [
        "npx",
        "wrangler",
        "kv",
        "key",
        "put",
        kv_key,
        "--namespace-id",
        namespace_id,
        "--path",
        str(file_path),
        "--remote",
    ]
    return _run_wrangler(cmd, use_api_token=use_api_token)


def _maybe_remote_put(kv_key: str, payload: Dict[str, Any], namespace_id: str) -> Dict[str, Any]:
    if not _truthy("MKM_PET_KV_REMOTE_WRITE"):
        return {"skipped": True, "reason": "MKM_PET_KV_REMOTE_WRITE not set"}
    if not namespace_id.strip():
        return {"skipped": True, "reason": "empty kv namespace id"}

    tmp_dir = ROOT / "reports" / "tmp" / "pet_kv_remote_put"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe_name = kv_key.replace("/", "__").replace(":", "_")[-120:]
    if safe_name.endswith(".json"):
        safe_name = safe_name[:-5]
    tmp_file = tmp_dir / f"{safe_name}.json"
    tmp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    force_token = _truthy("MKM_WRANGLER_FORCE_API_TOKEN")
    saved_cf = os.environ.get("CLOUDFLARE_API_TOKEN")
    saved_alias = os.environ.get("CF_API_TOKEN")

    code, stdout, stderr = _wrangler_kv_put_file(kv_key, tmp_file, namespace_id, use_api_token=force_token)
    auth_mode = "api_token" if force_token else "oauth_first"

    if code != 0 and not force_token and (saved_cf or saved_alias):
        code, stdout, stderr = _wrangler_kv_put_file(kv_key, tmp_file, namespace_id, use_api_token=True)
        auth_mode = "api_token_retry"

    return {
        "skipped": False,
        "exit_code": code,
        "kv_key": kv_key,
        "auth_mode": auth_mode,
        "upload_path": str(tmp_file.relative_to(ROOT)).replace("\\", "/"),
        "stdout_tail": (stdout or "")[-400:],
        "stderr_tail": (stderr or "")[-400:],
        "ok": code == 0,
    }


def write_mirror(
    *,
    stub_path: Path,
    bridge_path: Path,
    namespace_id: str,
) -> Dict[str, Any]:
    stub = _read_json(stub_path)
    bridge = _read_json(bridge_path)
    pet = stub.get("pet_target") if isinstance(stub.get("pet_target"), dict) else {}
    profile_id = str(pet.get("profile_id") or "pet-demo-001")
    plan = stub.get("pet_kv_injection_plan") if isinstance(stub.get("pet_kv_injection_plan"), dict) else {}
    base_event = str(plan.get("planned_event_id") or f"stub-{datetime.now(timezone.utc).strftime('%Y%m%d')}")
    event_id = f"{base_event}-rq027-{uuid.uuid4().hex[:8]}"
    scenario = str((stub.get("pet_bridge_request_dry_run") or {}).get("scenario") or "health_check")

    coach = _telemetry_coach_event(
        profile_id=profile_id,
        scenario=scenario,
        bridge_req=bridge,
        event_id=event_id,
    )
    profile_snap = _profile_telemetry_snapshot(profile_id, event_id)

    coach_key = f"pet_companion/coach_events/{profile_id}/{event_id}.json"
    profile_key = f"pet_companion/profile/{profile_id}.json"

    coach_local = MIRROR_ROOT / "coach_events" / profile_id / f"{event_id}.json"
    profile_local = MIRROR_ROOT / "profile" / f"{profile_id}.json"
    operator_local = MIRROR_ROOT / "operator" / "commander-dev" / "operator_slots.json"

    coach_local.parent.mkdir(parents=True, exist_ok=True)
    profile_local.parent.mkdir(parents=True, exist_ok=True)
    operator_local.parent.mkdir(parents=True, exist_ok=True)

    coach_local.write_text(json.dumps(coach, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    profile_local.write_text(json.dumps(profile_snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    operator_local.write_text(
        json.dumps(
            {
                "schema": "commander_operator_channel_local_v1",
                "generated_at_utc": _utc_now(),
                "operator_channel": stub.get("operator_channel"),
                "must_not_forward_to_pet_bridge": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    remote_coach = _maybe_remote_put(coach_key, coach, namespace_id)
    remote_profile = _maybe_remote_put(profile_key, profile_snap, namespace_id)

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            return str(p)

    return {
        "schema": "commander_dev_pack_pet_kv_mirror_write_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "rq_id": "RQ-027",
        "stub_ref": (
            str(stub_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            if stub_path.resolve().is_relative_to(ROOT.resolve())
            else str(stub_path)
        ),
        "local_mirror_root": (
            str(MIRROR_ROOT.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            if MIRROR_ROOT.resolve().is_relative_to(ROOT.resolve())
            else str(MIRROR_ROOT)
        ),
        "paths_written": {
            "coach_event": _rel(coach_local),
            "profile_snapshot": _rel(profile_local),
            "operator_slots": _rel(operator_local),
        },
        "kv_keys_planned": {"coach_event": coach_key, "profile": profile_key},
        "remote_put": {"coach_event": remote_coach, "profile": remote_profile},
        "integrity": {
            "commander_to_pet_merge_forbidden": stub.get("commander_to_pet_merge_forbidden", True),
            "stub_integrity_pass": (stub.get("integrity_check") or {}).get("pass"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stub-json", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--bridge-json", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--kv-namespace-id", default=DEFAULT_NS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    _load_dotenv()

    stub_path = args.stub_json if args.stub_json.is_absolute() else ROOT / args.stub_json
    bridge_path = args.bridge_json if args.bridge_json.is_absolute() else ROOT / args.bridge_json
    if not stub_path.is_file():
        print(f"MISSING: {stub_path}", flush=True)
        return 2
    if not bridge_path.is_file():
        print(f"MISSING: {bridge_path} — run build_commander_dev_pack_pet_bridge_kv_stub_v1.py first", flush=True)
        return 2

    payload = write_mirror(stub_path=stub_path, bridge_path=bridge_path, namespace_id=args.kv_namespace_id.strip())
    if not args.stdout_only:
        out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out}")
    remote = payload.get("remote_put") or {}
    remote_ok = all(
        (v.get("skipped") or v.get("ok"))
        for v in remote.values()
        if isinstance(v, dict)
    ) and any(
        isinstance(v, dict) and v.get("ok") for v in remote.values()
    ) if _truthy("MKM_PET_KV_REMOTE_WRITE") else True
    print(
        json.dumps(
            {
                "ok": remote_ok,
                "mirror": payload["paths_written"],
                "remote_put": remote,
            },
            ensure_ascii=False,
        )
    )
    return 0 if remote_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
