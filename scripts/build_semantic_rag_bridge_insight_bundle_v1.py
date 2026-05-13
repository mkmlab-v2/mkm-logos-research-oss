#!/usr/bin/env python3
"""Assemble internal semantic+RAG bridge insight bundle v1 (B-track / lab).

Reads optional RAG hit JSON, optional `premium_btrack_multilens_report_v1` JSON
(`lenses[].rag.retrieval_runs[].hits`), optional `philosophy_lane_rag_pilot_v1`
JSON (`blocks[]`), and optional calibration artifact path; emits JSON matching
docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json.

Merge order (total cap 24): ``--rag-json`` → ``--premium-multilens-report-json`` →
``--philosophy-pilot-json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "build_semantic_rag_bridge_insight_bundle_v1.py"
SCRIPT_VERSION = "1.0.2"
BUNDLE_VERSION = "1.0.2"
SCHEMA_ID = "semantic_rag_bridge_insight_bundle_v1"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "semantic_rag_bridge_insight_bundle_v1_latest.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / f"{SCHEMA_ID}.schema.json"

CALIBRATION_KINDS = frozenset(
    {
        "none",
        "myeongri_vector_4d",
        "logos_4d_state_v1",
        "prism_slkm_pointer",
        "compression_seed_slkm",
        "market_sasang_lens_snapshot",
    }
)
TRACK_ENUM = frozenset({"B-track", "internal_lab", "Track_C_advisory"})
GATING_ENUM = frozenset({"NON_GATING", "advisory", "hold_candidate"})
CONFIDENCE_ENUM = frozenset({"A", "B", "C"})


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_under_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_rag_evidence(raw: Any, *, max_items: int = 24) -> list[dict[str, Any]]:
    rows_in: list[Any]
    if isinstance(raw, list):
        rows_in = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("rag_evidence"), list):
            rows_in = raw["rag_evidence"]  # type: ignore[assignment]
        elif isinstance(raw.get("hits"), list):
            rows_in = raw["hits"]  # type: ignore[assignment]
        else:
            rows_in = []
    else:
        rows_in = []

    out: list[dict[str, Any]] = []
    for row in rows_in[:max_items]:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("source_id") or row.get("chunk_id") or row.get("id") or "").strip()
        snippet = str(row.get("snippet") or row.get("text") or row.get("body") or "").strip()
        band = str(row.get("confidence_band") or row.get("band") or "B").strip().upper()
        if band not in CONFIDENCE_ENUM:
            band = "B"
        if not sid:
            sid = "unknown_source"
        if len(snippet) > 8000:
            snippet = snippet[:8000]
        item: dict[str, Any] = {
            "source_id": sid[:512],
            "snippet": snippet,
            "confidence_band": band,
        }
        uri = row.get("uri")
        if isinstance(uri, str) and uri.strip():
            item["uri"] = uri.strip()[:2048]
        out.append(item)
    return out


def rag_evidence_from_premium_multilens_report_v1(doc: Any, *, max_items: int = 24) -> list[dict[str, Any]]:
    """Extract RAG hits from ``premium_btrack_multilens_report_v1`` lenses into bridge ``rag_evidence`` rows."""
    if not isinstance(doc, dict):
        return []
    lenses = doc.get("lenses")
    if not isinstance(lenses, list):
        return []
    out: list[dict[str, Any]] = []
    for lens in lenses:
        if len(out) >= max_items:
            break
        if not isinstance(lens, dict):
            continue
        lens_id = str(lens.get("lens_id") or "lens").strip() or "lens"
        rag = lens.get("rag")
        if not isinstance(rag, dict):
            continue
        runs = rag.get("retrieval_runs")
        if not isinstance(runs, list):
            continue
        for run in runs:
            if len(out) >= max_items:
                break
            if not isinstance(run, dict):
                continue
            run_id = str(run.get("run_id") or "run").strip() or "run"
            hits = run.get("hits")
            if not isinstance(hits, list):
                continue
            for hit in hits:
                if len(out) >= max_items:
                    break
                if not isinstance(hit, dict):
                    continue
                orig_sid = str(hit.get("source_id") or "").strip()
                if not orig_sid:
                    orig_sid = "unknown_hit"
                sid = f"premium_ml:{lens_id}:{run_id}:{orig_sid}"
                snippet = str(hit.get("snippet") or "").strip()
                if not snippet:
                    snippet = "(empty)"
                lic = hit.get("license_note")
                if isinstance(lic, str) and lic.strip():
                    extra = f"\n---\nlicense_note: {lic.strip()[:1800]}"
                    snippet = (snippet + extra)[:8000]
                else:
                    snippet = snippet[:8000]
                band = str(hit.get("confidence_band") or "B").strip().upper()
                if band not in CONFIDENCE_ENUM:
                    band = "B"
                row: dict[str, Any] = {
                    "source_id": sid[:512],
                    "snippet": snippet,
                    "confidence_band": band,
                }
                uri = hit.get("uri")
                if isinstance(uri, str) and uri.strip():
                    row["uri"] = uri.strip()[:2048]
                out.append(row)
    return out


def rag_evidence_from_philosophy_pilot_v1(doc: Any, *, max_items: int = 24) -> list[dict[str, Any]]:
    """Map `philosophy_lane_rag_pilot_v1` `blocks[]` into `rag_evidence`-shaped rows (B-band)."""
    if not isinstance(doc, dict):
        return []
    blocks = doc.get("blocks")
    if not isinstance(blocks, list):
        return []
    out: list[dict[str, Any]] = []
    for i, b in enumerate(blocks):
        if len(out) >= max_items:
            break
        if not isinstance(b, dict):
            continue
        rail = str(b.get("source_rail") or "block").replace(" ", "_")[:120]
        summary = str(b.get("summary") or "").strip()
        detail = str(b.get("detail") or "").strip()
        snippet = summary if not detail else f"{summary}\n{detail}"
        if not snippet:
            continue
        item: dict[str, Any] = {
            "source_id": f"philosophy_lane_rag_pilot:{rail}:{i}"[:512],
            "snippet": snippet[:8000],
            "confidence_band": "B",
        }
        ep = b.get("evidence_path")
        if isinstance(ep, str) and ep.strip():
            item["uri"] = ep.strip()[:2048]
        out.append(item)
    return out


def _normalize_slots(raw: Any) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        slots_in = raw
    elif isinstance(raw, dict) and isinstance(raw.get("structured_insight_slots"), list):
        slots_in = raw["structured_insight_slots"]  # type: ignore[assignment]
    else:
        return None
    out: list[dict[str, Any]] = []
    for row in slots_in[:32]:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("slot_id") or "").strip()
        text = str(row.get("text") or "").strip()
        if not sid or not text:
            continue
        slot: dict[str, Any] = {
            "slot_id": sid[:128],
            "text": text[:4000],
        }
        evi = row.get("evidence_index")
        if isinstance(evi, int) and evi >= 0:
            slot["evidence_index"] = evi
        out.append(slot)
    return out or None


def _validate_bundle(instance: dict[str, Any]) -> tuple[bool, list[str]]:
    try:
        import jsonschema
    except ImportError:
        return True, ["jsonschema not installed; skipped"]
    schema_obj = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errs: list[str] = []
    try:
        jsonschema.validate(instance=instance, schema=schema_obj)
    except jsonschema.exceptions.ValidationError as e:  # type: ignore[attr-defined]
        errs.append(str(e.message))
        return False, errs
    return True, []


def build_bundle(
    *,
    calibration_kind: str,
    calibration_artifact: Path | None,
    summary_line: str | None,
    rag_evidence: list[dict[str, Any]],
    structured_slots: list[dict[str, Any]] | None,
    lens_id: str | None,
    route_confidence: float | None,
    track: str,
    gating: str,
    hypothesis_label: str | None,
) -> dict[str, Any]:
    if calibration_kind not in CALIBRATION_KINDS:
        raise ValueError(f"calibration_kind must be one of {sorted(CALIBRATION_KINDS)}")
    if track not in TRACK_ENUM:
        raise ValueError(f"track must be one of {sorted(TRACK_ENUM)}")
    if gating not in GATING_ENUM:
        raise ValueError(f"gating must be one of {sorted(GATING_ENUM)}")

    cal: dict[str, Any] = {"kind": calibration_kind}
    if calibration_kind != "none" and calibration_artifact is not None:
        if calibration_artifact.is_file():
            cal["artifact_path_rel"] = _posix_under_root(calibration_artifact)
        elif calibration_artifact.exists():
            cal["artifact_path_rel"] = _posix_under_root(calibration_artifact)
        else:
            cal["artifact_path_rel"] = _posix_under_root(calibration_artifact)
    if summary_line:
        cal["summary_line"] = summary_line.strip()[:512]

    slots: list[dict[str, Any]]
    if structured_slots:
        slots = structured_slots
    else:
        stub = (
            f"Calibration={calibration_kind}; rag_evidence_count={len(rag_evidence)}; "
            f"generator={SCRIPT_NAME}@{SCRIPT_VERSION}."
        )
        slots = [{"slot_id": "bridge.stub", "text": stub[:4000]}]

    bundle: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": BUNDLE_VERSION,
        "generated_at_utc": _now_utc(),
        "rag_evidence": rag_evidence,
        "calibration_reference": cal,
        "structured_insight_slots": slots,
        "policy": {
            "track": track,
            "gating": gating,
            "hypothesis_label": hypothesis_label,
        },
    }

    if lens_id:
        lc = 0.5 if route_confidence is None else max(0.0, min(1.0, float(route_confidence)))
        slug = lens_id.lower().replace("-", "_")
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:64] or "lens"
        bundle["lens_route"] = {
            "lens_id": slug,
            "route_confidence_0_1": lc,
        }

    ok, errs = _validate_bundle(bundle)
    bundle["bridge_meta"] = {"validation_ok": ok, "validation_errors": errs[:32]}
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path")
    ap.add_argument(
        "--calibration-kind",
        required=True,
        choices=sorted(CALIBRATION_KINDS),
        help="Which 4D/calibration family this bridge run points at",
    )
    ap.add_argument(
        "--calibration-artifact",
        type=Path,
        default=None,
        help="Optional path to snapshot JSON (repo-relative recorded when under ROOT)",
    )
    ap.add_argument("--summary-line", type=str, default=None, help="Optional one-line audit summary")
    ap.add_argument(
        "--rag-json",
        type=Path,
        default=None,
        help="JSON file: list of hits or {rag_evidence:[...]} / {hits:[...]}",
    )
    ap.add_argument(
        "--premium-multilens-report-json",
        type=Path,
        default=None,
        help=(
            "Optional premium_btrack_multilens_report_v1 JSON; per-lens "
            "`rag.retrieval_runs[].hits[]` appended after --rag-json (cap 24 total)."
        ),
    )
    ap.add_argument(
        "--philosophy-pilot-json",
        type=Path,
        default=None,
        help=(
            "Optional philosophy_lane_rag_pilot_v1 artifact; `blocks[]` appended to "
            "rag_evidence after --rag-json and --premium-multilens-report-json (cap 24 total)."
        ),
    )
    ap.add_argument(
        "--slots-json",
        type=Path,
        default=None,
        help="JSON file: list of {slot_id,text,evidence_index?} or wrapper object",
    )
    ap.add_argument("--lens-id", type=str, default=None)
    ap.add_argument("--route-confidence", type=float, default=None)
    ap.add_argument("--track", choices=sorted(TRACK_ENUM), default="B-track")
    ap.add_argument("--gating", choices=sorted(GATING_ENUM), default="NON_GATING")
    ap.add_argument("--hypothesis-label", type=str, default="[HYPO]")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if JSON Schema validation fails (requires jsonschema)",
    )
    ap.add_argument(
        "--print-json",
        action="store_true",
        help="Print bundle JSON to stdout instead of writing --out",
    )
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    cal_path = None
    if args.calibration_artifact is not None:
        cal_path = (
            args.calibration_artifact
            if args.calibration_artifact.is_absolute()
            else ROOT / args.calibration_artifact
        )

    rag_raw = _read_json(args.rag_json) if args.rag_json else []
    if rag_raw is None and args.rag_json:
        print(json.dumps({"ok": False, "error": "rag_json_unreadable"}, ensure_ascii=False), file=sys.stderr)
        return 1
    rag_evidence = _normalize_rag_evidence(rag_raw if rag_raw is not None else [])
    if args.premium_multilens_report_json:
        pr = (
            args.premium_multilens_report_json
            if args.premium_multilens_report_json.is_absolute()
            else ROOT / args.premium_multilens_report_json
        )
        premium_doc = _read_json(pr)
        if premium_doc is None:
            print(
                json.dumps({"ok": False, "error": "premium_multilens_report_json_unreadable"}, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
        extra_p = rag_evidence_from_premium_multilens_report_v1(
            premium_doc, max_items=max(0, 24 - len(rag_evidence))
        )
        rag_evidence = (rag_evidence + extra_p)[:24]
    if args.philosophy_pilot_json:
        pj = (
            args.philosophy_pilot_json
            if args.philosophy_pilot_json.is_absolute()
            else ROOT / args.philosophy_pilot_json
        )
        pilot_doc = _read_json(pj)
        if pilot_doc is None:
            print(
                json.dumps({"ok": False, "error": "philosophy_pilot_json_unreadable"}, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
        extra = rag_evidence_from_philosophy_pilot_v1(pilot_doc, max_items=max(0, 24 - len(rag_evidence)))
        rag_evidence = (rag_evidence + extra)[:24]

    slots_raw = _read_json(args.slots_json) if args.slots_json else None
    if args.slots_json and slots_raw is None:
        print(json.dumps({"ok": False, "error": "slots_json_unreadable"}, ensure_ascii=False), file=sys.stderr)
        return 1
    slots = _normalize_slots(slots_raw)

    hypo = args.hypothesis_label.strip() if args.hypothesis_label else None
    if hypo == "":
        hypo = None

    try:
        bundle = build_bundle(
            calibration_kind=args.calibration_kind,
            calibration_artifact=cal_path,
            summary_line=args.summary_line,
            rag_evidence=rag_evidence,
            structured_slots=slots,
            lens_id=args.lens_id,
            route_confidence=args.route_confidence,
            track=args.track,
            gating=args.gating,
            hypothesis_label=hypo,
        )
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    meta = bundle.get("bridge_meta") or {}
    if args.strict and not meta.get("validation_ok"):
        print(json.dumps({"ok": False, "bundle": bundle}, ensure_ascii=False), file=sys.stderr)
        return 2

    text = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    if args.print_json:
        sys.stdout.write(text)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": None if args.print_json else str(out_path),
                "validation_ok": meta.get("validation_ok"),
                "rag_evidence_count": len(rag_evidence),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
