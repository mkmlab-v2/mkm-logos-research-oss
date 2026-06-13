#!/usr/bin/env python3
"""Turnstile Logpush CF user-token hygiene: probe, plan, optional API revoke.

No secrets printed. Parent needs User API Tokens Read+Write to --apply revokes.

  py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --dry-run
  py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --probe-token cfut_...
  py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --apply --keep-name MKM-turnstile-logpush-r2-v1
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    token_fingerprint,
)

ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
TARGET_NAME = "MKM-turnstile-logpush-r2-v1"
OUT = ROOT / "reports" / "turnstile_logpush_token_cleanup_v1_latest.json"
PLAN = ROOT / "docs" / "final" / "artifacts" / "turnstile_logpush_token_cleanup_plan_latest.md"

PARENT_KEYS = (
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "CLOUDFLARE_TURNSTILE_API_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "CLOUDFLARE_LOGPUSH_API_TOKEN",
)


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def _parent_tokens() -> list[tuple[str, str]]:
    import os

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for key in PARENT_KEYS:
        val = (
            _read_windows_user_env(key)
            or os.environ.get(key, "").strip()
            or _read_dotenv_key(key)
        ).strip().strip("<>").strip('"').strip("'")
        if not val or val in seen:
            continue
        seen.add(val)
        out.append((key, val))
    return out


def probe_logpush_token(tok: str) -> dict[str, Any]:
    dest = _read_dotenv_key("TURNSTILE_LOGPUSH_DESTINATION_CONF").strip()
    doc: dict[str, Any] = {"token_fingerprint": token_fingerprint(tok)}

    _, verify = _api(tok, "GET", "/user/tokens/verify")
    res = verify.get("result") if isinstance(verify.get("result"), dict) else {}
    doc["verify_ok"] = bool(verify.get("success"))
    doc["status"] = res.get("status")
    doc["token_id"] = res.get("id")

    checks: dict[str, Any] = {}
    for label, path in [
        ("list_jobs", f"/accounts/{ACCOUNT}/logpush/jobs"),
        ("turnstile_fields", f"/accounts/{ACCOUNT}/logpush/datasets/turnstile_events/fields"),
        ("turnstile_widgets", f"/accounts/{ACCOUNT}/challenges/widgets"),
        ("r2_buckets", f"/accounts/{ACCOUNT}/r2/buckets"),
    ]:
        _, pl = _api(tok, "GET", path)
        checks[label] = bool(pl.get("success"))

    if dest:
        _, pl = _api(tok, "POST", f"/accounts/{ACCOUNT}/logpush/validate/destination", {"destination_conf": dest})
        checks["validate_r2_dest"] = bool(pl.get("success"))

    body = {
        "name": "probe-turnstile-cleanup",
        "dataset": "turnstile_events",
        "destination_conf": dest or "r2://mkm-turnstile-logs/turnstile/{DATE}",
        "enabled": False,
        "output_options": {"field_names": ["Timestamp"], "timestamp_format": "rfc3339"},
    }
    _, pl = _api(tok, "POST", f"/accounts/{ACCOUNT}/logpush/jobs", body)
    if pl.get("success"):
        checks["create_turnstile_events"] = True
        jid = (pl.get("result") or {}).get("id")
        if jid:
            _api(tok, "DELETE", f"/accounts/{ACCOUNT}/logpush/jobs/{jid}")
    else:
        err = (pl.get("errors") or [{}])[0]
        checks["create_turnstile_events"] = False
        checks["create_error"] = err

    doc["checks"] = checks
    score = sum(1 for k, v in checks.items() if k != "create_error" and v is True)
    if checks.get("create_turnstile_events"):
        doc["readiness"] = "READY"
        doc["score"] = score
    elif str((checks.get("create_error") or {}).get("message", "")).find("exceeded max jobs") >= 0:
        doc["readiness"] = "PERMS_OK_PLAN_BLOCKED"
        doc["score"] = score
    elif not checks.get("turnstile_widgets"):
        doc["readiness"] = "MISSING_TURNSTILE"
        doc["score"] = score
    else:
        doc["readiness"] = "PARTIAL"
        doc["score"] = score
    return doc


def _list_user_tokens(parent: str) -> tuple[bool, list[dict[str, Any]], str]:
    _, pl = _api(parent, "GET", "/user/tokens")
    if not pl.get("success"):
        err = (pl.get("errors") or [{}])[0]
        return False, [], str(err.get("message") or "list_failed")
    rows = [r for r in (pl.get("result") or []) if isinstance(r, dict)]
    return True, rows, ""


def _write_plan(doc: dict[str, Any]) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Turnstile Logpush token cleanup plan",
        "",
        f"Generated: {doc.get('generated_at_utc')}",
        "",
        "## Situation",
        f"- Duplicate name in dashboard: `{TARGET_NAME}` (6+ rows on page 2)",
        f"- `.env` token fp: `{doc.get('env_token_fingerprint')}` readiness: `{doc.get('env_readiness')}`",
        "",
        "## Keep (target state)",
        "- **One** user token named `MKM-turnstile-logpush-r2-v1`",
        "- Permissions (all **Account** scope): Turnstile Edit, Logs Edit, Workers R2 Storage Edit",
        "",
        "## Manual cleanup (5 min — no API list permission on current parents)",
        "1. Open https://dash.cloudflare.com/profile/api-tokens → page **2**",
        f"2. Find all `{TARGET_NAME}` rows",
        "3. **Keep one** row that shows `Account.Turnstile` + `Account.Workers R2 Storage` + `+1` (Logs)",
        "4. On that row click **Roll** → copy new `cfut_...` once",
        "5. **Revoke** every other duplicate `MKM-turnstile-logpush-r2-v1` (5–6 rows)",
        "6. Revoke the row that shows only `Account.Logs` + `Account.Workers R2 Storage` (no Turnstile)",
        "7. Sync + verify:",
        "   ```powershell",
        "   py scripts/sync_cloudflare_logpush_token_to_env_v1.py --token cfut_...",
        "   py scripts/check_turnstile_logpush_auto_v1.py",
        "   ```",
        "",
        "## After READY token",
        "```powershell",
        "py scripts/provision_turnstile_logpush_r2_bundle_v1.py --assume-bucket-exists --apply",
        "```",
        "",
        "## Do NOT",
        "- Do not use prefill URL (causes Zone Logs bug + more duplicates)",
        "- Do not create new tokens until duplicates are revoked",
        "",
    ]
    PLAN.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Write cleanup plan + probe .env token.")
    ap.add_argument("--apply", action="store_true", help="Revoke duplicate named tokens via API (needs parent list/write).")
    ap.add_argument("--keep-id", default="", help="Token id to keep when --apply.")
    ap.add_argument("--keep-name", default=TARGET_NAME, help="Duplicate name to collapse.")
    ap.add_argument("--probe-token", default="", help="Probe a single cfut_ token (no print of secret).")
    args = ap.parse_args()

    if args.probe_token:
        doc = probe_logpush_token(args.probe_token.strip())
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        if doc.get("readiness") in {"READY", "PERMS_OK_PLAN_BLOCKED"}:
            return 0
        checks = doc.get("checks") or {}
        if doc.get("verify_ok") and checks.get("list_jobs") and checks.get("validate_r2_dest"):
            return 0
        return 2

    doc: dict[str, Any] = {
        "schema": "turnstile_logpush_token_cleanup_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_name": args.keep_name,
        "reproduce": "py scripts/cleanup_turnstile_logpush_cf_tokens_v1.py --dry-run",
    }

    env_tok = _read_dotenv_key("CLOUDFLARE_LOGPUSH_API_TOKEN").strip()
    if env_tok:
        env_probe = probe_logpush_token(env_tok)
        doc["env_token_fingerprint"] = env_probe.get("token_fingerprint")
        doc["env_token_id"] = env_probe.get("token_id")
        doc["env_readiness"] = env_probe.get("readiness")
        doc["env_checks"] = env_probe.get("checks")

    listed = False
    duplicates: list[dict[str, Any]] = []
    for parent_key, parent_tok in _parent_tokens():
        ok, rows, err = _list_user_tokens(parent_tok)
        attempt = {"parent_key": parent_key, "parent_fp": token_fingerprint(parent_tok), "list_ok": ok, "error": err}
        if ok:
            listed = True
            dups = [r for r in rows if str(r.get("name") or "") == args.keep_name]
            attempt["duplicate_count"] = len(dups)
            attempt["duplicate_ids"] = [r.get("id") for r in dups]
            duplicates = dups
            doc["list_parent"] = parent_key
        doc.setdefault("parent_attempts", []).append(attempt)
        if ok:
            break

    doc["duplicate_count"] = len(duplicates)
    doc["duplicate_ids"] = [r.get("id") for r in duplicates]

    if args.apply:
        if not listed:
            doc["decision"] = "BLOCKED_NO_LIST_PERMISSION"
            doc["human_gate"] = (
                "No parent token can list/revoke user API tokens. "
                "Follow manual steps in turnstile_logpush_token_cleanup_plan_latest.md"
            )
            OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            _write_plan(doc)
            print(json.dumps(doc, indent=2, ensure_ascii=False))
            return 1

        keep_id = args.keep_id.strip() or (doc.get("env_token_id") or "")
        if not keep_id:
            doc["decision"] = "BLOCKED_NO_KEEP_ID"
            OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            print(json.dumps(doc, indent=2, ensure_ascii=False))
            return 1

        parent_key, parent_tok = doc["list_parent"], next(t for k, t in _parent_tokens() if k == doc["list_parent"])
        revoked: list[str] = []
        for row in duplicates:
            tid = str(row.get("id") or "")
            if not tid or tid == keep_id:
                continue
            _, pl = _api(parent_tok, "DELETE", f"/user/tokens/{tid}")
            if pl.get("success"):
                revoked.append(tid)
        doc["revoked_ids"] = revoked
        doc["kept_id"] = keep_id
        doc["decision"] = "REVOKED_DUPLICATES" if revoked else "NOTHING_TO_REVOKE"

    elif doc.get("env_readiness") == "READY":
        doc["decision"] = "ENV_TOKEN_OK_MANUAL_DEDUP_ONLY"
    elif doc.get("env_readiness") == "MISSING_TURNSTILE":
        doc["decision"] = "ENV_TOKEN_WRONG_PICK_TURNSTILE_ROW_AND_ROLL"
    else:
        doc["decision"] = "MANUAL_CLEANUP_REQUIRED"

    _write_plan(doc)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0 if doc["decision"] in {"ENV_TOKEN_OK_MANUAL_DEDUP_ONLY", "REVOKED_DUPLICATES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
