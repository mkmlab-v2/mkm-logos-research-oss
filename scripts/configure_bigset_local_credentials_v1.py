#!/usr/bin/env python3
"""Auto-configure BigSet local credentials from MKM secret planes (no browser).

Resolves OPENROUTER_API_KEY / TINYFISH_API_KEY from process env, DPAPI store,
or workspace `.env` (values never logged). POSTs to BigSet backend local-setup API.

B-track · tier_15 when keys present · send_gate HOLD.

Reproducible:
  py scripts/configure_bigset_local_credentials_v1.py
  py scripts/configure_bigset_local_credentials_v1.py --backend-url http://127.0.0.1:3501
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_local_credentials_setup_v1_latest.json"
ENV_PATH = ROOT / ".env"

SERVICE_KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "tinyfish": "TINYFISH_API_KEY",
}

SETUP_PATHS = {
    "openrouter": "/local-setup/openrouter-key",
    "tinyfish": "/local-setup/tinyfish",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv_quiet() -> None:
    if not ENV_PATH.is_file():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _resolve_secret(env_name: str) -> str | None:
    val = (os.environ.get(env_name) or "").strip()
    if val:
        return val
    try:
        from scripts.security_agent_manager import get_security_agent

        got = get_security_agent().get_env_var(env_name)
        if got and str(got).strip():
            return str(got).strip()
    except Exception:
        pass
    return None


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body)
        except json.JSONDecodeError:
            parsed = {"error": err_body[:500]}
        return {"ok": False, "http_status": e.code, **parsed}
    except urllib.error.URLError as e:
        return {"ok": False, "error": "backend_unreachable", "detail": str(e.reason)}


def _configure_service(
    *,
    backend_base: str,
    service: str,
    api_key: str,
) -> dict[str, Any]:
    path = SETUP_PATHS[service]
    url = f"{backend_base.rstrip('/')}{path}"
    result = _http_json("POST", url, {"apiKey": api_key})
    ok = result.get("complete") is True or (
        isinstance(result.get("services"), dict)
        and isinstance(result["services"].get(service), dict)
        and result["services"][service].get("configured") is True
    )
    if result.get("ok") is False:
        ok = False
    return {
        "service": service,
        "ok": ok,
        "http_status": result.get("http_status"),
        "error": result.get("error"),
        "status_snapshot": result if isinstance(result, dict) else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto BigSet local credential setup (MKM → backend API)")
    ap.add_argument("--backend-url", default=os.environ.get("BIGSET_BACKEND_URL", "http://127.0.0.1:3501"))
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--skip-openrouter", action="store_true")
    ap.add_argument("--skip-tinyfish", action="store_true")
    ap.add_argument(
        "--free-tier",
        action="store_true",
        help="also run apply_bigset_free_tier_profile_v1.py (artifact only; restart bigset separately)",
    )
    ap.add_argument(
        "--azure-openrouter",
        action="store_true",
        help="use AZURE_OPENAI_API_KEY for BigSet openrouter slot (Azure v1 base URL)",
    )
    ap.add_argument(
        "--force-openrouter",
        action="store_true",
        help="re-POST openrouter key even if already configured",
    )
    args = ap.parse_args()

    _load_dotenv_quiet()
    if args.free_tier:
        from scripts.apply_bigset_free_tier_profile_v1 import main as apply_free_main

        apply_free_main()
    backend = args.backend_url.rstrip("/")

    health = _http_json("GET", f"{backend}/health")
    if health.get("status") != "ok":
        doc = {
            "schema": "bigset_local_credentials_setup_v1",
            "generated_at_utc": _now(),
            "ok": False,
            "error": "bigset_backend_not_healthy",
            "backend_url": backend,
            "health": health,
            "reproduce": "bigset start  # then re-run this script",
        }
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "bigset_backend_not_healthy"}, ensure_ascii=False))
        return 1

    before = _http_json("GET", f"{backend}/local-setup/status")
    steps: list[dict[str, Any]] = []

    for service, env_name in SERVICE_KEYS.items():
        if service == "openrouter" and args.skip_openrouter:
            steps.append({"service": service, "skipped": True, "reason": "flag"})
            continue
        if service == "tinyfish" and args.skip_tinyfish:
            steps.append({"service": service, "skipped": True, "reason": "flag"})
            continue

        svc_before = (before.get("services") or {}).get(service) or {}
        if svc_before.get("configured") and not (service == "openrouter" and args.force_openrouter):
            steps.append({"service": service, "skipped": True, "reason": "already_configured", "ok": True})
            continue

        if service == "openrouter" and args.azure_openrouter:
            secret = _resolve_secret("AZURE_OPENAI_API_KEY")
            env_name = "AZURE_OPENAI_API_KEY"
        else:
            secret = _resolve_secret(env_name)
        if not secret:
            steps.append(
                {
                    "service": service,
                    "ok": False,
                    "error": "secret_missing",
                    "env_name": env_name,
                    "hint": f"Register once: powershell -File scripts\\Invoke-LocalLock_v1.ps1 register {env_name}",
                }
            )
            continue

        step = _configure_service(backend_base=backend, service=service, api_key=secret)
        steps.append(step)

    after = _http_json("GET", f"{backend}/local-setup/status")
    complete = after.get("complete") is True
    all_steps_ok = all(s.get("ok") is not False for s in steps if not s.get("skipped"))

    doc = {
        "schema": "bigset_local_credentials_setup_v1",
        "generated_at_utc": _now(),
        "ok": complete and all_steps_ok,
        "research_only": True,
        "send_gate": "HOLD",
        "backend_url": backend,
        "setup_complete": complete,
        "status_before": before,
        "status_after": after,
        "steps": [
            {k: v for k, v in s.items() if k != "status_snapshot"} for s in steps
        ],
        "reproduce": "py scripts/configure_bigset_local_credentials_v1.py",
        "notes": {
            "openrouter_source": "OPENROUTER_API_KEY in .env or DPAPI",
            "tinyfish_source": "TINYFISH_API_KEY — one-time register if absent",
            "no_browser": True,
        },
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "setup_complete": complete,
                "artifact": str(args.artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
