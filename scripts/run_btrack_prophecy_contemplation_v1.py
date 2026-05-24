#!/usr/bin/env python3
"""B-track prophecy pilot: pre-generation contemplation gate (local bundle guards + digest).

Writes docs/final/artifacts/btrack_prophecy_contemplation_v1_latest.json.

1) Local bundle guards (always): BTC scope, artifacts shape.
2) Optional Gemini reflect (cost): MKM_BTRACK_CONTEMPLATION_USE_GEMINI=1 and API key; JSON-only contract.

Invoked from run_btrack_daily_hypothesis_chain.ps1 when -ResearchEvaluationInstrument is btc unless
MKM_BTRACK_PROPHECY_CONTEMPLATION_V1 is 0 or false (opt-out).

Env (optional):
  MKM_BTRACK_CONTEMPLATION_TIMEOUT_SEC — wall-clock cap for the whole script (default 30; raise for Gemini).
  MKM_BTRACK_CONTEMPLATION_MAX_OUTPUT_TOKENS — recorded in budget JSON (default 0).
  MKM_BTRACK_CONTEMPLATION_MAX_ROUNDS — recorded (default 1).
  MKM_BTRACK_CONTEMPLATION_USE_GEMINI — truthy to run Gemini after local pass (strict fail if no API key).
  MKM_BTRACK_CONTEMPLATION_GEMINI_MODEL — default gemini-2.5-flash
  MKM_BTRACK_CONTEMPLATION_THINKING_BUDGET — passed to ThinkingConfig; 0 disables thinking budget.
  MKM_BTRACK_CONTEMPLATION_GEMINI_TIMEOUT_SEC — HTTP-ish ceiling for the Gemini call (default 120).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.btrack_interpretive_bridge_v1 import compact_interpretive_for_prompt

DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_contemplation_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "btrack_prophecy_contemplation_v1.schema.json"
SCHEMA_ID = "btrack_prophecy_contemplation_v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _env_truthy(name: str) -> bool:
    v = str(os.environ.get(name) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _gemini_api_key() -> str | None:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            o = json.loads(m.group(1).strip())
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            pass
    try:
        o = json.loads(text)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def _collect_btc_scope_violations(bundle: dict[str, Any]) -> list[str]:
    arts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    violations: list[str] = []
    if not isinstance(arts, dict):
        return violations

    def _check(name: str, art: Any) -> None:
        if not isinstance(art, dict):
            return
        ts = art.get("trading_scope") if isinstance(art.get("trading_scope"), dict) else {}
        if isinstance(ts, dict):
            pa = str(ts.get("primary_asset") or "").strip().upper()
            if pa and pa != "BTCUSDT":
                violations.append(f"{name}:trading_scope.primary_asset={pa}")
        ps = art.get("policy_scope") if isinstance(art.get("policy_scope"), dict) else {}
        if isinstance(ps, dict):
            pa2 = str(ps.get("trading_primary_asset") or "").strip().upper()
            if pa2 and pa2 != "BTCUSDT":
                violations.append(f"{name}:policy_scope.trading_primary_asset={pa2}")
            kospi_role = str(ps.get("kospi_role") or "").strip().lower()
            if kospi_role and kospi_role != "observation_only":
                violations.append(f"{name}:policy_scope.kospi_role={kospi_role}")

    for k, v in arts.items():
        _check(str(k), v)
    return violations


def _try_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    try:
        schema = _load_json(schema_path)
        jsonschema.Draft202012Validator(schema).validate(doc)
    except Exception as e:  # noqa: BLE001
        return [str(e)]
    return []


def _append_audit(
    repo: Path,
    *,
    stage: str,
    decision: str,
    evidence_rel: str,
    note: str,
    skip: bool,
) -> None:
    if skip:
        return
    log_py = repo / "scripts" / "log_agent_decision.py"
    if not log_py.is_file():
        return
    cmd = [
        sys.executable,
        str(log_py),
        "--repo-root",
        str(repo),
        "--mission-id",
        "btrack_prophecy_contemplation_v1",
        "--stage",
        stage,
        "--decision",
        decision,
        "--evidence-path",
        evidence_rel.replace("\\", "/"),
        "--actor",
        "run_btrack_prophecy_contemplation_v1.py",
        "--note",
        note[:3800],
    ]
    subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, check=False)


def _run_gemini_reflect(
    bundle: dict[str, Any],
    *,
    model: str,
    thinking_budget: int,
    timeout_sec: int,
) -> dict[str, Any]:
    """Call Gemini; return dict with contemplation_ok, risk_flags, redacted_summary or raises."""
    key = _gemini_api_key()
    if not key:
        raise RuntimeError("missing_gemini_api_key")

    from google import genai
    from google.genai import types

    arts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    interpretive_bridge = arts.get("sasang_interpretive_bridge_context") if isinstance(arts, dict) else {}
    if not isinstance(interpretive_bridge, dict):
        interpretive_bridge = {}
    interpretive_digest = compact_interpretive_for_prompt(interpretive_bridge)

    bundle_text = json.dumps(bundle, ensure_ascii=False, indent=2)[:72_000]
    prompt = f"""You are a B-track research-only pre-flight reviewer (not live trading, not medical).
Read the JSON bundle snapshot. Reply with a single JSON object only (no markdown fences).

Required JSON shape:
{{
  "contemplation_ok": true or false,
  "risk_flags": ["short snake_case strings, max 12 items"],
  "redacted_summary": "one or two English sentences; no dollar amounts, no trade instructions"
}}

Set contemplation_ok=false if the bundle suggests non-BTC execution gating, medical claims, or contradictions
with a strict BTC-only research lane. Sasang interpretive axes are human_only reference — do not treat them as
clinical diagnosis or order triggers. Otherwise true.

Sasang interpretive bridge digest (read-only, non-gating):
{interpretive_digest}

Bundle JSON:
{bundle_text}
"""
    timeout_ms = max(10_000, int(timeout_sec) * 1000)
    client = genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(timeout=timeout_ms))
    cfg_kw: dict[str, Any] = {"temperature": 0.2}
    if thinking_budget > 0:
        cfg_kw["thinking_config"] = types.ThinkingConfig(thinking_budget=int(thinking_budget))
    config = types.GenerateContentConfig(**cfg_kw)
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=prompt)],
        config=config,
    )
    raw = (resp.text or "").strip()
    blob = _extract_json_blob(raw)
    if not blob:
        raise RuntimeError(f"unparseable_gemini_json:{raw[:800]!r}")
    ok = bool(blob.get("contemplation_ok"))
    flags = blob.get("risk_flags")
    if not isinstance(flags, list):
        flags = []
    clean_flags: list[str] = []
    for x in flags[:24]:
        if isinstance(x, str) and x.strip():
            clean_flags.append(x.strip()[:200])
    summary = blob.get("redacted_summary")
    summary_s = str(summary).strip()[:400] if summary is not None else ""
    return {
        "contemplation_ok": ok,
        "risk_flags": clean_flags,
        "redacted_summary": summary_s,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--repo-root", type=Path, default=ROOT)
    ap.add_argument("--skip-audit-log", action="store_true")
    ap.add_argument(
        "--skip-gemini-reflect",
        action="store_true",
        help="Skip optional Gemini reflect even if MKM_BTRACK_CONTEMPLATION_USE_GEMINI is set (tests/offline).",
    )
    args = ap.parse_args()

    t0 = time.monotonic()
    timeout_sec = max(1, _env_int("MKM_BTRACK_CONTEMPLATION_TIMEOUT_SEC", 30))
    max_out = max(0, _env_int("MKM_BTRACK_CONTEMPLATION_MAX_OUTPUT_TOKENS", 0))
    max_rounds = max(1, min(8, _env_int("MKM_BTRACK_CONTEMPLATION_MAX_ROUNDS", 1)))
    gemini_timeout = max(10, _env_int("MKM_BTRACK_CONTEMPLATION_GEMINI_TIMEOUT_SEC", 120))
    gemini_model = (os.environ.get("MKM_BTRACK_CONTEMPLATION_GEMINI_MODEL") or "gemini-2.5-flash").strip()
    thinking_budget = max(0, _env_int("MKM_BTRACK_CONTEMPLATION_THINKING_BUDGET", 2048))

    if not args.bundle.is_file():
        print(f"error: bundle missing: {args.bundle}", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle)
    bundle_sha = _file_sha256(args.bundle)
    try:
        bundle_rel = str(args.bundle.resolve().relative_to(args.repo_root.resolve())).replace("\\", "/")
    except ValueError:
        bundle_rel = str(args.bundle).replace("\\", "/")

    checks: list[dict[str, Any]] = []
    arts_ok = isinstance(bundle.get("artifacts"), dict)
    checks.append({"id": "bundle_artifacts_object", "ok": arts_ok, "detail": None if arts_ok else "artifacts_not_object"})
    violations = _collect_btc_scope_violations(bundle)
    scope_ok = len(violations) == 0
    checks.append(
        {
            "id": "btc_trading_scope_bundle_guard",
            "ok": scope_ok,
            "detail": None if scope_ok else ";".join(violations[:12]),
        }
    )

    arts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    interpretive_bridge = arts.get("sasang_interpretive_bridge_context") if isinstance(arts, dict) else {}
    if not isinstance(interpretive_bridge, dict):
        interpretive_bridge = {}
    ib_present = bool(interpretive_bridge.get("available"))
    ib_guards_ok = (
        interpretive_bridge.get("auto_weight_adjustment_forbidden") is True
        and interpretive_bridge.get("track_a_live_routing_forbidden") is True
    )
    checks.append(
        {
            "id": "interpretive_bridge_present",
            "ok": True,
            "detail": "present" if ib_present else (interpretive_bridge.get("reason") or "absent_optional"),
        }
    )
    checks.append(
        {
            "id": "interpretive_bridge_safety_flags",
            "ok": (not ib_present) or ib_guards_ok,
            "detail": None if ((not ib_present) or ib_guards_ok) else "forbidden_flags_not_true",
        }
    )

    local_ok = all(bool(c.get("ok")) for c in checks)
    gemini_review: dict[str, Any] | None = None
    gr_summary: str | None = None
    model_route = "local_bundle_guard_v1"

    use_gemini = _env_truthy("MKM_BTRACK_CONTEMPLATION_USE_GEMINI") and not args.skip_gemini_reflect
    if use_gemini and local_ok:
        model_route = "local_bundle_guard_v1+gemini_reflect_v1"
        api_key = _gemini_api_key()
        if not api_key:
            checks.append(
                {
                    "id": "gemini_api_key_present",
                    "ok": False,
                    "detail": "MKM_BTRACK_CONTEMPLATION_USE_GEMINI set but no GEMINI_API_KEY/GOOGLE_API_KEY",
                }
            )
        else:
            try:
                gr = _run_gemini_reflect(
                    bundle,
                    model=gemini_model,
                    thinking_budget=thinking_budget,
                    timeout_sec=gemini_timeout,
                )
                gr_summary = str(gr.get("redacted_summary") or "").strip() or None
                gemini_review = {
                    "used": True,
                    "model": gemini_model,
                    "thinking_budget": thinking_budget if thinking_budget > 0 else None,
                    "contemplation_ok": gr.get("contemplation_ok"),
                    "risk_flags": gr.get("risk_flags") or [],
                    "error": None,
                }
                checks.append({"id": "gemini_reflect_json_contract", "ok": True, "detail": None})
                checks.append(
                    {
                        "id": "gemini_reflect_contemplation_ok",
                        "ok": bool(gr.get("contemplation_ok")),
                        "detail": None if gr.get("contemplation_ok") else "llm_flagged_contemplation_ok_false",
                    }
                )
            except Exception as e:  # noqa: BLE001
                gemini_review = {
                    "used": True,
                    "model": gemini_model,
                    "thinking_budget": thinking_budget if thinking_budget > 0 else None,
                    "contemplation_ok": None,
                    "risk_flags": [],
                    "error": str(e)[:2000],
                }
                checks.append(
                    {
                        "id": "gemini_reflect_call_ok",
                        "ok": False,
                        "detail": str(e)[:500],
                    }
                )

    elapsed = time.monotonic() - t0
    wall_ok = elapsed <= float(timeout_sec)
    checks.append(
        {
            "id": "total_wall_clock_within_timeout_sec",
            "ok": wall_ok,
            "detail": f"elapsed_sec={elapsed:.3f}" if wall_ok else f"elapsed_sec={elapsed:.3f}>cap={timeout_sec}",
        }
    )

    all_ok = all(bool(c.get("ok")) for c in checks)
    status = "pass" if all_ok else "fail"
    digest_src_obj: dict[str, Any] = {
        "bundle_sha256": bundle_sha,
        "checks": checks,
        "violations": violations,
    }
    if gemini_review is not None:
        digest_src_obj["gemini_review"] = gemini_review
    digest_src = json.dumps(digest_src_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()

    local_summary = (
        f"local_bundle_guard_v1 status_local={'pass' if local_ok else 'fail'} "
        f"checks_ok={sum(1 for c in checks if c.get('ok'))}/{len(checks)} violations_n={len(violations)}"
    )
    if gemini_review and gemini_review.get("used"):
        if gemini_review.get("error"):
            llm_s = f"gemini_err:{str(gemini_review.get('error'))[:80]}"
        elif gr_summary:
            llm_s = f"gemini:{gr_summary[:220]}"
        else:
            llm_s = "gemini_ok" if gemini_review.get("contemplation_ok") else "gemini_flagged"
        tail = f" | {llm_s}"
        summary = (local_summary + tail)[:500]
    else:
        summary = local_summary[:500]

    doc: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "generated_at_utc": _iso_now(),
        "pilot_lane": "btrack_btc_macro_prophecy",
        "budget": {
            "max_output_tokens": max_out,
            "timeout_sec": timeout_sec,
            "max_rounds": max_rounds,
        },
        "inputs_digest": {
            "bundle_path": bundle_rel,
            "bundle_sha256": bundle_sha,
        },
        "model_route": model_route,
        "review": {
            "status": status,
            "checks": checks,
            "redacted_reasoning_summary": summary,
            "reasoning_digest_sha256": digest,
        },
        "approved_hypothesis_payload": {},
        "downstream": {"compatible_with": "btrack_hypothesis_prophecy_v1"},
    }
    if gemini_review is not None:
        doc["gemini_review"] = gemini_review

    schema_errs = _try_jsonschema(doc, args.schema)
    if schema_errs:
        print("jsonschema:", *schema_errs, sep="\n", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        out_rel = str(args.output.resolve().relative_to(args.repo_root.resolve())).replace("\\", "/")
    except ValueError:
        out_rel = str(args.output).replace("\\", "/")

    _append_audit(
        args.repo_root,
        stage="s1_complete",
        decision=status,
        evidence_rel=out_rel,
        note=summary,
        skip=bool(args.skip_audit_log),
    )

    print(f"WROTE: {args.output.resolve()} review.status={status}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
