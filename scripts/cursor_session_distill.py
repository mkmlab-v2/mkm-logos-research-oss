# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.5, L:0.7, K:0.7, M:0.8}
# Balance: 85
# Purpose: Stage raw Cursor chat text and emit Obsidian-ready distill markdown (YAML frontmatter).
# Keywords: cursor, distill, vault, staging, archive
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = REPO_ROOT / "memory" / "obsidian_vault" / "cursor_distill"
STAGING_RAW_DIR = REPO_ROOT / "memory" / "obsidian_vault" / "_cursor_session_staging" / "raw"

CMD_PREFIXES = (
    "py ",
    "python ",
    "pip ",
    "git ",
    "npm ",
    "pnpm ",
    "npx ",
    "curl ",
    "powershell ",
    "pwsh ",
    "$ ",
)


def _read_bytes(path: Path | None) -> bytes:
    if path is None:
        return sys.stdin.buffer.read()
    return path.read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _first_summary_lines(text: str, n: int = 3, max_len: int = 220) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("```"):
            continue
        lines.append(s[:max_len] + ("…" if len(s) > max_len else ""))
        if len(lines) >= n:
            break
    while len(lines) < n:
        lines.append("(편집: 요약 문장 추가)")
    return lines


def _extract_commands(text: str, limit: int = 80) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for m in re.finditer(
        r"```(?:bash|sh|zsh|powershell|pwsh|cmd|shell)?\s*\n(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block = m.group(1).strip()
        for line in block.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s not in seen:
                seen.add(s)
                found.append(s)
            if len(found) >= limit:
                return found

    for line in text.splitlines():
        s = line.strip().strip("`")
        if not s:
            continue
        low = s.lower()
        if any(low.startswith(p.strip().lower()) for p in CMD_PREFIXES if p.strip()):
            if s not in seen:
                seen.add(s)
                found.append(s)
        elif low.startswith("run:") or low.startswith("execute:"):
            if s not in seen:
                seen.add(s)
                found.append(s)
        if len(found) >= limit:
            break
    return found


def _extract_paths(text: str, limit: int = 120) -> list[str]:
    patterns = [
        r"[Cc]:[/\\][^\n\r`\"'<>|]+",
        r"\b(?:scripts|projects|docs|tests|memory|\.cursor)/[a-zA-Z0-9_.\-/]+\.(?:py|ps1|md|json|yml|yaml|toml|tsx?|jsx?)\b",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            p = m.group(0).replace("/", "\\") if m.group(0).lower().startswith("c:") else m.group(0)
            p = p.strip(".,;:)\"'`")
            if len(p) < 4 or p in seen:
                continue
            seen.add(p)
            out.append(p)
            if len(out) >= limit:
                return sorted(out)
    return sorted(out)


def _escape_yaml_scalar(s: str) -> str:
    if not s:
        return '""'
    if any(c in s for c in ('\n', '"', ":", "#")) or s.strip() != s:
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _dump_frontmatter(fields: dict) -> str:
    lines = ['---']
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int | float):
            lines.append(f"{k}: {v}")
        elif isinstance(v, str):
            lines.append(f"{k}: {_escape_yaml_scalar(v)}")
        elif isinstance(v, Iterable) and not isinstance(v, str | dict):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {_escape_yaml_scalar(str(item))}")
        else:
            lines.append(f"{k}: {_escape_yaml_scalar(str(v))}")
    lines.append('---')
    return "\n".join(lines) + "\n"


def _default_out_path(session_slug: str) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-zA-Z0-9._가-힣-]+", "_", session_slug).strip("_") or "session"
    return DEFAULT_VAULT_DIR / f"{day}_cursor_distill_{slug}.md"


def build_markdown(
    *,
    raw_text: str,
    source_note: str,
    session_ref: str,
    three_lines: list[str],
    commands: list[str],
    paths: list[str],
    content_sha256: str,
    line_count: int,
    byte_len: int,
) -> str:
    fm = _dump_frontmatter(
        {
            "title": f"Cursor session distill {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "schema": "cursor_session_distill_v1",
            "distilled_utc": datetime.now(timezone.utc).isoformat(),
            "session_ref": session_ref,
            "source_note": source_note,
            "source_sha256": content_sha256,
            "source_lines": line_count,
            "source_bytes": byte_len,
            "tags": ["cursor-distill", "local-vault"],
            "share_ready": False,
        }
    )

    cmd_block = "\n".join(f"- `{c}`" for c in commands) or "- (none detected)"
    path_block = "\n".join(f"- `{p}`" for p in paths) or "- (none detected)"
    summary_block = "\n".join(f"- {s}" for s in three_lines)

    body = f"""
## Three-line summary (edit)

{summary_block}

## Commands (heuristic)

{cmd_block}

## Paths (heuristic)

{path_block}

## Facts lock (human)

- Verified paths/commands only; no guessed secrets or API values.

## Open risks / unknowns

- (편집)

## Next actions

- (편집)

## Raw excerpt (first 2KiB)

```
{raw_text[:2048]}{"…" if len(raw_text) > 2048 else ""}
```
""".strip()
    return fm + "\n" + body + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage Cursor chat/export text and write vault-ready distill markdown.",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Raw chat file (UTF-8). Default: stdin",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help=f"Output markdown (default: {DEFAULT_VAULT_DIR}/YYYY-MM-DD_cursor_distill_<slug>.md)",
    )
    parser.add_argument(
        "--session-slug",
        default="session",
        help="Filename slug when --out omitted",
    )
    parser.add_argument(
        "--session-ref",
        default="",
        help="External id (e.g. transcript path or Cursor chat id)",
    )
    parser.add_argument(
        "--write-raw-staging",
        action="store_true",
        help=f"Also copy full raw bytes under {STAGING_RAW_DIR}",
    )
    parser.add_argument(
        "--print-default-path",
        action="store_true",
        help="Print resolved default output path and exit",
    )
    args = parser.parse_args()

    if args.print_default_path:
        print(_default_out_path(args.session_slug))
        return 0

    if args.input is None and sys.stdin.isatty():
        parser.error("No --input and stdin is a TTY; pass -i file or pipe text in.")

    data = _read_bytes(args.input)
    try:
        raw_text = data.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = data.decode("utf-8", errors="replace")
    if raw_text.startswith("\ufeff"):
        raw_text = raw_text[1:]

    source_note = str(args.input.resolve()) if args.input else "stdin"
    h = _sha256(data)
    lines = raw_text.count("\n") + (1 if raw_text and not raw_text.endswith("\n") else 0)
    cmds = _extract_commands(raw_text)
    paths = _extract_paths(raw_text)
    three = _first_summary_lines(raw_text)

    out_path = args.out or _default_out_path(args.session_slug)
    md = build_markdown(
        raw_text=raw_text,
        source_note=source_note,
        session_ref=args.session_ref or source_note,
        three_lines=three,
        commands=cmds,
        paths=paths,
        content_sha256=h,
        line_count=lines,
        byte_len=len(data),
    )

    if args.write_raw_staging:
        STAGING_RAW_DIR.mkdir(parents=True, exist_ok=True)
        stem = out_path.stem
        raw_copy = STAGING_RAW_DIR / f"{stem}.raw.txt"
        raw_copy.write_bytes(data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(str(out_path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
