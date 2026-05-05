from __future__ import annotations

import argparse
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforce slim .cursorrules from SSOT template.")
    parser.add_argument("--workspace-root", default="C:/workspace")
    parser.add_argument(
        "--template-path",
        default="docs/final/artifacts/cursorrules_slim_ssot_v1.txt",
    )
    parser.add_argument("--make-readonly", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)
    template = root / args.template_path
    target = root / ".cursorrules"

    if not template.exists():
        raise SystemExit(f"template not found: {template}")

    content = template.read_text(encoding="utf-8")
    if not content.endswith("\n"):
        content += "\n"

    if target.exists():
        try:
            target.chmod(0o666)
        except Exception:
            pass

    target.write_text(content, encoding="utf-8")

    if args.make_readonly:
        try:
            target.chmod(0o444)
        except Exception:
            # On Windows, chmod may not fully enforce readonly for all tools.
            pass

    print(f"enforced: {target}")
    print(f"bytes={target.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
