#!/usr/bin/env python3
"""POST device_memory_bridge to mkmlife Worker; save live request/response ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/pet_companion_device_memory_bridge_v1_fixture.json"
DEFAULT_SLOTS = ROOT / "reports/pet_companion_memory_slots_latest.json"
DEFAULT_REQ_OUT = ROOT / "reports/pet_companion_device_bridge_live_request_latest.json"
DEFAULT_RES_OUT = ROOT / "reports/pet_companion_device_bridge_live_response_latest.json"
BRIDGE_PATH = "/api/v1/pet-companion/bridge"
REQUEST_SCHEMA = "pet_companion_device_memory_bridge_request_v1"
RESPONSE_SCHEMA = "pet_companion_device_memory_bridge_response_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _scenario_from_slots(slots: list[dict[str, Any]], *, fallback: str) -> str:
    allowed = {"walk", "meal", "behavior", "health_check", "other"}
    for slot in slots:
        if slot.get("type") == "behavior_pattern":
            val = str(slot.get("value") or "").strip()
            if val in allowed:
                return val
    return fallback if fallback in allowed else "health_check"


def _extracted_slots_from_memory_slots(slots: list[dict[str, Any]], *, profile_id: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for slot in slots[:12]:
        val = slot.get("value")
        if isinstance(val, dict):
            fact = json.dumps(val, ensure_ascii=False)[:100]
        else:
            fact = f"{slot.get('type', 'slot')}: {val}"[:100]
        if not fact.strip():
            continue
        out.append(
            {
                "subject": profile_id,
                "fact_summary": fact,
                "confidence_tier": "SLOT_INFERRED",
            }
        )
    return out


def build_bridge_request(
    *,
    profile_id: str,
    scenario: str,
    question_masked: str,
    extracted_slots: list[dict[str, str]],
    template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    req_id = f"req-live-{uuid.uuid4().hex[:12]}"
    body: dict[str, Any] = {
        "schema": REQUEST_SCHEMA,
        "schema_version": "1.0.0",
        "request_id": req_id,
        "client_ts_utc": _utc_now(),
        "profile_id": profile_id,
        "scenario": scenario,
        "raw_user_question_masked": question_masked[:1000],
        "emergency_signal": False,
        "redaction_profile_id": "pii_mask_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "memory_context_injection": {
            "timestamp_epoch_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
            "extracted_slots": extracted_slots,
        },
    }
    if template:
        for key in (
            "schema",
            "schema_version",
            "redaction_profile_id",
            "hypothesis_tier",
            "research_only",
            "non_gating",
        ):
            if key in template:
                body[key] = template[key]
    return body


def build_request_from_artifacts(
    *,
    fixture_path: Path,
    slots_path: Path,
    profile_id: str | None,
    scenario: str | None,
    question_masked: str | None,
) -> dict[str, Any]:
    fixture = _load_json(fixture_path) or {}
    template = fixture.get("mock_request") if isinstance(fixture.get("mock_request"), dict) else {}
    slots_doc = _load_json(slots_path) or {}
    by_profile = slots_doc.get("slots_by_profile") if isinstance(slots_doc.get("slots_by_profile"), dict) else {}

    pid = profile_id or str(template.get("profile_id") or "pet-demo-001")
    prof_slots = by_profile.get(pid) if isinstance(by_profile.get(pid), list) else []
    if not prof_slots and by_profile:
        pid = next(iter(by_profile.keys()))
        prof_slots = by_profile.get(pid) if isinstance(by_profile.get(pid), list) else []

    scen = scenario or _scenario_from_slots(prof_slots, fallback=str(template.get("scenario") or "health_check"))
    question = question_masked or str(
        template.get("raw_user_question_masked")
        or "반려 동물 건강·루틴 관찰 질문(마스킹됨)"
    )
    extracted = _extracted_slots_from_memory_slots(prof_slots, profile_id=pid)
    if not extracted and isinstance(template.get("memory_context_injection"), dict):
        raw_slots = template["memory_context_injection"].get("extracted_slots")
        if isinstance(raw_slots, list):
            extracted = [s for s in raw_slots if isinstance(s, dict)][:12]  # type: ignore[arg-type]

    return build_bridge_request(
        profile_id=pid,
        scenario=scen,
        question_masked=question,
        extracted_slots=extracted,
        template=template,
    )


def _base_urls(cli_base: str | None) -> list[str]:
    if cli_base:
        return [cli_base.rstrip("/")]
    env = (os.environ.get("MKMLIFE_BASE_URL") or os.environ.get("PET_COMPANION_BASE_URL") or "").strip()
    candidates = [env, "https://mkmlife.com", "http://127.0.0.1:3105", "http://localhost:3105"]
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if not c:
            continue
        u = c.rstrip("/")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def post_bridge(base_url: str, body: dict[str, Any], *, timeout_s: float) -> tuple[int, dict[str, Any]]:
    url = f"{base_url}{BRIDGE_PATH}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": (
                "MKM-PetCompanionBridgePoC/1.0 "
                "(B-track research_only; +https://mkm12.local/pet-companion-device-bridge)"
            ),
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            status = int(resp.status)
            raw = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        status = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        raise RuntimeError(f"url_error:{exc.reason}") from exc

    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        parsed = {"error": "invalid_json", "raw": raw[:500]}
    return status, parsed if isinstance(parsed, dict) else {"error": "non_object_response"}


def validate_response(body: dict[str, Any], *, request_id: str) -> list[str]:
    errs: list[str] = []
    if body.get("schema") != RESPONSE_SCHEMA:
        errs.append("schema_mismatch")
    if body.get("request_id") != request_id:
        errs.append("request_id_mismatch")
    policy = body.get("server_persistence_policy")
    if not isinstance(policy, dict):
        errs.append("missing_server_persistence_policy")
    else:
        must_not = policy.get("must_not_persist")
        if not isinstance(must_not, list) or "extracted_slots" not in must_not:
            errs.append("must_not_persist_extracted_slots")
    hints = body.get("local_graph_update_hints")
    if not isinstance(hints, dict):
        errs.append("missing_local_graph_update_hints")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture-json", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--slots-json", type=Path, default=DEFAULT_SLOTS)
    ap.add_argument("--profile-id", default="")
    ap.add_argument("--scenario", default="")
    ap.add_argument("--question-masked", default="")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--timeout-s", type=float, default=30.0)
    ap.add_argument("--request-out", type=Path, default=DEFAULT_REQ_OUT)
    ap.add_argument("--response-out", type=Path, default=DEFAULT_RES_OUT)
    ap.add_argument("--dry-run", action="store_true", help="Build request only; no HTTP")
    ap.add_argument(
        "--transport",
        choices=("auto", "python", "node"),
        default="auto",
        help="auto=node smoke when available, else python urllib",
    )
    ap.add_argument(
        "--fallback-fixture-on-block",
        action="store_true",
        help="If edge blocks (e.g. CF 1010), use fixture mock_response for graph PoC only",
    )
    args = ap.parse_args()

    fixture_path = args.fixture_json if args.fixture_json.is_absolute() else ROOT / args.fixture_json
    slots_path = args.slots_json if args.slots_json.is_absolute() else ROOT / args.slots_json
    req_out = args.request_out if args.request_out.is_absolute() else ROOT / args.request_out
    res_out = args.response_out if args.response_out.is_absolute() else ROOT / args.response_out

    bridge_req = build_request_from_artifacts(
        fixture_path=fixture_path,
        slots_path=slots_path,
        profile_id=args.profile_id or None,
        scenario=args.scenario or None,
        question_masked=args.question_masked or None,
    )
    req_out.parent.mkdir(parents=True, exist_ok=True)
    req_out.write_text(json.dumps(bridge_req, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "request_out": str(req_out)}, ensure_ascii=False))
        return 0

    def _post_via_node(base_url: str) -> tuple[int, dict[str, Any]]:
        import subprocess
        import shutil

        smoke = ROOT / "projects/mkm/mkm-life/scripts/smoke-pet-companion-bridge.mjs"
        if not smoke.is_file():
            raise RuntimeError("node_smoke_missing")
        node = shutil.which("node") or shutil.which("node.exe")
        if not node:
            raise RuntimeError("node_missing")
        env = dict(os.environ)
        env["MKMLIFE_BASE_URL"] = base_url
        env["MKM_BRIDGE_REQUEST_JSON"] = json.dumps(bridge_req, ensure_ascii=False)
        proc = subprocess.run(
            [node, str(smoke)],
            cwd=str(ROOT / "projects/mkm/mkm-life"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=max(5, int(args.timeout_s) + 5),
        )
        if proc.returncode != 0:
            raise RuntimeError(f"node_smoke_exit_{proc.returncode}:{proc.stderr[-400:]}")
        out_path = env.get("MKM_BRIDGE_RESPONSE_OUT") or str(
            ROOT / "reports/_tmp_pet_bridge_live_response.json"
        )
        parsed = _load_json(Path(out_path))
        if not parsed:
            raise RuntimeError("node_smoke_no_response_file")
        return 200, parsed

    last_err: str | None = None
    used_base: str | None = None
    transport_used: str | None = None
    status = 0
    response: dict[str, Any] = {}
    tmp_res = ROOT / "reports/_tmp_pet_bridge_live_response.json"

    for base in _base_urls(args.base_url or None):
        try:
            if args.transport in ("auto", "node"):
                os.environ["MKM_BRIDGE_RESPONSE_OUT"] = str(tmp_res)
                status, response = _post_via_node(base)
                transport_used = "node"
            else:
                status, response = post_bridge(base, bridge_req, timeout_s=args.timeout_s)
                transport_used = "python"
            val_errs = validate_response(response, request_id=str(bridge_req["request_id"]))
            if status == 200 and not val_errs:
                used_base = base
                break
            last_err = f"http_{status}:{','.join(val_errs) or 'validation_failed'}"
        except RuntimeError as exc:
            if args.transport == "auto" and "node_smoke" in str(exc):
                try:
                    status, response = post_bridge(base, bridge_req, timeout_s=args.timeout_s)
                    transport_used = "python"
                    val_errs = validate_response(response, request_id=str(bridge_req["request_id"]))
                    if status == 200 and not val_errs:
                        used_base = base
                        break
                    last_err = f"http_{status}:{','.join(val_errs) or 'validation_failed'}"
                except RuntimeError as exc2:
                    last_err = str(exc2)
            else:
                last_err = str(exc)

    if not used_base and args.fallback_fixture_on_block:
        fixture = _load_json(fixture_path) or {}
        mock = fixture.get("mock_response") if isinstance(fixture.get("mock_response"), dict) else {}
        if mock:
            response = dict(mock)
            response["request_id"] = str(bridge_req["request_id"])
            response["response_id"] = f"res-fallback-{uuid.uuid4().hex[:8]}"
            used_base = "fixture_fallback"
            transport_used = "fixture_fallback"
            last_err = None

    if not used_base:
        print(
            json.dumps(
                {"ok": False, "error": last_err or "all_bases_failed", "request_out": str(req_out)},
                ensure_ascii=False,
            )
        )
        return 1

    res_out.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hints = response.get("local_graph_update_hints") if isinstance(response.get("local_graph_update_hints"), dict) else {}
    print(
        json.dumps(
            {
                "ok": True,
                "base_url": used_base,
                "transport": transport_used,
                "status": response.get("status"),
                "bridge_slots_count": (response.get("input_meta_reflected") or {}).get("bridge_slots_count"),
                "hints_nodes": len(hints.get("suggested_nodes_to_upsert") or []),
                "hints_edges": len(hints.get("suggested_edges_to_link") or []),
                "request_out": str(req_out),
                "response_out": str(res_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
