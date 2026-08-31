#!/usr/bin/env python3
"""Build mkm_research_digested_fact_v1 JSON from Tier 0 markdown (Mastication, B-track).

Parses explicit ## Digested facts blocks and heuristic table rows (Work | Claim).
Track B · research_only · send_gate HOLD · not Track A promotion until gate Right.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_dr2_digest_wiring_v1 import (  # noqa: E402
    SCHEMA_VERSION,
    build_binding_candidate_wiring,
    build_hold_no_target_wiring,
    has_legacy_wiring_keys,
    normalize_fact_record,
    utc_now,
)

DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_research_digested_fact_v1.schema.json"

DIGESTED_SECTION_RE = re.compile(
    r"^##\s+digested\s+facts(?:\s+\([^)]+\))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
FACT_HEADING_RE = re.compile(r"^###\s+fact_id:\s*([a-z0-9_]+)\s*$", re.IGNORECASE | re.MULTILINE)
BULLET_KV_RE = re.compile(r"^-\s+([a-z_]+):\s*(.+?)\s*$", re.IGNORECASE)
ARXIV_RE = re.compile(r"\b(2[0-9]{3}\.[0-9]{4,5})\b")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*([^;|↓↑×x\n]{0,40})", re.IGNORECASE)
MULTIPLIER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*×", re.IGNORECASE)
SINGLE_MULT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*×", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:64] or "fact"


def _parse_float(raw: str) -> float:
    return float(raw.strip().rstrip("%").replace(",", ""))


def _parse_explicit_blocks(text: str) -> list[dict[str, Any]]:
    match = DIGESTED_SECTION_RE.search(text)
    if not match:
        return []

    section_text = text[match.end() :]
    facts: list[dict[str, Any]] = []
    headings = list(FACT_HEADING_RE.finditer(section_text))
    if not headings:
        return facts

    for idx, heading in enumerate(headings):
        fact_id = heading.group(1).strip().lower()
        start = heading.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(section_text)
        block = section_text[start:end]
        kv: dict[str, str] = {}
        for line in block.splitlines():
            m = BULLET_KV_RE.match(line.strip())
            if m:
                kv[m.group(1).lower()] = m.group(2).strip()

        if "metric_name" not in kv or "value" not in kv:
            continue

        unit = kv.get("unit", "other")
        if unit not in {"ratio", "percent", "multiplier", "count", "milliseconds", "other"}:
            unit = "other"

        verification_status = kv.get("verification_status", "Unknown")
        if verification_status not in {"Right", "Wrong", "Unknown"}:
            verification_status = "Unknown"

        verification_method = kv.get("verification_method", "not_run")
        if verification_method not in {
            "active_fact_lite",
            "abstract_only",
            "paywall_blocked",
            "fixture_trusted",
            "not_run",
        }:
            verification_method = "fixture_trusted" if verification_status == "Right" else "not_run"

        prov: dict[str, Any] = {"extraction_method": "explicit_block"}
        if kv.get("arxiv_id"):
            prov["arxiv_id"] = kv["arxiv_id"]
        if kv.get("table_ref"):
            prov["table_ref"] = kv["table_ref"]
        if kv.get("url"):
            prov["url"] = kv["url"]

        fact: dict[str, Any] = {
            "fact_id": fact_id,
            "metric_name": kv["metric_name"],
            "value": _parse_float(kv["value"]),
            "unit": unit,
            "comparison_arm": kv.get("comparison_arm", fact_id),
            "provenance": prov,
            "verification": {
                "status": verification_status,
                "method": verification_method,
            },
        }
        if kv.get("verification_reason"):
            fact["verification"]["reason"] = kv["verification_reason"]

        if has_legacy_wiring_keys(kv):
            fact["mkm_wiring"] = build_binding_candidate_wiring(
                fact_id=fact_id,
                baseline_plane=kv["baseline_plane"],
                artifact_path=kv["artifact_path"],
                artifact_field=kv["artifact_field"],
                assertion=kv["assertion"],
                binding_reason="explicit wiring keys in ## Digested facts block",
                verification_status=verification_status,
            )

        facts.append(fact)
    return facts


def _metric_from_context(label: str) -> str:
    label_l = label.lower()
    if "latency" in label_l:
        return "latency_change"
    if "cost" in label_l:
        return "cost_change"
    if "energy" in label_l:
        return "energy_change"
    if "offload" in label_l or "cloud" in label_l:
        return "cloud_offload_rate"
    if "quality" in label_l:
        return "quality_rate"
    return _slugify(label)[:48]


def _extract_from_table_rows(text: str, *, existing_ids: set[str]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for line in text.splitlines():
        row = TABLE_ROW_RE.match(line.strip())
        if not row:
            continue
        work = row.group(1).strip()
        claim = row.group(2).strip()
        if work.lower() in {"work", "benchmark", "---", "paper"} or claim.lower() in {"claim", "finding", "---"}:
            continue
        if not re.search(r"\d", claim):
            continue

        arxiv_match = ARXIV_RE.search(f"{work} {claim}")
        arxiv_id = arxiv_match.group(1) if arxiv_match else None

        for pct in PERCENT_RE.finditer(claim):
            label = pct.group(2).strip() or work
            metric = _metric_from_context(label)
            fact_id = _slugify(f"{work}_{metric}")
            suffix = 2
            while fact_id in existing_ids:
                fact_id = f"{fact_id}_{suffix}"
                suffix += 1
            existing_ids.add(fact_id)
            prov: dict[str, Any] = {
                "extraction_method": "table_heuristic",
                "source_line_hint": line.strip()[:200],
            }
            if arxiv_id:
                prov["arxiv_id"] = arxiv_id
            facts.append(
                {
                    "fact_id": fact_id,
                    "metric_name": metric,
                    "value": float(pct.group(1)),
                    "unit": "percent",
                    "comparison_arm": work,
                    "provenance": prov,
                    "verification": {"status": "Unknown", "method": "not_run"},
                }
            )

        mult = MULTIPLIER_RE.search(claim) or SINGLE_MULT_RE.search(claim)
        if mult:
            if mult.lastindex and mult.lastindex >= 2:
                value = (float(mult.group(1)) + float(mult.group(2))) / 2.0
            else:
                value = float(mult.group(1))
            fact_id = _slugify(f"{work}_multiplier")
            suffix = 2
            while fact_id in existing_ids:
                fact_id = f"{fact_id}_{suffix}"
                suffix += 1
            existing_ids.add(fact_id)
            prov = {
                "extraction_method": "table_heuristic",
                "source_line_hint": line.strip()[:200],
            }
            if arxiv_id:
                prov["arxiv_id"] = arxiv_id
            facts.append(
                {
                    "fact_id": fact_id,
                    "metric_name": "multiplier",
                    "value": value,
                    "unit": "multiplier",
                    "comparison_arm": work,
                    "provenance": prov,
                    "verification": {"status": "Unknown", "method": "not_run"},
                }
            )
    return facts


def build_mkm_research_digested_facts(
    *,
    source_path: Path,
    topic_slug: str | None = None,
    include_table_heuristic: bool = True,
) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    facts = _parse_explicit_blocks(text)
    methods: list[str] = []
    if facts:
        methods.append("explicit_block")
    if include_table_heuristic:
        existing_ids = {f["fact_id"] for f in facts}
        table_facts = _extract_from_table_rows(text, existing_ids=existing_ids)
        if table_facts:
            methods.append("table_heuristic")
        facts.extend(table_facts)

    if not methods:
        methods.append("none")

    slug = topic_slug or _slugify(source_path.stem)
    flags = []
    if any(f.get("verification", {}).get("status") == "Unknown" for f in facts):
        flags.append("contains_unverified_numeric_facts")
    if any(f.get("provenance", {}).get("extraction_method") == "table_heuristic" for f in facts):
        flags.append("table_heuristic_not_llm_verified")

    origin = _posix_path(source_path)
    generated_at = utc_now()
    normalized_facts: list[dict[str, Any]] = []
    for fact in facts:
        nf = normalize_fact_record(
            fact,
            artifact_origin=origin,
            created_at=generated_at,
            citation_status="not_run_at_mastication",
        )
        if not nf.get("mkm_wiring"):
            nf["mkm_wiring"] = build_hold_no_target_wiring(
                fact_id=str(nf["fact_id"]),
                binding_reason="mastication default; wiring resolved in map step",
                source_artifact_ids=[origin],
            )
        normalized_facts.append(nf)

    return {
        "schema": "mkm_research_digested_fact_v1",
        "version": SCHEMA_VERSION,
        "research_only": True,
        "send_gate": "HOLD",
        "authoritative_ssot_auto_apply": "LOCKED",
        "topic_slug": slug,
        "source_tier0_path": origin,
        "source_sha256": file_sha256(source_path),
        "facts": normalized_facts,
        "provenance": {
            "generated_at_utc": generated_at,
            "extraction_methods": methods,
            "uncertainty_flags": flags,
            "extraction_notes": (
                f"Mastication from {origin}; "
                "DR2 explicit mkm_wiring required; pytest gate for Right+ assertions."
            ),
            "dr2_normalized_at_utc": generated_at,
        },
    }


def validate_digested(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("jsonschema required for --strict") from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def default_out_path(source: Path, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    return out_dir / f"{source.stem}_digested_facts_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build mkm_research_digested_fact_v1 from Tier 0 markdown")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--topic-slug", default=None)
    parser.add_argument("--no-table-heuristic", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {source}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    doc = build_mkm_research_digested_facts(
        source_path=source,
        topic_slug=args.topic_slug,
        include_table_heuristic=not args.no_table_heuristic,
    )
    if args.strict:
        try:
            validate_digested(doc)
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": str(exc), "step": "schema_validate"}, ensure_ascii=False),
                file=sys.stderr,
            )
            return 2

    out_path = args.out.resolve() if args.out else default_out_path(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix_path(out_path),
                "fact_count": len(doc["facts"]),
                "source_sha256": doc["source_sha256"],
                "schema_validated": bool(args.strict),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
