#!/usr/bin/env python3
"""
MKM System2 Self-Correction Gate MVP v1 — output-hold + deterministic validate loop.

Serial roles (no LangGraph): generate -> validate (SSOT/rules) -> arbitrate (conservative).
Week-1 default: dry_run=True (no LLM). Week-2: optional meta-layer validate + memory/Vertex staging on pass.

  py scripts/mkm_system2_self_correction_gate_mvp_v1.py run --draft-file path.txt
  py scripts/run_mkm_system2_self_correction_gate_chain_v1.py --draft-file path.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_SCHEMA = (
    REPO_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "schemas"
    / "mkm_system2_self_correction_gate_mvp_v1.schema.json"
)
DEFAULT_OUT = REPO_ROOT / "reports" / "mkm_system2_self_correction_gate_mvp_v1_latest.json"
DEFAULT_PASSED_LOG = REPO_ROOT / "reports" / "mkm_system2_self_correction_gate_passed_v1.jsonl"
DEFAULT_VERTEX_STAGING = REPO_ROOT / "reports" / "mkm_system2_vertex_staging_v1.jsonl"
DEFAULT_PROMOTION_OUT = REPO_ROOT / "reports" / "mkm_system2_memory_promotion_candidate_v1_latest.json"
DEFAULT_META_LAYER_SCHEMA = (
    REPO_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "schemas"
    / "mkm_meta_layer_turn_envelope_v1.schema.json"
)
DEFAULT_MISSION_LOG = REPO_ROOT / "MISSION_LOG.md"
DEFAULT_CENTRAL = REPO_ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"

BOUNDARY_ACK = (
    "B-track/research_only; no Track A/live-trading auto-merge; human sign-off required for production."
)

# Deterministic validate rules (role 2)
_GHOST_METRIC_RES = [
    re.compile(r"\b\d+\.?\d*\s*%\b"),
    re.compile(r"\b(hit_rate|ROI|latency_ms|coverage)\s*[:=]\s*[\d.]+", re.I),
    re.compile(r"\b\d+\s*ms\b", re.I),
]
_HYPO_LEAK_RES = [
    re.compile(r"\[HYPO\].{0,120}(실매매|live trading|Track A\s*승격|combined_all_passed\s*GO)", re.I | re.S),
    re.compile(r"(실매매\s*GO|live\s*order).{0,80}\[HYPO\]", re.I | re.S),
]
_B_TO_A_RES = [
    re.compile(r"B-track.{0,40}Track A", re.I),
    re.compile(r"research_only.{0,40}(실매매|live)", re.I),
]
_LOGOS_GATING_RES = [
    re.compile(r"성경.{0,40}(하락|상승).{0,40}(예언|확정|단정)", re.I),
    re.compile(r"Logos.{0,40}(bearish|bullish).{0,40}(trigger|GO)", re.I),
]
_LIVE_PROMOTION_RES = re.compile(
    r"Track A\s*승격|실매매\s*GO|live trading\s*GO|combined_all_passed\s*GO",
    re.I,
)
_LIVE_PROMOTION_SAFE_RES = re.compile(r"확인 필요|합선 금지|research_only|human sign-off", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"expected JSON object: {path}")
    return doc


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _allowed_corpus(field_context: dict[str, Any] | None, extra_text: str = "") -> str:
    parts: list[str] = [extra_text]
    if field_context:
        parts.append(json.dumps(field_context, ensure_ascii=False))
        for key in ("allowed_fields", "fields", "values"):
            block = field_context.get(key)
            if isinstance(block, dict):
                parts.append(json.dumps(block, ensure_ascii=False))
                for k, v in block.items():
                    parts.append(f"{k}={v}")
                    parts.append(f"{k}: {v}")
            elif isinstance(block, list):
                parts.append(" ".join(str(x) for x in block))
    return "\n".join(parts)


def _metric_token_allowed(token: str, corpus: str) -> bool:
    if token in corpus:
        return True
    m = re.match(r"(\w+)\s*[:=]\s*([\d.]+)", token, re.I)
    if not m:
        return False
    key, val = m.group(1), m.group(2)
    return key.lower() in corpus.lower() and val in corpus


def _collect_sources(
    mission_log: Path | None,
    central: Path | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kind, path in (("mission_log", mission_log), ("central", central)):
        if path is None:
            continue
        out.append({"kind": kind, "path": str(path), "present": path.is_file()})
    return out


def validate_draft(
    draft: str,
    *,
    field_context: dict[str, Any] | None = None,
    corpus_extra: str = "",
) -> list[str]:
    """Role 2 — deterministic fact/rail checks. Empty list == pass."""
    errors: list[str] = []
    text = draft.strip()
    if not text:
        errors.append("empty_draft")
        return errors

    corpus = _allowed_corpus(field_context, corpus_extra)

    for pat in _HYPO_LEAK_RES:
        if pat.search(text):
            errors.append("hypo_leak_to_track_a_or_live")

    if _LIVE_PROMOTION_RES.search(text) and not _LIVE_PROMOTION_SAFE_RES.search(text):
        errors.append("live_promotion_language")

    for pat in _B_TO_A_RES:
        if pat.search(text):
            errors.append("btrack_to_track_a_or_live_merge")

    for pat in _LOGOS_GATING_RES:
        if pat.search(text) and "[NON_GATING]" not in text:
            errors.append("logos_gating_without_NON_GATING")

    for pat in _GHOST_METRIC_RES:
        for m in pat.finditer(text):
            token = m.group(0)
            if not _metric_token_allowed(token, corpus):
                errors.append(f"ghost_metric:{token}")
                break

    if "[HYPO]" in text and re.search(r"\b\d+\.?\d*\s*%\b", text):
        for m in re.finditer(r"\b\d+\.?\d*\s*%\b", text):
            if m.group(0) not in corpus:
                errors.append(f"hypo_with_unsourced_percent:{m.group(0)}")
                break

    return errors


def arbitrate(*, validate_errors: list[str]) -> dict[str, Any]:
    """Role 3 — conservative decision from validate outcome only."""
    if validate_errors:
        return {
            "decision": "HOLD",
            "principle": "most_conservative_wins",
            "reason": ";".join(validate_errors[:5]),
        }
    return {
        "decision": "GO",
        "principle": "most_conservative_wins",
        "reason": "validate_pass",
    }


def attempt_deterministic_repair(draft: str, errors: list[str]) -> str:
    """Dry-run repair: strip/replace only what rules flagged (no LLM)."""
    out = draft
    if any(e.startswith("logos_gating") for e in errors):
        if "[NON_GATING]" not in out:
            out = "[NON_GATING] " + out
    if "hypo_leak_to_track_a_or_live" in errors or "btrack_to_track_a_or_live_merge" in errors or "live_promotion_language" in errors:
        out = re.sub(
            r"(실매매\s*GO|live trading|Track A\s*승격)",
            "확인 필요(Track A/실매매 자동 합선 금지)",
            out,
            flags=re.I,
        )
    for err in errors:
        if err.startswith("ghost_metric:") or err.startswith("hypo_with_unsourced_percent:"):
            token = err.split(":", 1)[1]
            out = out.replace(token, "확인 필요")
    return out


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _gemini_api_key() -> str | None:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def _gemini_repair_enabled(explicit_flag: bool) -> bool:
    return explicit_flag or _env_truthy("MKM_SYSTEM2_GEMINI_REPAIR")


def _ollama_repair_enabled(explicit_flag: bool) -> bool:
    return explicit_flag or _env_truthy("MKM_SYSTEM2_OLLAMA_REPAIR")


def _ollama_fallback_after_gemini() -> bool:
    """When Gemini fails, try local Ollama before deterministic repair (default on)."""
    raw = os.getenv("MKM_SYSTEM2_OLLAMA_FALLBACK_AFTER_GEMINI", "1")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _ollama_chat_base_url() -> str:
    host = (
        os.getenv("MKM_SYSTEM2_OLLAMA_BASE_URL")
        or os.getenv("OLLAMA_HOST")
        or "http://127.0.0.1:11434"
    ).strip().rstrip("/")
    if host.endswith("/v1"):
        return host
    return host + "/v1"


def _build_repair_prompt(
    draft: str,
    errors: list[str],
    *,
    field_context: dict[str, Any] | None = None,
) -> str:
    allowed = _allowed_corpus(field_context, "")
    return f"""You are MKM System2 draft repair (research/ops only; not live trading).
Fix the draft to resolve validation errors. Rules:
- Do NOT invent numbers, %, ms, hit_rate, ROI, coverage.
- Do NOT use Track A 승격, 실매매 GO, or live trading GO language.
- Keep [HYPO] out of Track A / live trading sentences.
- Add [NON_GATING] if Logos/Biblical gating language appears.
- Prefer "확인 필요(Track A/실매매 자동 합선 금지)" over promotion language.
- Output plain text only (no markdown fences).

Validation errors:
{json.dumps(errors, ensure_ascii=False)}

Allowed corpus excerpt (only cite if already here):
{allowed[:6000]}

Draft:
{draft[:8000]}
"""


def attempt_gemini_repair(
    draft: str,
    errors: list[str],
    *,
    field_context: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Optional Gemini rewrite; falls back to deterministic repair without network/key."""
    meta: dict[str, Any] = {"engine": "gemini", "ok": False}
    key = _gemini_api_key()
    if not key:
        meta["fallback"] = "deterministic_no_key"
        return attempt_deterministic_repair(draft, errors), meta

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        meta["fallback"] = f"deterministic_import_error:{exc}"
        return attempt_deterministic_repair(draft, errors), meta

    model = os.getenv("MKM_SYSTEM2_GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    timeout_sec = int(os.getenv("MKM_SYSTEM2_GEMINI_TIMEOUT_SEC", "90") or "90")
    prompt = _build_repair_prompt(draft, errors, field_context=field_context)
    try:
        timeout_ms = max(10_000, timeout_sec * 1000)
        client = genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(timeout=timeout_ms))
        resp = client.models.generate_content(
            model=model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(temperature=0.1),
        )
        text = (resp.text or "").strip()
        if not text:
            meta["fallback"] = "deterministic_empty_gemini_response"
            return attempt_deterministic_repair(draft, errors), meta
        meta.update({"ok": True, "model": model})
        return text, meta
    except Exception as exc:
        meta["fallback"] = f"deterministic_gemini_error:{type(exc).__name__}"
        return attempt_deterministic_repair(draft, errors), meta


def attempt_ollama_repair(
    draft: str,
    errors: list[str],
    *,
    field_context: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Local Ollama OpenAI-compatible chat repair; falls back to deterministic on failure."""
    meta: dict[str, Any] = {"engine": "ollama", "ok": False}
    base = _ollama_chat_base_url()
    model = (
        os.getenv("MKM_SYSTEM2_OLLAMA_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or "gemma4:e2b"
    ).strip() or "gemma4:e2b"
    timeout_sec = int(os.getenv("MKM_SYSTEM2_OLLAMA_TIMEOUT_SEC", "120") or "120")
    prompt = _build_repair_prompt(draft, errors, field_context=field_context)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "stream": False,
    }
    req = urllib.request.Request(
        url=base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(10, timeout_sec)) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        choices = payload.get("choices") or []
        text = ""
        if choices:
            text = str((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            meta["fallback"] = "deterministic_empty_ollama_response"
            return attempt_deterministic_repair(draft, errors), meta
        meta.update({"ok": True, "model": model, "base_url": base})
        return text, meta
    except urllib.error.URLError as exc:
        meta["fallback"] = f"deterministic_ollama_unreachable:{exc.reason}"
        return attempt_deterministic_repair(draft, errors), meta
    except Exception as exc:
        meta["fallback"] = f"deterministic_ollama_error:{type(exc).__name__}"
        return attempt_deterministic_repair(draft, errors), meta


def attempt_rule_guided_live_repair(
    draft: str,
    errors: list[str],
    *,
    field_context: dict[str, Any] | None = None,
    gemini_repair: bool = False,
    ollama_repair: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Live path: Gemini -> Ollama (optional) -> deterministic repair."""
    use_gemini = _gemini_repair_enabled(gemini_repair)
    use_ollama = _ollama_repair_enabled(ollama_repair)
    chain: list[dict[str, Any]] = []

    if use_gemini:
        text, meta = attempt_gemini_repair(draft, errors, field_context=field_context)
        chain.append(meta)
        if meta.get("ok"):
            meta["chain"] = chain
            return text, meta
        if use_ollama or _ollama_fallback_after_gemini():
            text, ometa = attempt_ollama_repair(draft, errors, field_context=field_context)
            chain.append(ometa)
            if ometa.get("ok"):
                ometa["chain"] = chain
                return text, ometa
        meta["chain"] = chain
        return text, meta

    if use_ollama:
        text, meta = attempt_ollama_repair(draft, errors, field_context=field_context)
        chain.append(meta)
        if meta.get("ok"):
            meta["chain"] = chain
            return text, meta
        meta["chain"] = chain
        return text, meta

    repaired = attempt_deterministic_repair(draft, errors)
    return repaired, {"engine": "deterministic", "ok": True}


def generate_draft(
    *,
    draft: str,
    field_context: dict[str, Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Role 1 — week-1 uses supplied draft; live uses rule-guided repair on retry."""
    return {
        "mode": "passthrough_dry_run" if dry_run else "rule_guided_live_v1",
        "field_keys": sorted((field_context or {}).keys()),
        "draft_chars": len(draft),
    }


def run_gate(
    draft: str,
    *,
    field_context: dict[str, Any] | None = None,
    corpus_extra: str = "",
    max_retries: int = 2,
    dry_run: bool = True,
    gemini_repair: bool = False,
    ollama_repair: bool = False,
    mission_log: Path | None = DEFAULT_MISSION_LOG,
    central: Path | None = DEFAULT_CENTRAL,
) -> dict[str, Any]:
    sources = _collect_sources(mission_log, central)
    attempts: list[dict[str, Any]] = []
    current = draft
    retry_count = 0
    failed_reasons: list[str] = []
    final_errors: list[str] = []

    gen_meta = generate_draft(draft=current, field_context=field_context, dry_run=dry_run)
    if gemini_repair and not dry_run:
        gen_meta["gemini_repair"] = True
    if ollama_repair and not dry_run:
        gen_meta["ollama_repair"] = True

    for attempt in range(1, max_retries + 2):
        errors = validate_draft(current, field_context=field_context, corpus_extra=corpus_extra)
        attempts.append(
            {
                "attempt": attempt,
                "validate_errors": errors,
                "draft_excerpt": current[:240],
            }
        )
        if not errors:
            final_errors = []
            failed_reasons = []
            break

        final_errors = errors
        failed_reasons = errors
        if attempt > max_retries:
            retry_count = max_retries
            break

        retry_count = attempt
        repair_meta: dict[str, Any]
        if dry_run:
            current = attempt_deterministic_repair(current, errors)
            repair_meta = {"engine": "deterministic", "ok": True}
        else:
            current, repair_meta = attempt_rule_guided_live_repair(
                current,
                errors,
                field_context=field_context,
                gemini_repair=gemini_repair,
                ollama_repair=ollama_repair,
            )
        attempts[-1]["repair"] = repair_meta

    action = arbitrate(validate_errors=final_errors)
    all_pass = len(final_errors) == 0

    return {
        "schema": "mkm_system2_self_correction_gate_mvp_v1",
        "generated_at_utc": _utc_now(),
        "dry_run": dry_run,
        "all_pass": all_pass,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "failed_reasons": failed_reasons,
        "sources": sources,
        "roles": {
            "generate": gen_meta,
            "validate": {"engine": "deterministic_rules_v1", "error_count": len(final_errors)},
            "arbitrate": action,
        },
        "final_action": action,
        "draft_final": current if all_pass else current[:500],
        "attempts": attempts,
        "boundary_ack": BOUNDARY_ACK,
    }


def validate_report(doc: dict[str, Any], schema_path: Path | None = None) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("jsonschema package required") from e
    schema = _load_json(schema_path or DEFAULT_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def append_passed_log(doc: dict[str, Any], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "mkm_system2_self_correction_gate_passed_v1",
        "recorded_at_utc": _utc_now(),
        "source_tag": "system2_gate_mvp_v1",
        "dry_run": doc.get("dry_run"),
        "draft_excerpt": (doc.get("draft_final") or "")[:280],
        "sources": doc.get("sources"),
        "boundary_ack": BOUNDARY_ACK,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_vertex_staging_row(doc: dict[str, Any], staging_path: Path) -> None:
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "mkm_system2_vertex_staging_row_v1",
        "recorded_at_utc": _utc_now(),
        "source_tag": "system2_gate_mvp_v1",
        "text": (doc.get("draft_final") or "")[:4000],
        "gate_all_pass": doc.get("all_pass"),
        "human_sign_off_required": True,
        "vertex_upload": "deferred_manual_or_Run-AgentSearchCorpusUploadAndImport_v1",
        "boundary_ack": BOUNDARY_ACK,
    }
    with staging_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_memory_promotion_candidate(doc: dict[str, Any], *, gate_report_path: str) -> dict[str, Any]:
    return {
        "schema": "mkm_system2_memory_promotion_candidate_v1",
        "generated_at_utc": _utc_now(),
        "eligible": bool(doc.get("all_pass")),
        "gate_report_path": gate_report_path,
        "draft_excerpt": (doc.get("draft_final") or "")[:400],
        "promotion_targets": {
            "athena_checkpoint": {"requires_flag": "--write-checkpoint", "human_sign_off_required": True},
            "passed_log_jsonl": str(DEFAULT_PASSED_LOG),
            "vertex_staging_jsonl": str(DEFAULT_VERTEX_STAGING),
            "meta_layer_agent_decisions_log": "reports/agent_decisions_log.jsonl",
        },
        "human_sign_off_required": True,
        "boundary_ack": BOUNDARY_ACK,
    }


def validate_meta_layer_envelope(
    envelope_path: Path,
    *,
    schema_path: Path | None = None,
    append_log: bool = False,
    mission_id: str = "system2-gate-mvp",
    actor: str = "mkm_system2_self_correction_gate_mvp_v1",
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "mkm_meta_layer_envelope_v1.py"),
    ]
    if append_log:
        cmd.extend(
            [
                "append",
                "--json-file",
                str(envelope_path),
                "--mission-id",
                mission_id,
                "--actor",
                actor,
                "--note",
                "system2_gate_pass_serial_hook",
            ]
        )
    else:
        cmd.extend(["validate", "--json-file", str(envelope_path)])
    if schema_path:
        cmd.extend(["--schema", str(schema_path)])
    cp = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "")[-400:],
    }


def apply_post_pass_hooks(
    doc: dict[str, Any],
    *,
    gate_report_path: Path,
    meta_layer_json: Path | None = None,
    append_meta_layer_log: bool = False,
    vertex_staging_path: Path | None = None,
    promotion_out_path: Path | None = None,
) -> dict[str, Any]:
    hooks: dict[str, Any] = {"applied": doc.get("all_pass") is True}
    if not doc.get("all_pass"):
        hooks["skipped_reason"] = "gate_not_all_pass"
        return hooks

    if promotion_out_path is not None:
        promo = build_memory_promotion_candidate(doc, gate_report_path=str(gate_report_path))
        promotion_out_path.parent.mkdir(parents=True, exist_ok=True)
        promotion_out_path.write_text(json.dumps(promo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hooks["memory_promotion"] = {"ok": True, "path": str(promotion_out_path)}

    if vertex_staging_path is not None:
        append_vertex_staging_row(doc, vertex_staging_path)
        hooks["vertex_staging"] = {"ok": True, "path": str(vertex_staging_path)}

    if meta_layer_json is not None:
        if not meta_layer_json.is_file():
            hooks["meta_layer"] = {"ok": False, "error": "missing_meta_layer_json"}
        else:
            hooks["meta_layer"] = validate_meta_layer_envelope(
                meta_layer_json,
                append_log=append_meta_layer_log,
            )
        if not hooks["meta_layer"]["ok"]:
            doc["all_pass"] = False
            doc["failed_reasons"] = list(doc.get("failed_reasons") or []) + ["meta_layer_validate_fail"]
            doc["final_action"] = arbitrate(validate_errors=doc["failed_reasons"])
            hooks["gate_downgraded"] = True

    return hooks


def maybe_write_checkpoint(message: str, *, dry_run_checkpoint: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "athena_checkpoint.py")]
    if dry_run_checkpoint:
        cmd.append("--dry-run")
    cmd.append(message[:240])
    cp = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "")[-300:],
    }


def _write_out(doc: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    if args.draft_file:
        draft = _read_text(Path(args.draft_file))
    elif args.draft_text is not None:
        draft = args.draft_text
    else:
        print("mkm_system2_self_correction_gate_mvp_v1: --draft-file or --draft-text required", file=sys.stderr)
        return 2

    field_context: dict[str, Any] | None = None
    if args.field_context_json:
        field_context = _load_json(Path(args.field_context_json))

    corpus_extra = ""
    if args.mission_log and Path(args.mission_log).is_file():
        corpus_extra += _read_text(Path(args.mission_log))[:4000]
    if args.central and Path(args.central).is_file():
        corpus_extra += _read_text(Path(args.central))[:4000]

    doc = run_gate(
        draft,
        field_context=field_context,
        corpus_extra=corpus_extra,
        max_retries=args.max_retries,
        dry_run=not args.live,
        gemini_repair=getattr(args, "gemini_repair", False),
        ollama_repair=getattr(args, "ollama_repair", False),
        mission_log=Path(args.mission_log) if args.mission_log else None,
        central=Path(args.central) if args.central else None,
    )

    if args.write_checkpoint and doc["all_pass"]:
        if args.checkpoint_apply:
            if not getattr(args, "human_signoff_json", None):
                print("mkm_system2_self_correction_gate_mvp_v1: --checkpoint-apply requires --human-signoff-json", file=sys.stderr)
                return 2
            from scripts.mkm_system2_human_signoff_v1 import validate_signoff

            signoff_errs = validate_signoff(
                Path(args.human_signoff_json),
                required_scope="checkpoint_apply",
            )
            if signoff_errs:
                print("mkm_system2_self_correction_gate_mvp_v1: signoff invalid: " + ";".join(signoff_errs), file=sys.stderr)
                return 1
        msg = args.checkpoint_message or f"system2 gate pass: {(doc.get('draft_final') or '')[:120]}"
        doc["checkpoint"] = maybe_write_checkpoint(
            msg,
            dry_run_checkpoint=not args.checkpoint_apply,
        )
        if getattr(args, "human_signoff_json", None):
            from scripts.mkm_system2_human_signoff_v1 import signoff_summary

            doc.setdefault("human_signoff", signoff_summary(Path(args.human_signoff_json)))

    meta_path = Path(args.meta_layer_json) if getattr(args, "meta_layer_json", None) else None
    if getattr(args, "export_promotion", False) or meta_path or getattr(args, "vertex_staging", False):
        out_path = Path(args.out_json) if args.out_json else DEFAULT_OUT
        doc["post_pass_hooks"] = apply_post_pass_hooks(
            doc,
            gate_report_path=out_path,
            meta_layer_json=meta_path,
            append_meta_layer_log=getattr(args, "append_meta_layer_log", False),
            vertex_staging_path=(
                Path(args.vertex_staging_jsonl)
                if getattr(args, "vertex_staging", False)
                else None
            ),
            promotion_out_path=(
                Path(args.promotion_out_json)
                if getattr(args, "export_promotion", False)
                else None
            ),
        )

    try:
        validate_report(doc)
    except Exception as exc:
        print(f"mkm_system2_self_correction_gate_mvp_v1: report schema invalid: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out_json) if args.out_json else DEFAULT_OUT
    _write_out(doc, out_path)

    if doc["all_pass"] and args.append_passed_log:
        append_passed_log(doc, Path(args.passed_log) if args.passed_log else DEFAULT_PASSED_LOG)

    print(json.dumps({"ok": doc["all_pass"], "out_json": str(out_path), "decision": doc["final_action"]["decision"]}))
    return 0 if doc["all_pass"] else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="MKM System2 self-correction gate MVP v1")
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run output-hold validate loop")
    run.add_argument("--draft-file", help="Draft text file")
    run.add_argument("--draft-text", help="Draft inline text")
    run.add_argument("--field-context-json", help="Allowed fields/values JSON for ghost-metric checks")
    run.add_argument("--mission-log", default=str(DEFAULT_MISSION_LOG))
    run.add_argument("--central", default=str(DEFAULT_CENTRAL))
    run.add_argument("--max-retries", type=int, default=2)
    run.add_argument("--live", action="store_true", help="rule_guided_live_v1 repair on retry")
    run.add_argument("--gemini-repair", action="store_true", help="Use Gemini repair on live retries (or MKM_SYSTEM2_GEMINI_REPAIR=1)")
    run.add_argument("--ollama-repair", action="store_true", help="Use Ollama repair on live retries (or MKM_SYSTEM2_OLLAMA_REPAIR=1)")
    run.add_argument("--human-signoff-json", help="Required for --checkpoint-apply")
    run.add_argument("--out-json", default=str(DEFAULT_OUT))
    run.add_argument("--append-passed-log", action="store_true")
    run.add_argument("--passed-log", default=str(DEFAULT_PASSED_LOG))
    run.add_argument("--export-promotion", action="store_true", help="Write memory promotion candidate JSON on pass")
    run.add_argument("--promotion-out-json", default=str(DEFAULT_PROMOTION_OUT))
    run.add_argument("--vertex-staging", action="store_true", help="Append pass row to Vertex staging jsonl (offline)")
    run.add_argument("--vertex-staging-jsonl", default=str(DEFAULT_VERTEX_STAGING))
    run.add_argument("--meta-layer-json", help="Validate meta-layer envelope serially after gate pass")
    run.add_argument("--append-meta-layer-log", action="store_true", help="Append validated envelope to agent_decisions_log")
    run.add_argument("--write-checkpoint", action="store_true")
    run.add_argument("--checkpoint-apply", action="store_true", help="Actually write CENTRAL checkpoint (default dry-run)")
    run.add_argument("--checkpoint-message")
    run.set_defaults(func=cmd_run)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
