#!/usr/bin/env python3
"""LocalLock vault audit — identity vs DPAPI key names only (no secret values)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/mkm_community_accounts_registry_v1.json"
OUT = ROOT / "reports/local_lock_vault_audit_v1_latest.json"
VERIFY_GITHUB = ROOT / "scripts/verify_local_lock_github_secret_v1.ps1"


def _powershell_exe() -> str:
    """Prefer pwsh — Windows PowerShell 5 from Python subprocess may fail to load Security module."""
    for candidate in (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PowerShell/7/pwsh.exe",
        Path(r"C:\Program Files\PowerShell\7/pwsh.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return "powershell.exe"


def _parse_subprocess_json(stdout: str, stderr: str, exit_code: int) -> dict:
    text = stdout.strip()
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {
        "ok": False,
        "parse_error": True,
        "exit_code": exit_code,
        "stderr_head": stderr.strip()[:240] or None,
    }


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mkm_paths() -> tuple[Path, Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA not set (Windows-only audit).")
    base = Path(appdata) / "MKM"
    return base / "dev_identities_v1.json", base / "secret_store_v1.json"


def _keys_from_object(doc: dict | None) -> list[str]:
    if not isinstance(doc, dict):
        return []
    return sorted(doc.keys())


def _community_accounts() -> list[dict]:
    reg = _load_json(REGISTRY)
    if not isinstance(reg, dict):
        return []
    return [a for a in reg.get("accounts") or [] if isinstance(a, dict)]


def _legacy_env_keys(acct: dict) -> list[str]:
    keys: list[str] = []
    for field in ("dpapi_username_key", "dpapi_password_key", "dpapi_pat_key"):
        val = acct.get(field)
        if val:
            keys.append(str(val))
    return keys


def main() -> int:
    doc: dict = {
        "schema": "local_lock_vault_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "note": "Boolean/key names only — no secret values",
    }

    if sys.platform != "win32":
        doc["ok"] = False
        doc["error"] = "windows_only"
        doc["reproduce"] = "py scripts/check_local_lock_vault_audit_v1.py"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 1

    identity_path, secret_path = _mkm_paths()
    identities = _load_json(identity_path) or {}
    secrets = _load_json(secret_path) or {}

    identity_keys = _keys_from_object(identities if isinstance(identities, dict) else None)
    secret_keys = _keys_from_object(secrets if isinstance(secrets, dict) else None)
    identity_set = set(identity_keys)
    secret_set = set(secret_keys)

    paired = sorted(k for k in identity_keys if k in secret_set)
    identity_missing_secret = sorted(k for k in identity_keys if k not in secret_set)

    local_lock_orphans = sorted(
        k for k in secret_keys if k in identity_set and k not in paired
    )  # empty by definition
    _ = local_lock_orphans

    mkm_community_prefix = "MKM_COMMUNITY_"
    legacy_community_in_store = sorted(k for k in secret_keys if k.startswith(mkm_community_prefix))
    api_infra_orphans = sorted(
        k for k in secret_keys if k not in identity_set and not k.startswith(mkm_community_prefix)
    )

    community_rows: list[dict] = []
    gtm_ok = True
    for acct in _community_accounts():
        acct_id = str(acct.get("id") or "")
        deferred = str(acct.get("status") or "") == "deferred"
        row = {
            "id": acct_id,
            "platform": acct.get("platform"),
            "deferred": deferred,
            "identity_present": acct_id in identity_set,
            "local_lock_secret_present": acct_id in secret_set,
            "legacy_env_keys_in_store": {
                key: key in secret_set for key in _legacy_env_keys(acct)
            },
        }
        if not deferred:
            if not row["identity_present"] or not row["local_lock_secret_present"]:
                row["gtm_ready"] = False
                gtm_ok = False
            else:
                row["gtm_ready"] = True
        else:
            row["gtm_ready"] = None
        community_rows.append(row)

    github_verify: dict | None = None
    if VERIFY_GITHUB.is_file() and "github_mkmlab_v2" in secret_set:
        proc = subprocess.run(
            [
                _powershell_exe(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(VERIFY_GITHUB),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        github_verify = _parse_subprocess_json(proc.stdout, proc.stderr, proc.returncode)
        if github_verify and not github_verify.get("ok"):
            gtm_ok = False

    doc["stores"] = {
        "identity_path": str(identity_path),
        "secret_path": str(secret_path),
        "identity_count": len(identity_keys),
        "secret_count": len(secret_keys),
    }
    doc["local_lock"] = {
        "identity_keys": identity_keys,
        "paired_identity_and_secret": paired,
        "identity_missing_secret": identity_missing_secret,
    }
    doc["legacy_naming"] = {
        "mkm_community_keys_in_store": legacy_community_in_store,
        "note": "LocalLock uses identity id as secret key; legacy MKM_COMMUNITY_* keys are optional duplicates.",
    }
    doc["api_infra_secret_keys"] = {
        "count": len(api_infra_orphans),
        "keys": api_infra_orphans,
        "note": "Non-identity secrets (Gemini, SMTP, etc.) — security_agent_manager path; not LocalLock menu.",
    }
    doc["community_gtm"] = community_rows
    doc["github_pat_verify"] = github_verify
    doc["ok"] = gtm_ok and not identity_missing_secret
    doc["reproduce"] = "py scripts/check_local_lock_vault_audit_v1.py"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
