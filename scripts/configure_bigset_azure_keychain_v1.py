#!/usr/bin/env python3
"""Inject Azure OpenAI API key into BigSet local credential store (bypass OpenRouter /key verify).

BigSet local-setup POST verifies against OPENROUTER_BASE_URL/key — Azure returns 404.
Local mode resolveCredential reads OS keychain/file first; this script writes the Azure key
directly via the same @napi-rs/keyring account BigSet uses.

B-track · send_gate HOLD · no secrets logged.

Reproducible:
  py scripts/configure_bigset_azure_keychain_v1.py
  py scripts/configure_bigset_azure_keychain_v1.py --home C:\\Users\\PRO\\.bigset
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_azure_keychain_v1_latest.json"
KEYCHAIN_SERVICE = "ai.bigset.local-credentials"
DEFAULT_HOME = Path.home() / ".bigset"

NODE_SET_SNIPPET = r"""
const { createHash } = require("node:crypto");
const { Entry } = require("@napi-rs/keyring");
const home = process.env.BIGSET_HOME;
const apiKey = process.env.BIGSET_INJECT_API_KEY;
if (!home || !apiKey) {
  console.error(JSON.stringify({ ok: false, error: "missing_env" }));
  process.exit(2);
}
const ws = "bigset-" + createHash("sha256").update(home).digest("hex").slice(0, 16);
const account = `${ws}:openrouter`;
new Entry(process.env.BIGSET_KEYCHAIN_SERVICE || "ai.bigset.local-credentials", account).setPassword(apiKey);
console.log(JSON.stringify({ ok: true, keychainAccount: account, storage: "OS keychain" }));
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_azure_key() -> str | None:
    from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet

    load_dotenv_quiet()
    key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    if key:
        return key
    try:
        from scripts.security_agent_manager import get_security_agent

        got = get_security_agent().get_env_var("AZURE_OPENAI_API_KEY")
        if got and str(got).strip():
            return str(got).strip()
    except Exception:
        pass
    return None


def _find_keyring_module() -> Path | None:
    candidates = [
        Path(os.environ.get("BIGSET_NPM_ROOT", ""))
        / "node_modules"
        / "@adamexu"
        / "bigset"
        / "node_modules"
        / "@napi-rs"
        / "keyring",
        Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@adamexu" / "bigset" / "node_modules" / "@napi-rs" / "keyring",
        Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@tiny-fish" / "bigset" / "node_modules" / "@napi-rs" / "keyring",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def inject_azure_keychain(*, home: Path, azure_key: str) -> dict:
    keyring_dir = _find_keyring_module()
    env = {
        **os.environ,
        "BIGSET_HOME": str(home.resolve()),
        "BIGSET_INJECT_API_KEY": azure_key,
        "BIGSET_KEYCHAIN_SERVICE": KEYCHAIN_SERVICE,
        "NODE_PATH": str(keyring_dir.parent.parent) if keyring_dir else "",
    }
    proc = subprocess.run(
        ["node", "-e", NODE_SET_SNIPPET],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    try:
        payload = json.loads(stdout.splitlines()[-1]) if stdout else {}
    except json.JSONDecodeError:
        payload = {"ok": False, "error": "node_parse_failed", "stdout_tail": stdout[-300:], "stderr_tail": stderr[-300:]}
    if proc.returncode != 0 and payload.get("ok") is not True:
        payload.setdefault("ok", False)
        payload["exit_code"] = proc.returncode
        if stderr and "Cannot find module" in stderr:
            payload["error"] = "keyring_module_missing"
            payload["hint"] = "npm install -g @adamexu/bigset"
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="BigSet Azure key → local keychain (skip OpenRouter verify)")
    ap.add_argument("--home", type=Path, default=Path(os.environ.get("BIGSET_HOME", DEFAULT_HOME)))
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    azure_key = _resolve_azure_key()
    if not azure_key:
        doc = {
            "schema": "bigset_azure_keychain_v1",
            "generated_at_utc": _now(),
            "ok": False,
            "error": "AZURE_OPENAI_API_KEY_missing",
            "reproduce": "py scripts/configure_bigset_azure_keychain_v1.py",
        }
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "AZURE_OPENAI_API_KEY_missing"}, ensure_ascii=False))
        return 1

    result = inject_azure_keychain(home=args.home, azure_key=azure_key)
    doc = {
        "schema": "bigset_azure_keychain_v1",
        "generated_at_utc": _now(),
        "ok": result.get("ok") is True,
        "research_only": True,
        "send_gate": "HOLD",
        "bigset_home": str(args.home.resolve()),
        "keychain_account": result.get("keychainAccount"),
        "storage": result.get("storage"),
        "error": result.get("error"),
        "hint": result.get("hint"),
        "reproduce": "py scripts/configure_bigset_azure_keychain_v1.py && powershell -File scripts\\Invoke-BigSetAzureStart_v1.ps1",
        "notes": "Restart bigset backend after keychain inject so OPENROUTER_BASE_URL=Azure is loaded.",
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "keychain_account": doc.get("keychain_account"), "artifact": str(args.artifact.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
