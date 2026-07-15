#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resume pin staleness advisory + CENTRAL checkpoint contradiction detect (P0.3).

Maps: Zep temporal invalidation spirit; memory poisoning temporal decay advisory.
research_only · SEND HOLD · no auto-forget / no Track A merge.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_resume_pin_freshness_v1.schema.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "mkm_resume_pin_freshness_policy_v1_latest.json"
DEFAULT_LATEST = ROOT / "docs" / "final" / "artifacts" / "mkm_resume_pin_freshness_v1_latest.json"
DEFAULT_CENTRAL = ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
DEFAULT_INDEX = ROOT / "storage" / "meta" / "mkm_ops_memory_index_v1.json"

SCHEMA = "mkm_resume_pin_freshness_v1"

CHECKPOINT_LINE_RE = re.compile(
    r"^-\s+\*\*(\d{4}-\d{2}-\d{2}T[\d:.]+Z)\*\*\s+—\s+(.+)$"
)
CONTINUITY_RE = re.compile(r"continuity=([a-z0-9][a-z0-9._-]{2,127})", re.I)
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,}")

STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "only",
        "next",
        "exit0",
        "pytest",
        "research",
        "continuity",
        "artifact",
        "scripts",
        "send",
        "gate",
        "track",
        "live",
        "trade",
        "mkm",
        "athena",
    }
)

POLARITY_POS = frozenset(
    {
        "done",
        "complete",
        "closed",
        "applied",
        "pass",
        "passed",
        "confirmed",
        "enabled",
        "approved",
        "go",
        "ready",
        "live",
        "fixed",
        "resolved",
    }
)
POLARITY_NEG = frozenset(
    {
        "open",
        "hold",
        "pending",
        "blocked",
        "fail",
        "failed",
        "reverted",
        "stale",
        "deferred",
        "stopped",
        "stop",
        "absent",
        "forbidden",
        "no_go",
        "nogo",
    }
)

# Essence-only PASS/DONE claims (must_keep tags alone do NOT trigger).
ESSENCE_L2_CLAIM_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:PASS(?:ED)?|DONE|exit\s*0|exit0|overall_ok)\b"
    r"|\bgold\s+\d+\s*/\s*\d+\b"
    r")"
)

# L0 coordinate surfaces — not L2 truth (CONSTITUTION/scripts/artifacts/exit).
L0_COORDINATE_SURFACES = frozenset(
    {
        "MISSION_LOG.md",
        "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
    }
)


def utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(stamp: str) -> datetime:
    s = stamp.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def age_days_between(as_of: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    delta = now - as_of
    return max(0.0, delta.total_seconds() / 86400.0)


def load_policy(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_POLICY
    if not path.is_file():
        return {"default_max_age_days": 7, "max_age_days_by_node_id": {}, "max_age_days_by_prefix": {}}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc


def max_age_days_for_node(node_id: str, policy: dict[str, Any]) -> int:
    by_id = policy.get("max_age_days_by_node_id") or {}
    if node_id in by_id:
        return int(by_id[node_id])
    by_prefix = policy.get("max_age_days_by_prefix") or {}
    for prefix, days in by_prefix.items():
        if node_id.startswith(str(prefix)):
            return int(days)
    return int(policy.get("default_max_age_days") or 7)


def parse_central_checkpoints(
    central_text: str,
    *,
    max_rows: int = 20,
) -> list[dict[str, Any]]:
    start = central_text.find("<!-- ATHENA_CHECKPOINT_V1_START -->")
    end = central_text.find("<!-- ATHENA_CHECKPOINT_V1_END -->")
    if start < 0 or end < 0 or end <= start:
        return []
    block = central_text[start:end]
    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        m = CHECKPOINT_LINE_RE.match(line.strip())
        if not m:
            continue
        ts, message = m.group(1), m.group(2).strip()
        cont = CONTINUITY_RE.search(message)
        rows.append(
            {
                "stamp_utc": ts,
                "message": message,
                "continuity_id": cont.group(1) if cont else "",
            }
        )
    return rows[:max_rows]


def _message_tokens(message: str) -> set[str]:
    raw = message.lower()
    raw = CONTINUITY_RE.sub(" ", raw)
    tokens: set[str] = set()
    for m in TOKEN_RE.finditer(raw):
        tok = m.group(0)
        if tok in STOPWORDS:
            continue
        if tok.isdigit():
            continue
        tokens.add(tok)
    return tokens


def _polarity(message: str) -> str | None:
    toks = _message_tokens(message)
    pos = bool(toks & POLARITY_POS)
    neg = bool(toks & POLARITY_NEG)
    if pos and not neg:
        return "pos"
    if neg and not pos:
        return "neg"
    if pos and neg:
        return "mixed"
    return None


def _stamp_delta_seconds(newer_stamp: str, older_stamp: str) -> float | None:
    try:
        return abs(
            (parse_iso_utc(newer_stamp) - parse_iso_utc(older_stamp)).total_seconds()
        )
    except (ValueError, TypeError):
        return None


def detect_checkpoint_contradictions(
    checkpoints: list[dict[str, Any]],
    *,
    min_shared_tokens: int = 2,
    same_continuity_burst_seconds: int | None = None,
) -> list[dict[str, Any]]:
    """Flag pairs where newer 1-liner collides with an older 1-liner.

    same_continuity: only when polarity conflicts (DONE vs OPEN). Same-polarity
    wording refinements and near-duplicate bursts are suppressed.
    """
    collisions: list[dict[str, Any]] = []
    if len(checkpoints) < 2:
        return collisions

    if same_continuity_burst_seconds is None:
        policy = load_policy()
        same_continuity_burst_seconds = int(
            policy.get("checkpoint_same_continuity_burst_seconds") or 60
        )

    for i in range(len(checkpoints) - 1):
        newer = checkpoints[i]
        for j in range(i + 1, len(checkpoints)):
            older = checkpoints[j]
            n_msg = str(newer.get("message") or "")
            o_msg = str(older.get("message") or "")
            n_cont = str(newer.get("continuity_id") or "")
            o_cont = str(older.get("continuity_id") or "")

            reason: str | None = None
            shared: list[str] = []
            n_pol = _polarity(n_msg)
            o_pol = _polarity(o_msg)

            if n_cont and n_cont == o_cont and n_msg.strip() != o_msg.strip():
                delta = _stamp_delta_seconds(
                    str(newer.get("stamp_utc") or ""),
                    str(older.get("stamp_utc") or ""),
                )
                # Burst double-write / refine same status — not a contradiction.
                if (
                    delta is not None
                    and delta <= float(same_continuity_burst_seconds)
                    and n_pol
                    and o_pol
                    and n_pol == o_pol
                ):
                    reason = None
                elif (
                    n_pol
                    and o_pol
                    and n_pol != o_pol
                    and n_pol != "mixed"
                    and o_pol != "mixed"
                ):
                    reason = "same_continuity_divergent_status"
                elif n_pol and o_pol and n_pol == o_pol:
                    # Same continuity, same polarity, outside burst — wording drift only.
                    reason = None
                else:
                    # Ambiguous polarity on same continuity — keep advisory.
                    reason = "same_continuity_divergent_status"
            else:
                n_tok = _message_tokens(n_msg)
                o_tok = _message_tokens(o_msg)
                shared = sorted(n_tok & o_tok)[:12]
                if (
                    len(shared) >= min_shared_tokens
                    and n_pol
                    and o_pol
                    and n_pol != o_pol
                    and n_pol != "mixed"
                    and o_pol != "mixed"
                ):
                    reason = "polarity_conflict+topic_overlap"
                elif n_pol and o_pol and n_pol != o_pol and n_pol != "mixed" and o_pol != "mixed":
                    overlap = n_tok & o_tok
                    if len(overlap) >= 1:
                        shared = sorted(overlap)[:12]
                        reason = "polarity_conflict"

            if not reason:
                continue

            collisions.append(
                {
                    "newer_stamp_utc": newer.get("stamp_utc", ""),
                    "older_stamp_utc": older.get("stamp_utc", ""),
                    "newer_message": n_msg[:2000],
                    "older_message": o_msg[:2000],
                    "contradicts_prior_checkpoint": True,
                    "collision_reason": reason,
                    "shared_tokens": shared,
                    **({"continuity_id": n_cont} if n_cont else {}),
                }
            )
    return collisions


def _json_generated_at(root: Path, rel_path: str | None) -> str | None:
    if not rel_path:
        return None
    path = root / rel_path.replace("\\", "/")
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None
    for key in ("generated_at_utc", "last_updated_utc", "stamp_utc"):
        val = doc.get(key)
        if isinstance(val, str) and len(val) >= 10:
            return val
    return None


def resolve_pin_as_of_utc(
    *,
    root: Path,
    node_id: str,
    pin: dict[str, Any],
    index_doc: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return (as_of_utc, age_source)."""
    if node_id == "prism_ops_central_checkpoint" and checkpoints:
        return str(checkpoints[0]["stamp_utc"]), "newest_checkpoint"

    json_stamp = _json_generated_at(root, pin.get("file_path"))
    if json_stamp:
        return json_stamp, "json_generated_at"

    idx_stamp = index_doc.get("last_updated_utc")
    if isinstance(idx_stamp, str) and idx_stamp:
        return idx_stamp, "index_last_updated"

    rel = pin.get("file_path")
    nodes = index_doc.get("nodes") or {}
    node = nodes.get(node_id) or {}
    rel = node.get("file_path") or rel
    if rel:
        fpath = root / str(rel).replace("\\", "/")
        if fpath.is_file():
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc)
            return mtime.strftime("%Y-%m-%dT%H:%M:%SZ"), "file_mtime"

    return utc_now_z(), "unknown"


def build_pin_freshness_row(
    *,
    node_id: str,
    pin: dict[str, Any],
    root: Path,
    policy: dict[str, Any],
    index_doc: dict[str, Any],
    checkpoints: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    as_of_utc, age_source = resolve_pin_as_of_utc(
        root=root,
        node_id=node_id,
        pin=pin,
        index_doc=index_doc,
        checkpoints=checkpoints,
    )
    age = age_days_between(parse_iso_utc(as_of_utc), now=now)
    max_age = max_age_days_for_node(node_id, policy)
    return {
        "node_id": node_id,
        "age_days": round(age, 3),
        "max_age_days": max_age,
        "stale_advisory": age > float(max_age),
        "as_of_utc": as_of_utc,
        "age_source": age_source,
    }


def essence_claims_l2_pass(essence: str) -> bool:
    """True when pin *essence* claims PASS/DONE (ignore must_keep-only)."""
    return bool(ESSENCE_L2_CLAIM_RE.search(essence or ""))


def resolve_l2_evidence(
    root: Path,
    file_path: str | None,
) -> tuple[bool, str]:
    """Cheap L2 evidence check: path must be a real non-L0 artifact file."""
    if not file_path or not str(file_path).strip():
        return False, "missing_file_path"
    rel = str(file_path).replace("\\", "/")
    if rel in L0_COORDINATE_SURFACES or rel.endswith("CENTRAL_AGENT_MEMORY_V1.md"):
        return False, "l0_surface_not_l2_evidence"
    path = root / rel
    if not path.is_file():
        return False, "missing_l2_artifact"
    if path.suffix.lower() == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return False, "l2_artifact_unreadable"
        if not isinstance(doc, dict) or not doc:
            return False, "l2_artifact_empty"
    return True, "ok"


def detect_l0_l2_claim_gaps(
    pins: list[dict[str, Any]],
    root: Path,
) -> list[dict[str, Any]]:
    """Warn when essence claims PASS/DONE but L2 artifact evidence is missing.

    must_keep substrings alone never trigger — essence text is required.
    """
    gaps: list[dict[str, Any]] = []
    for pin in pins:
        essence = str(pin.get("essence") or "")
        if not essence_claims_l2_pass(essence):
            continue
        ok, reason = resolve_l2_evidence(root, pin.get("file_path"))
        if ok:
            continue
        gaps.append(
            {
                "node_id": str(pin.get("node_id") or ""),
                "essence_preview": essence[:240],
                "file_path": str(pin.get("file_path") or ""),
                "gap_reason": reason,
                "advisory": True,
            }
        )
    return gaps


def annotate_ops_pins_freshness(
    pins: list[dict[str, Any]],
    root: Path,
    *,
    policy: dict[str, Any] | None = None,
    index_doc: dict[str, Any] | None = None,
    central_text: str | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Enrich pins with freshness fields; return (pins, contradictions, l0_l2_gaps)."""
    policy = policy or load_policy()
    index_path = root / DEFAULT_INDEX.relative_to(ROOT)
    if index_doc is None and index_path.is_file():
        index_doc = json.loads(index_path.read_text(encoding="utf-8-sig"))
    index_doc = index_doc or {}

    central_path = root / DEFAULT_CENTRAL.relative_to(ROOT)
    if central_text is None and central_path.is_file():
        central_text = central_path.read_text(encoding="utf-8")
    central_text = central_text or ""
    window = int(policy.get("checkpoint_contradiction_window") or 12)
    checkpoints = parse_central_checkpoints(central_text, max_rows=window)
    contradictions = detect_checkpoint_contradictions(checkpoints)
    l0_l2_gaps = detect_l0_l2_claim_gaps(pins, root)

    enriched: list[dict[str, Any]] = []
    gap_by_id = {g["node_id"]: g for g in l0_l2_gaps if g.get("node_id")}
    for pin in pins:
        node_id = str(pin.get("node_id") or "")
        row = build_pin_freshness_row(
            node_id=node_id,
            pin=pin,
            root=root,
            policy=policy,
            index_doc=index_doc,
            checkpoints=checkpoints,
            now=now,
        )
        merged = dict(pin)
        merged["max_age_days"] = row["max_age_days"]
        merged["age_days"] = row["age_days"]
        merged["stale_advisory"] = row["stale_advisory"]
        merged["as_of_utc"] = row["as_of_utc"]
        merged["age_source"] = row["age_source"]
        if node_id == "prism_ops_central_checkpoint" and contradictions:
            merged["checkpoint_contradictions"] = contradictions
        if node_id in gap_by_id:
            merged["l0_l2_claim_gap"] = gap_by_id[node_id]
        enriched.append(merged)
    return enriched, contradictions, l0_l2_gaps


def build_freshness_report(
    pins: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    *,
    l0_l2_claim_gaps: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    policy = policy or load_policy()
    gaps = l0_l2_claim_gaps or []
    pin_rows = [
        {
            "node_id": p.get("node_id"),
            "age_days": p.get("age_days"),
            "max_age_days": p.get("max_age_days"),
            "stale_advisory": p.get("stale_advisory"),
            "as_of_utc": p.get("as_of_utc"),
            "age_source": p.get("age_source"),
        }
        for p in pins
        if p.get("node_id")
    ]
    stale_count = sum(1 for r in pin_rows if r.get("stale_advisory"))
    return {
        "schema": SCHEMA,
        "generated_at_utc": generated_at_utc or utc_now_z(),
        "research_only": True,
        "send_gate": "HOLD",
        "policy_pointer": str(DEFAULT_POLICY.relative_to(ROOT)).replace("\\", "/"),
        "default_max_age_days": int(policy.get("default_max_age_days") or 7),
        "pins": pin_rows,
        "checkpoint_contradictions": contradictions,
        "l0_l2_claim_gaps": gaps,
        "advisory_summary": {
            "stale_pin_count": stale_count,
            "contradiction_count": len(contradictions),
            "l0_l2_claim_gap_count": len(gaps),
        },
        "reproduce": [
            "py scripts/check_mkm_resume_pin_freshness_v1.py",
            "py -m pytest tests/test_mkm_resume_pin_freshness_v1.py -q",
        ],
    }


def validate_freshness_report(report: dict[str, Any], schema_path: Path | None = None) -> list[str]:
    errs: list[str] = []
    if report.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    if report.get("research_only") is not True:
        errs.append("research_only must be true")
    if report.get("send_gate") != "HOLD":
        errs.append("send_gate must be HOLD")
    schema_path = schema_path or DEFAULT_SCHEMA
    if schema_path.is_file():
        try:
            import jsonschema  # type: ignore

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(report, schema)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            errs.append(f"jsonschema: {exc}")
    return errs


def write_freshness_latest(report: dict[str, Any], path: Path | None = None) -> None:
    path = path or DEFAULT_LATEST
    errs = validate_freshness_report(report)
    if errs:
        raise ValueError("; ".join(errs))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        ckpts = [
            {"stamp_utc": "2026-07-15T10:00:00Z", "message": "continuity=demo · P0.3 DONE exit0", "continuity_id": "demo"},
            {"stamp_utc": "2026-07-15T09:00:00Z", "message": "continuity=demo · P0.3 OPEN blocked", "continuity_id": "demo"},
        ]
        hits = detect_checkpoint_contradictions(ckpts)
        assert hits and hits[0]["collision_reason"] == "same_continuity_divergent_status"
        row = build_pin_freshness_row(
            node_id="prism_ops_central_checkpoint",
            pin={"file_path": "docs/final/CENTRAL_AGENT_MEMORY_V1.md"},
            root=ROOT,
            policy=load_policy(),
            index_doc={},
            checkpoints=ckpts,
            now=parse_iso_utc("2026-07-15T12:00:00Z"),
        )
        assert row["age_source"] == "newest_checkpoint"
        print("OK: mkm_resume_pin_freshness_v1 self-test")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
