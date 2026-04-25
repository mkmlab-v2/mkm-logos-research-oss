#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BLOCK_PATTERNS = [
    r"\bbitsandbytes\b",
    r"\bautoawq\b",
    r"\bawq\b",
    r"\bgptq\b",
    r"\bquanto\b",
    r"\bquantization_config\b",
    r"\bload_in_(4|8)bit\b",
    r"\bfp8\b",
    r"\bint4\b",
]

DEFAULT_SCAN_DIRS = [
    "projects/bitcoin-trading/src",
    "scripts",
]

ALLOWED_FILE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml"}

# B-track / isolated training entrypoints (explicitly not backend fact-engine).
# Basename skip avoids CI drift when path-based --skip-regex does not match every runner layout.
REVIEWED_ISOLATED_LLM_TRAIN_SCRIPTS = frozenset(
    {
        "train_mkm_prophecy_lora_unsloth.py",
        "run_rag_turboquant_poc_template.py",
    }
)


def _iter_files(root: Path, scan_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in scan_dirs:
        base = (root / rel).resolve()
        if not base.exists() or not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in ALLOWED_FILE_EXTS:
                files.append(p)
    return files


def _should_skip(path: Path, skip_patterns: list[re.Pattern[str]]) -> bool:
    normalized = path.as_posix()
    return any(p.search(normalized) for p in skip_patterns)


def _is_reviewer_skip_script(root: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if len(rel.parts) < 2 or rel.parts[0] != "scripts":
        return False
    return rel.name in REVIEWED_ISOLATED_LLM_TRAIN_SCRIPTS


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when LLM quantization-specific dependencies/configs are introduced "
            "into protected backend fact-engine code."
        )
    )
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--scan-dir",
        action="append",
        default=[],
        help="Relative directory to scan (repeatable). Defaults are applied when omitted.",
    )
    parser.add_argument(
        "--skip-regex",
        action="append",
        default=[
            r"/tests?/",
            r"/docs/",
            r"/reports/",
            r"/data/",
            r"/\.cursor/",
        ],
        help="Regex for file paths that should be ignored (repeatable).",
    )
    parser.add_argument(
        "--allow-regex",
        action="append",
        default=[],
        help=(
            "Regex for text patterns to allow even if blocked. "
            "Use only for explicit, reviewed exceptions."
        ),
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    scan_dirs = args.scan_dir if args.scan_dir else DEFAULT_SCAN_DIRS
    skip_patterns = [re.compile(p) for p in args.skip_regex]
    blocked = [re.compile(p, flags=re.IGNORECASE) for p in BLOCK_PATTERNS]
    allow_patterns = [re.compile(p, flags=re.IGNORECASE) for p in args.allow_regex]

    violations: list[tuple[Path, int, str, str]] = []
    for path in _iter_files(root, scan_dirs):
        if _is_reviewer_skip_script(root, path):
            continue
        if _should_skip(path, skip_patterns):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, line in enumerate(content.splitlines(), start=1):
            for bp in blocked:
                if bp.search(line):
                    if any(ap.search(line) for ap in allow_patterns):
                        continue
                    violations.append((path, idx, bp.pattern, line.strip()))
                    break

    if violations:
        print("Quantization guard FAILED: forbidden patterns found in protected backend paths.")
        for path, line_no, pattern, line in violations:
            rel = path.relative_to(root).as_posix()
            print(f"- {rel}:{line_no} matched `{pattern}` -> {line}")
        print(
            "\nPolicy: backend fact-engine code must stay deterministic/high-precision. "
            "Quantization belongs only to frontend LLM or isolated RAG lanes."
        )
        return 1

    print("Quantization guard PASSED: no forbidden quantization patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
