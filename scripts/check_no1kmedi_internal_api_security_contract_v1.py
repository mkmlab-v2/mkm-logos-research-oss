#!/usr/bin/env python3
"""Read-only Fact-Lock check: no1kmedi internal API auth contract + optional Security Agent probe.

Does not call HTTP by default. Never prints secret values.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify internal-api-auth paths and .env.example contract for no1kmedi admin API."
    )
    ap.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Monorepo root (default: parent of scripts/).",
    )
    ap.add_argument(
        "--security-agent-probe",
        action="store_true",
        help="Resolve NO1KMEDI_ADMIN_TOKEN via security_agent_manager (DPAPI); exit 0 if skip/unavailable.",
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    errors: list[str] = []

    auth_ts = root / "projects" / "no1kmedi" / "src" / "lib" / "internal-api-auth.ts"
    env_ex = root / "projects" / "no1kmedi" / ".env.example"
    if not auth_ts.is_file():
        errors.append(f"missing {auth_ts.relative_to(root)}")
    if not env_ex.is_file():
        errors.append(f"missing {env_ex.relative_to(root)}")
    else:
        text = env_ex.read_text(encoding="utf-8", errors="replace")
        if "NO1KMEDI_ADMIN_TOKEN" not in text:
            errors.append("projects/no1kmedi/.env.example missing NO1KMEDI_ADMIN_TOKEN")
        if "x-no1kmedi-admin-token" not in text:
            errors.append("projects/no1kmedi/.env.example missing header contract (x-no1kmedi-admin-token)")

    if errors:
        msg = "; ".join(errors)
        print(f"check_no1kmedi_internal_api_security_contract_v1 FAILED: {msg}", file=sys.stderr)
        return 1

    if args.security_agent_probe:
        scripts_dir = root / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            from security_agent_manager import get_security_agent  # type: ignore

            agent = get_security_agent()
            _ = agent.get_env_var("NO1KMEDI_ADMIN_TOKEN")
        except Exception as exc:
            print(f"security_agent_probe error: {exc}", file=sys.stderr)
            return 1

    print("check_no1kmedi_internal_api_security_contract_v1 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
