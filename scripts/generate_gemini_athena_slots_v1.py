#!/usr/bin/env python3
"""Generate Athena slot markdown answers via Gemini API (google-genai CLI wrapper).

Writes deterministic-ish filenames under docs/final/artifacts/vibe_runs_raw/athena_raw_outputs/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GEMINI_CLI = ROOT / "scripts" / "gemini_multimodal_batch.py"
RUNS_JSONL = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
EXTERNAL_JSONL = ROOT / "docs" / "final" / "artifacts" / "vibe_external_inputs_latest.jsonl"
EXTERNAL_ATTACH = ROOT / "docs" / "final" / "artifacts" / "vibe_external_inputs_latest.attach.txt"
PROMPTS_MD = ROOT / "docs" / "final" / "artifacts" / "vibe_prompt_set_v1.md"
OUT_DIR = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "athena_raw_outputs"

# Default chain when --model omitted: comma list in GEMINI_VIBE_SLOT_MODELS, else built-ins.
_DEFAULT_SLOT_MODELS = ("gemini-2.5-flash", "gemini-2.0-flash")
_MAX_ATTEMPTS_PER_MODEL = 5


def _slot_model_chain(cli_model: str) -> list[str]:
    """Explicit --model → single model only; else env or defaults (fallback order)."""
    if cli_model.strip():
        return [cli_model.strip()]
    raw = os.environ.get("GEMINI_VIBE_SLOT_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(_DEFAULT_SLOT_MODELS)


def _looks_transient(stderr_stdout: str) -> bool:
    e = stderr_stdout.lower()
    return any(
        x in e
        for x in (
            "500 internal",
            "503",
            "504",
            "429",
            "resource exhausted",
            "timeout",
            "timed out",
            "temporarily unavailable",
            "internal error has occurred",
            "try again",
        )
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def materialize_external_attachment() -> Path:
    """Write a text attachment for Gemini (avoid unsupported mime types like json/jsonl/octet-stream)."""
    rows = read_jsonl(EXTERNAL_JSONL)
    payload = {
        "schema": "vibe_external_inputs_bundle_v1",
        "source_jsonl": "docs/final/artifacts/vibe_external_inputs_latest.jsonl",
        "rows": rows,
    }
    EXTERNAL_ATTACH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return EXTERNAL_ATTACH


def parse_prompts(md_text: str) -> dict[str, str]:
    prompt_map: dict[str, str] = {}
    chunks = re.split(r"^## Prompt\s+\d+\s+-\s+", md_text, flags=re.MULTILINE)
    headers = re.findall(r"^## Prompt\s+\d+\s+-\s+(.+)$", md_text, flags=re.MULTILINE)
    for idx, title in enumerate(headers, start=1):
        body = chunks[idx] if idx < len(chunks) else ""
        pid = f"prompt_{idx:02d}"
        prompt_map[pid] = f"{title.strip()}\n\n{body.strip()}"
    return prompt_map


def summarize_external(rows: list[dict[str, Any]]) -> str:
    lines = []
    for row in rows[:30]:
        bucket = row.get("bucket")
        series = row.get("series")
        value = row.get("value")
        direction = row.get("direction")
        conf = row.get("confidence")
        lines.append(f"- {bucket}/{series}: value={value} dir={direction} conf={conf}")
    return "\n".join(lines) if lines else "- (no external rows)"


def build_system_instruction() -> str:
    return (
        "You are the Gemini runtime persona Athena for MKM operational briefing.\n"
        "Fact-Lock: do not invent repo paths/keys/artifacts; if unknown say UNKNOWN.\n"
        "Multi-lens language policy: use lenses only as commentary; final trading posture stays conservative.\n"
        "Hard bans: no exact price targets; decision must be HOLD|REDUCE|WATCH only.\n"
        "Output MUST match the exact markdown template provided by the user prompt."
    )


def build_user_prompt(prompt_context: str, external_blob: str, slot: str) -> str:
    return (
        f"[Slot] {slot}\n\n"
        "[External snapshot]\n"
        f"{external_blob}\n\n"
        "[Prompt definition]\n"
        f"{prompt_context}\n\n"
        "Write the answer using EXACTLY this markdown template (keep headings/lines):\n"
        f"# {slot}\n\n"
        "Runtime: Gemini JAMS (Athena persona)\n\n"
        "Final Action: HOLD|REDUCE|WATCH\n"
        "Confidence: 0.00-1.00\n"
        "Risk Flags: [tag1, tag2]\n\n"
        "Evidence pointers:\n"
        "- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl\n\n"
        "Rationale:\n"
        "- (<= 6 bullets)\n\n"
        "Notes:\n"
        "- Explicitly state uncertainties.\n"
    )


def run_gemini(
    models: list[str],
    timeout: int,
    temperature: float,
    thinking_budget: int,
    system: str,
    user: str,
    attachment: Path,
) -> str:
    """
    Call gemini_multimodal_batch research with thinking off by default (--thinking-budget 0)
    so models that do not support thinking do not 400. Retries transient errors; tries next model on failure.
    """
    last_err = ""
    for model in models:
        cmd: list[str] = [
            sys.executable,
            str(GEMINI_CLI),
            "research",
            "--model",
            model,
            "--thinking-budget",
            str(thinking_budget),
            "--timeout",
            str(timeout),
            "--temperature",
            str(temperature),
            "--system",
            system,
            "--file",
            str(attachment),
            "--prompt",
            user,
        ]
        for attempt in range(1, _MAX_ATTEMPTS_PER_MODEL + 1):
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
            if proc.returncode == 0 and (proc.stdout or "").strip():
                return proc.stdout
            err = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
            last_err = err or f"exit={proc.returncode}"
            if _looks_transient(err):
                time.sleep(min(20, 2 ** (attempt - 1)))
                continue
            break
    raise RuntimeError(last_err)


def validate_basic_md(text: str, slot_file: str) -> None:
    upper = text.upper()
    if slot_file.upper() not in text[:200].upper():
        # mild warning only
        pass
    if not re.search(r"\b(HOLD|REDUCE|WATCH)\b", upper):
        raise ValueError("missing decision token")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="",
        help="Optional model id override. If omitted, uses gemini_multimodal_batch.py default.",
    )
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=0,
        help="0=disable thinking (recommended for slot batch; avoids 400 on non-thinking models).",
    )
    parser.add_argument("--limit", type=int, default=0, help="If >0, only generate first N slots.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not GEMINI_CLI.is_file():
        raise FileNotFoundError(str(GEMINI_CLI))

    runs = read_jsonl(RUNS_JSONL)
    external_rows = read_jsonl(EXTERNAL_JSONL)
    external_blob = summarize_external(external_rows)
    attachment = materialize_external_attachment()

    prompt_map = {}
    if PROMPTS_MD.is_file():
        prompt_map = parse_prompts(PROMPTS_MD.read_text(encoding="utf-8"))

    system = build_system_instruction()
    models = _slot_model_chain(args.model)
    if not args.dry_run:
        print(f"[vibe-slots] model_chain={models} thinking_budget={args.thinking_budget}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n = 0
    for row in runs:
        pid = str(row.get("prompt_id"))
        rid = int(row.get("run_index"))
        slot_file = f"{pid}_run_{rid:02d}.md"
        out_path = OUT_DIR / slot_file

        ctx = prompt_map.get(pid, "(missing vibe_prompt_set_v1.md context)")
        user = build_user_prompt(ctx, external_blob, slot_file)

        if args.limit and n >= args.limit:
            break

        if args.dry_run:
            print(f"[dry-run] would_generate {slot_file}")
            n += 1
            continue

        text = run_gemini(
            models,
            args.timeout,
            args.temperature,
            args.thinking_budget,
            system,
            user,
            attachment,
        )
        validate_basic_md(text, slot_file)
        out_path.write_text(text.strip() + "\n", encoding="utf-8")
        print(f"written: {out_path}")
        n += 1

    print(f"generated_slots: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
