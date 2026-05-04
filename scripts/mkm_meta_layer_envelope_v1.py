#!/usr/bin/env python3
"""
MKM Meta-Layer turn envelope v1 — JSON Schema validation + optional append to
reports/agent_decisions_log.jsonl (append-only).

Track C: optional hook at end of Invoke-TrackCMacroDailyFusion_v1.ps1, e.g.:
  py scripts/mkm_meta_layer_envelope_v1.py validate --json-file path\\envelope.json
  py scripts/mkm_meta_layer_envelope_v1.py append --json-file ... --mission-id trackc-fusion-daily --actor fusion-runner

Does not run fusion; only validates / logs when given an envelope file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    REPO_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "schemas"
    / "mkm_meta_layer_turn_envelope_v1.schema.json"
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_schema(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_SCHEMA
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def validate_jsonschema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("jsonschema package required") from e
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def coherence_rules(instance: dict[str, Any]) -> list[str]:
    """MKM hard rails beyond JSON Schema."""
    errs: list[str] = []
    rh = instance.get("rival_hypotheses") or {}
    h1, h2 = rh.get("H1", "").strip(), rh.get("H2", "").strip()
    if h1 == h2:
        errs.append("rival_hypotheses.H1 and H2 must differ (non-identical).")

    cc = instance.get("contradiction_check") or {}
    hold = cc.get("hold_recommendation")
    eb = instance.get("execution_barrier_labels") or {}
    allowed = eb.get("execution_allowed")

    if instance.get("risk_tier") == "ZERO_TOLERANCE" and allowed is True:
        errs.append("risk_tier ZERO_TOLERANCE requires execution_allowed=false.")

    if hold in ("HOLD", "ABORT") and allowed is True:
        errs.append(
            "hold_recommendation HOLD|ABORT requires execution_allowed=false."
        )

    if cc.get("violates_constitution_or_gates") is True and allowed is True:
        errs.append(
            "violates_constitution_or_gates=true requires execution_allowed=false."
        )

    return errs


def validate_envelope(
    instance: dict[str, Any], *, schema_path: Path | None = None
) -> list[str]:
    """Return list of error strings; empty means OK."""
    try:
        schema = load_schema(schema_path)
        validate_jsonschema(instance, schema)
    except Exception as e:
        return [f"jsonschema: {e}"]
    return coherence_rules(instance)


def apply_kill_switch_normalization(instance: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Force execution_allowed=false when risk tier or contradiction gates demand it.
    Returns (copy, changed).
    """
    out = deepcopy(instance)
    eb = out.setdefault("execution_barrier_labels", {})
    cc = out.get("contradiction_check") or {}
    changed = False
    if out.get("risk_tier") == "ZERO_TOLERANCE" and eb.get("execution_allowed") is True:
        eb["execution_allowed"] = False
        changed = True
    if cc.get("hold_recommendation") in ("HOLD", "ABORT") and eb.get("execution_allowed") is True:
        eb["execution_allowed"] = False
        changed = True
    if cc.get("violates_constitution_or_gates") is True and eb.get("execution_allowed") is True:
        eb["execution_allowed"] = False
        changed = True
    return out, changed


def extract_envelope_dict_from_agent_text(text: str) -> dict[str, Any]:
    """
    Parse meta-layer JSON from LLM-style output: fenced ```json ... ``` first,
    else a single JSON object spanning the string (stripped).
    """
    t = text.strip()
    m = re.search(r"```json\s*(.*?)\s*```", t, re.DOTALL | re.IGNORECASE)
    if m:
        payload = m.group(1).strip()
    else:
        payload = t
    return json.loads(payload)


class AthenaValidator:
    """
    Tollgate: parse LLM (or raw) text → normalize kill switch → validate → optional audit log.
    Reuses on-disk JSON Schema; does not duplicate schema literals.
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        schema_path: Path | None = None,
    ) -> None:
        self.repo_root = (repo_root or REPO_ROOT).resolve()
        self.schema_path = schema_path

    def validate_and_audit(
        self,
        agent_response: str,
        *,
        mission_id: str,
        actor: str,
        stage: str = "meta_layer",
        append_log: bool = True,
        evidence_path: str | None = None,
        note: str | None = None,
    ) -> Tuple[bool, dict[str, Any], str]:
        try:
            meta = extract_envelope_dict_from_agent_text(agent_response)
        except json.JSONDecodeError as e:
            return False, {}, f"[ATHENA-FAIL] JSON parse: {e}"

        normalized, repaired = apply_kill_switch_normalization(meta)
        errs = validate_envelope(normalized, schema_path=self.schema_path)
        if errs:
            return False, normalized, "[ATHENA-FAIL] " + "; ".join(errs)

        audit_msg = (
            "[ATHENA-PASS] envelope OK"
            + ("; kill_switch_normalized" if repaired else "")
        )

        if append_log:
            append_agent_decisions_log(
                self.repo_root,
                normalized,
                mission_id=mission_id,
                stage=stage,
                actor=actor,
                evidence_path=evidence_path,
                note=(note or "") + (";kill_switch_normalized" if repaired else ""),
            )

        allowed = bool(
            (normalized.get("execution_barrier_labels") or {}).get("execution_allowed")
        )
        return allowed, normalized, audit_msg


def append_agent_decisions_log(
    repo_root: Path,
    envelope: dict[str, Any],
    *,
    mission_id: str,
    stage: str,
    actor: str,
    evidence_path: str | None = None,
    note: str | None = None,
    timestamp: str | None = None,
) -> Path:
    log_path = repo_root / "reports" / "agent_decisions_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "timestamp": timestamp or _iso_now(),
        "mission_id": mission_id,
        "stage": stage,
        "decision": "meta_layer_envelope_v1",
        "evidence_path": evidence_path
        or "docs/final/artifacts/schemas/mkm_meta_layer_turn_envelope_v1.schema.json",
        "actor": actor,
        "meta_layer_envelope": envelope,
    }
    if note:
        entry["note"] = note
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_path


def _read_json_arg(path: Path | None) -> dict[str, Any]:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate envelope JSON")
    p_val.add_argument("--json-file", type=Path, default=None)
    p_val.add_argument("--schema", type=Path, default=None)

    p_app = sub.add_parser("append", help="Validate then append to agent_decisions_log.jsonl")
    p_app.add_argument("--json-file", type=Path, required=True)
    p_app.add_argument("--schema", type=Path, default=None)
    p_app.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    p_app.add_argument("--mission-id", required=True)
    p_app.add_argument("--stage", default="meta_layer")
    p_app.add_argument("--actor", required=True)
    p_app.add_argument("--evidence-path", default=None)
    p_app.add_argument("--note", default=None)
    p_app.add_argument("--dry-run", action="store_true")

    p_aud = sub.add_parser(
        "audit-markdown",
        help="Extract ```json envelope from markdown/text, validate, append log",
    )
    p_aud.add_argument("--markdown-file", type=Path, required=True)
    p_aud.add_argument("--schema", type=Path, default=None)
    p_aud.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    p_aud.add_argument("--mission-id", default="trackc-macro-daily-fusion")
    p_aud.add_argument("--stage", default="meta_layer")
    p_aud.add_argument("--actor", default="Invoke-TrackCMacroDailyFusion_v1")
    p_aud.add_argument("--evidence-path", default=None)
    p_aud.add_argument("--note", default=None)
    p_aud.add_argument("--no-append", action="store_true", help="Validate only; no JSONL write")

    args = parser.parse_args()

    if args.cmd == "validate":
        try:
            doc = _read_json_arg(args.json_file)
        except json.JSONDecodeError as e:
            print(f"INVALID_JSON: {e}", file=sys.stderr)
            return 2
        errs = validate_envelope(doc, schema_path=args.schema)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("OK: envelope validates.")
        return 0

    if args.cmd == "append":
        doc = json.loads(args.json_file.read_text(encoding="utf-8"))
        errs = validate_envelope(doc, schema_path=args.schema)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps(doc, ensure_ascii=False, indent=2))
            return 0
        out = append_agent_decisions_log(
            args.repo_root.resolve(),
            doc,
            mission_id=args.mission_id,
            stage=args.stage,
            actor=args.actor,
            evidence_path=args.evidence_path,
            note=args.note,
        )
        print(f"OK: appended -> {out}")
        return 0

    if args.cmd == "audit-markdown":
        text = args.markdown_file.read_text(encoding="utf-8")
        v = AthenaValidator(repo_root=args.repo_root, schema_path=args.schema)
        allowed, _meta, msg = v.validate_and_audit(
            text,
            mission_id=args.mission_id,
            actor=args.actor,
            stage=args.stage,
            append_log=not args.no_append,
            evidence_path=args.evidence_path,
            note=args.note,
        )
        print(msg)
        return 0 if msg.startswith("[ATHENA-PASS]") else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
