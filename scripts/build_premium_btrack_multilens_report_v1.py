#!/usr/bin/env python3
"""
Premium B-track multi-lens report packager (v0).

Sync-only, stub lens workers (example JSON), structural coordinator join,
disk MD + JSON matching premium_btrack_multilens_report_v1 schema.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    env = (Path(__file__).resolve().parent.parent).resolve()
    raw = os.environ.get("MKM_WORKSPACE_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return env


def _utc_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _posix_under_root(path: Path, root: Path) -> str:
    rp = path.resolve()
    rr = root.resolve()
    try:
        return rp.relative_to(rr).as_posix()
    except ValueError:
        return rp.as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_example(example_path: Path) -> dict[str, Any]:
    return json.loads(example_path.read_text(encoding="utf-8"))


def stub_lens_workers(example: dict[str, Any]) -> list[dict[str, Any]]:
    """v0: return lens blocks from packaged example (no network / no engines)."""
    lenses = example.get("lenses")
    if not isinstance(lenses, list) or not lenses:
        raise ValueError("example.lenses must be a non-empty list")
    return copy.deepcopy(lenses)


def stub_coordinator_block(example: dict[str, Any]) -> dict[str, Any]:
    coord = example.get("coordinator")
    if not isinstance(coord, dict):
        raise ValueError("example.coordinator must be an object")
    return copy.deepcopy(coord)


def render_lens_slice_md(lens: dict[str, Any]) -> str:
    lid = str(lens.get("lens_id", "unknown"))
    lines: list[str] = [
        f"## Lens `{lid}` (v0 stub / example-backed)",
        "",
    ]
    tags = lens.get("hypothesis_tags")
    if isinstance(tags, list) and tags:
        lines.append(f"- hypothesis_tags: {', '.join(str(t) for t in tags)}")
    eng = lens.get("engine_artifact_paths")
    if isinstance(eng, list) and eng:
        lines.append("- engine_artifact_paths:")
        for p in eng:
            lines.append(f"  - `{p}`")
    rag = lens.get("rag")
    if isinstance(rag, dict):
        cid = rag.get("corpus_id", "")
        lines.append(f"- rag.corpus_id: `{cid}`")
        runs = rag.get("retrieval_runs")
        if isinstance(runs, list):
            for run in runs:
                if not isinstance(run, dict):
                    continue
                rid = run.get("run_id", "")
                q = str(run.get("query", ""))
                lines.append(f"  - run `{rid}` query: {q}")
                hits = run.get("hits")
                if isinstance(hits, list):
                    for hit in hits[:24]:
                        if not isinstance(hit, dict):
                            continue
                        sid = hit.get("source_id", "")
                        band = hit.get("confidence_band", "")
                        snip = str(hit.get("snippet", ""))[:400]
                        lines.append(f"    - `{sid}` band={band} snippet: {snip}")
    lines.append("")
    lines.append("_This slice is v0 stub content copied from schema example hits._")
    lines.append("")
    return "\n".join(lines)


def render_synthesis_md(coordinator: dict[str, Any], lens_ids: list[str]) -> str:
    lines: list[str] = [
        "## Coordinator synthesis (v0 structural join)",
        "",
        f"- coordinator_mode_label: `{coordinator.get('coordinator_mode_label', '')}`",
        f"- lens_order: {', '.join(lens_ids)}",
        "",
    ]
    conflicts = coordinator.get("conflicts")
    if isinstance(conflicts, list):
        for row in conflicts:
            if not isinstance(row, dict):
                continue
            topic = row.get("topic", "")
            lines.append(f"### Conflict: {topic}")
            for k in ("myeongni_note", "sasang_note", "logos_note"):
                v = row.get(k)
                if v:
                    lines.append(f"- {k}: {v}")
            res = row.get("resolution_advisory", "")
            if res:
                lines.append(f"- **resolution_advisory**: {res}")
            lines.append("")
    caveats = coordinator.get("caveats")
    if isinstance(caveats, list) and caveats:
        lines.append("### Caveats")
        for c in caveats:
            lines.append(f"- {c}")
        lines.append("")
    return "\n".join(lines)


def render_package_md(
    report: dict[str, Any],
    slice_contents: dict[str, str],
    synthesis_text: str,
) -> str:
    tw = report.get("track_wall", [])
    tw_s = ", ".join(str(x) for x in tw) if isinstance(tw, list) else str(tw)
    ns = report.get("non_scope_ack", {})
    lines: list[str] = [
        "<!-- premium_btrack_multilens_report_v0 -->",
        "",
        "# Premium B-track multi-lens report (v0)",
        "",
        "> **Track**: B-track research / `[HYPO]`",
        f"> **track_wall**: `{tw_s}`",
        "",
        "## Fact-Lock banner (non_scope_ack)",
        "",
        f"- not_clinical_diagnosis: `{ns.get('not_clinical_diagnosis')}`",
        f"- not_live_trading: `{ns.get('not_live_trading')}`",
        f"- not_regime_autotrigger: `{ns.get('not_regime_autotrigger')}`",
        f"- logos_non_gating: `{ns.get('logos_non_gating')}`",
        "",
        "---",
        "",
        "## Per-lens slices (embedded for v0 single-file review)",
        "",
    ]
    for lid, body in slice_contents.items():
        lines.append(f"<a id=\"lens-{lid}\"></a>")
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Coordinator bundle")
    lines.append("")
    lines.append(synthesis_text)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Disclaimers")
    lines.append("")
    dis = report.get("disclaimers")
    if isinstance(dis, list):
        for d in dis:
            lines.append(f"- {d}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_End of report. v0 uses example-backed RAG stubs; replace workers incrementally._")
    lines.append("")
    return "\n".join(lines)


def _maybe_validate(instance: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        print("WARN: jsonschema not installed; skip schema validation.", file=sys.stderr)
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def build_report(
    *,
    root: Path,
    out_dir: Path,
    example_path: Path,
    validate_schema: bool,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    example = _load_example(example_path)
    lenses = stub_lens_workers(example)
    coord = stub_coordinator_block(example)

    lens_ids = [str(x.get("lens_id", "")) for x in lenses if isinstance(x, dict)]

    slice_paths: dict[str, Path] = {}
    slice_contents: dict[str, str] = {}
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", "unknown"))
        body = render_lens_slice_md(lens)
        slice_contents[lid] = body
        p = out_dir / f"lens_{lid}_premium_slice_v0.md"
        p.write_text(body, encoding="utf-8")
        slice_paths[lid] = p
        if lens.get("sections") and isinstance(lens["sections"], list) and lens["sections"]:
            sec0 = lens["sections"][0]
            if isinstance(sec0, dict):
                sec0["markdown_path"] = _posix_under_root(p, root)

    synthesis_text = render_synthesis_md(coord, lens_ids)
    synthesis_path = out_dir / "premium_multilens_synthesis_v0.md"
    synthesis_path.write_text(synthesis_text, encoding="utf-8")
    coord["synthesis_markdown_path"] = _posix_under_root(synthesis_path, root)

    report = copy.deepcopy(example)
    report["generated_at_utc"] = _utc_z()
    report.pop("async_job", None)
    report["lenses"] = lenses
    report["coordinator"] = coord

    main_md_path = out_dir / "premium_btrack_multilens_report_v1.md"
    main_json_path = out_dir / "premium_btrack_multilens_report_v1.json"

    package_md = render_package_md(report, slice_contents, synthesis_text)
    main_md_path.write_text(package_md, encoding="utf-8")
    md_hash = _sha256_bytes(main_md_path.read_bytes())

    report["package_artifacts"] = {
        "report_json_path": _posix_under_root(main_json_path, root),
        "report_markdown_path": _posix_under_root(main_md_path, root),
        "manifest_sha256": md_hash,
    }

    pl = report.get("pipeline")
    if isinstance(pl, list):
        for step in pl:
            if not isinstance(step, dict):
                continue
            outs = step.get("outputs")
            if not isinstance(outs, list):
                continue
            new_outs: list[str] = []
            for o in outs:
                if o.endswith("premium_btrack_multilens_report_v1.json"):
                    new_outs.append(_posix_under_root(main_json_path, root))
                elif o.endswith("premium_btrack_multilens_report_v1.md"):
                    new_outs.append(_posix_under_root(main_md_path, root))
                else:
                    new_outs.append(str(o))
            step["outputs"] = new_outs

    main_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    schema_path = root / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.schema.json"
    if validate_schema:
        _maybe_validate(report, schema_path)

    print(f"OK: wrote {_posix_under_root(main_md_path, root)}")
    print(f"OK: wrote {_posix_under_root(main_json_path, root)}")
    return 0


def main() -> int:
    root = _repo_root()
    default_example = root / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.example.json"
    default_out = root / "reports"

    ap = argparse.ArgumentParser(description="Build premium B-track multi-lens report package (v0 stub).")
    ap.add_argument("--out-dir", type=Path, default=default_out, help="Output directory (default: reports/)")
    ap.add_argument("--example-path", type=Path, default=default_example, help="Stub source JSON (default: schema example)")
    ap.add_argument("--no-validate", action="store_true", help="Skip jsonschema validation when available")
    args = ap.parse_args()

    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = (root / out_dir).resolve()

    example_path = args.example_path
    if not example_path.is_absolute():
        example_path = (root / example_path).resolve()

    if not example_path.is_file():
        print(f"ERROR: example not found: {example_path}", file=sys.stderr)
        return 2

    return build_report(
        root=root,
        out_dir=out_dir,
        example_path=example_path,
        validate_schema=not args.no_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
