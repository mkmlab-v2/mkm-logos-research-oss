#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.6, M:0.6}
# Balance: 91
# Purpose: Enforce MCP tool allowlist and required argument keys.
# Keywords: mcp, policy, allowlist, gate, security

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs/final/artifacts/mcp_tool_policy_v1.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/mcp_tool_policy_check_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--server", required=True)
    ap.add_argument("--tool-name", required=True)
    ap.add_argument("--args-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.policy_json.is_file():
        print(f"Missing policy-json: {args.policy_json}", file=sys.stderr)
        return 2
    if not args.args_json.is_file():
        print(f"Missing args-json: {args.args_json}", file=sys.stderr)
        return 2

    policy = json.loads(args.policy_json.read_text(encoding="utf-8"))
    payload = json.loads(args.args_json.read_text(encoding="utf-8"))
    allow = policy.get("allowlist", [])
    required_arg_keys = set(policy.get("required_arg_keys", []))
    deny_arg_patterns = [str(x) for x in policy.get("deny_arg_patterns", [])]
    scoped_deny = policy.get("server_tool_denylist", [])

    matched = None
    for row in allow:
        if not isinstance(row, dict):
            continue
        if row.get("server") == args.server and row.get("tool_name") == args.tool_name:
            matched = row
            break

    failures: list[str] = []
    if matched is None:
        failures.append("tool_not_allowlisted")
    else:
        for key in matched.get("required_keys", []):
            if key not in payload:
                failures.append(f"missing_required_key:{key}")

    for key in required_arg_keys:
        if key not in payload:
            failures.append(f"missing_global_required_key:{key}")

    for k, v in payload.items():
        blob = f"{k}={v}"
        for pat in deny_arg_patterns:
            if _safe_pattern(pat).search(blob):
                failures.append(f"deny_pattern_matched:{pat}")
        for row in scoped_deny:
            if not isinstance(row, dict):
                continue
            if row.get("server") != args.server or row.get("tool_name") != args.tool_name:
                continue
            for pat in row.get("deny_arg_patterns", []):
                p = str(pat)
                if _safe_pattern(p).search(blob):
                    failures.append(f"scoped_deny_pattern_matched:{p}")

    passed = len(failures) == 0
    out = {
        "schema": "mcp_tool_policy_check_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "server": args.server,
        "tool_name": args.tool_name,
        "pass": passed,
        "failures": failures,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

