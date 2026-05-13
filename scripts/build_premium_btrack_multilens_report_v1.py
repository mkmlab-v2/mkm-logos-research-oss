#!/usr/bin/env python3
"""
Premium B-track multi-lens report packager (v0 / v0.5).

Sync-only: stub lens workers from schema example; optional `--mode best-effort`
ingests independent-lens JSON from disk; optional tracked **offline RAG bundle**
(keyword hits over `tests/fixtures/premium_multilens_rag_corpus_bundle_v1.json`, no API).

Structural coordinator join, disk MD + JSON matching premium_btrack_multilens_report_v1 schema.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Mode = Literal["stub", "best-effort"]


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


def _load_rag_bundle(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _rag_query_chunks_from_blob(lens_id: str, blob: dict[str, Any]) -> str:
    chunks: list[str] = []
    note = blob.get("note")
    if note:
        chunks.append(str(note))
    sc = blob.get("scores")
    if isinstance(sc, dict):
        chunks.append(json.dumps(sc, ensure_ascii=False))
    mso = blob.get("myeongri_stream_outputs")
    if isinstance(mso, dict):
        chunks.append(str(mso.get("rationale", "")))
    sso = blob.get("sasang_stream_outputs")
    if isinstance(sso, dict):
        chunks.append(str(sso.get("rationale", "")))
    lso = blob.get("logos_stream_outputs")
    if isinstance(lso, dict):
        chunks.append(str(lso.get("rationale", "")))
    nsg = blob.get("narrative_snippet_guarded")
    if nsg:
        chunks.append(str(nsg))
    q = " ".join(chunks).strip()
    return q if q else f"{lens_id} B-track offline RAG query"


def _rag_query_tokens(q: str) -> list[str]:
    tokens = re.findall(r"[\w가-힣]{3,}", q.lower())
    seen: set[str] = set()
    uniq: list[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
        if len(uniq) >= 24:
            break
    return uniq


def _score_doc(tokens: list[str], text: str) -> int:
    tl = text.lower()
    return sum(1 for t in tokens if t in tl)


def _build_rag_from_bundle_entries(
    *,
    lens_id: str,
    disk_blob: dict[str, Any],
    entries: list[dict[str, Any]],
    max_hits: int = 5,
) -> dict[str, Any] | None:
    q_line = _rag_query_chunks_from_blob(lens_id, disk_blob)[:4000]
    tokens = _rag_query_tokens(q_line)
    if not entries:
        return None
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in entries:
        if not isinstance(doc, dict):
            continue
        text = str(doc.get("text", ""))
        sid = str(doc.get("source_id", "unknown"))
        sc = _score_doc(tokens, text)
        if sc > 0:
            scored.append((sc, doc))
    scored.sort(key=lambda x: (-x[0], x[1].get("source_id", "")))
    if not scored:
        scored = [(0, e) for e in entries if isinstance(e, dict)][:max_hits]
    if not scored:
        return None
    hits: list[dict[str, Any]] = []
    for i, (_sc, doc) in enumerate(scored[:max_hits]):
        band = "A" if i == 0 else ("B" if i < 3 else "C")
        text = str(doc.get("text", ""))
        hit: dict[str, Any] = {
            "source_id": str(doc.get("source_id", "unknown"))[:512],
            "snippet": (text[:7800] if text else "(empty)")[:8000],
            "confidence_band": band,
        }
        uri = doc.get("uri")
        if isinstance(uri, str) and uri.strip():
            hit["uri"] = uri[:2048]
        lic = doc.get("license_note")
        if isinstance(lic, str) and lic.strip():
            hit["license_note"] = lic[:2000]
        hits.append(hit)
    return {
        "corpus_id": "premium_multilens_rag_disk_bundle_v1",
        "retrieval_runs": [
            {
                "run_id": f"disk_kw_{lens_id}_v1",
                "query": q_line,
                "hits": hits,
            }
        ],
    }


def enrich_lenses_rag_from_disk_bundle(
    *,
    mode: Mode,
    root: Path,
    lenses: list[dict[str, Any]],
    disk_blobs: dict[str, dict[str, Any] | None],
    bundle_path: Path | None,
) -> str | None:
    """Replace lens['rag'] with offline keyword retrieval when bundle loads. Returns relative bundle path or None."""
    if mode != "best-effort" or bundle_path is None or not bundle_path.is_file():
        return None
    bundle = _load_rag_bundle(bundle_path)
    if not bundle:
        return None
    ent_root = bundle.get("entries")
    if not isinstance(ent_root, dict):
        return None
    used = False
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        blob = (disk_blobs or {}).get(lid)
        if not isinstance(blob, dict):
            continue
        raw = ent_root.get(lid)
        if not isinstance(raw, list) or not raw:
            continue
        rag = _build_rag_from_bundle_entries(lens_id=lid, disk_blob=blob, entries=raw, max_hits=5)
        if rag and isinstance(rag.get("retrieval_runs"), list) and rag["retrieval_runs"]:
            lens["rag"] = rag
            used = True
    if not used:
        return None
    return _posix_under_root(bundle_path, root)


def default_independent_lens_paths(root: Path) -> dict[str, Path]:
    art = root / "docs" / "final" / "artifacts"
    return {
        "myeongni": art / "myeongni_independent_lens_latest.json",
        "sasang": art / "sasang_independent_lens_latest.json",
        "logos": art / "logos_independent_lens_latest.json",
    }


def attach_disk_engine_paths(
    *,
    root: Path,
    lenses: list[dict[str, Any]],
    mode: Mode,
    overrides: dict[str, Path],
) -> dict[str, dict[str, Any] | None]:
    """When mode=best-effort, set engine_artifact_paths from disk and return blobs per lens_id."""
    blobs: dict[str, dict[str, Any] | None] = {}
    if mode != "best-effort":
        for lens in lenses:
            if isinstance(lens, dict) and lens.get("lens_id"):
                blobs[str(lens["lens_id"])] = None
        return blobs

    defaults = default_independent_lens_paths(root)
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        if lid not in defaults:
            blobs[lid] = None
            continue
        path = overrides.get(lid) or defaults[lid]
        path = path.resolve()
        if not path.is_file():
            print(f"WARN: best-effort missing artifact for lens={lid}: {path}", file=sys.stderr)
            blobs[lid] = None
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARN: best-effort failed to read JSON lens={lid}: {e}", file=sys.stderr)
            blobs[lid] = None
            continue
        lens["engine_artifact_paths"] = [_posix_under_root(path, root)]
        blobs[lid] = data
    return blobs


def _disk_snapshot_lines_myeongni(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    mso = blob.get("myeongri_stream_outputs")
    if isinstance(mso, dict):
        lines.append(f"- myeongri_stream_outputs.state_id: {mso.get('state_id')}")
        rat = str(mso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- myeongri_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def _disk_snapshot_lines_sasang(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    sso = blob.get("sasang_stream_outputs")
    if isinstance(sso, dict):
        lines.append(f"- sasang_stream_outputs.regime_hypothesis: `{sso.get('regime_hypothesis')}`")
        lines.append(f"- sasang_stream_outputs.mapping_target: `{sso.get('mapping_target')}`")
        rat = str(sso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- sasang_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def _disk_snapshot_lines_logos(blob: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        f"- artifact.schema: `{blob.get('schema')}` version=`{blob.get('version')}` ts=`{blob.get('ts_utc')}`",
    ]
    sc = blob.get("scores")
    if isinstance(sc, dict):
        lines.append(f"- scores.direction_score: {sc.get('direction_score')}")
        lines.append(f"- scores.confidence: {sc.get('confidence')}")
    refs = blob.get("evidence_refs")
    if isinstance(refs, list):
        lines.append(f"- evidence_refs.count: {len(refs)}")
    nsg = blob.get("narrative_snippet_guarded")
    if isinstance(nsg, str) and nsg:
        lines.append(f"- narrative_snippet_guarded (trim): {nsg[:400]}")
    lso = blob.get("logos_stream_outputs")
    if isinstance(lso, dict):
        rat = str(lso.get("rationale", ""))[:520]
        if rat:
            lines.append(f"- logos_stream_outputs.rationale (trim): {rat}")
    prov = blob.get("provenance")
    if isinstance(prov, dict):
        lines.append(f"- provenance.source: `{prov.get('source')}`")
    note = blob.get("note")
    if note:
        lines.append(f"- engine.note: {note}")
    return lines


def disk_snapshot_lines(lens_id: str, blob: dict[str, Any]) -> list[str]:
    if lens_id == "myeongni":
        return _disk_snapshot_lines_myeongni(blob)
    if lens_id == "sasang":
        return _disk_snapshot_lines_sasang(blob)
    if lens_id == "logos":
        return _disk_snapshot_lines_logos(blob)
    return [f"- (no summarizer for lens_id={lens_id!r})"]


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


def render_lens_slice_md(lens: dict[str, Any], disk_blob: dict[str, Any] | None) -> str:
    lid = str(lens.get("lens_id", "unknown"))
    mode_label = "stub + disk snapshot" if disk_blob is not None else "v0 stub / example-backed"
    lines: list[str] = [
        f"## Lens `{lid}` ({mode_label})",
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
    corpus_id = ""
    if isinstance(rag, dict):
        corpus_id = str(rag.get("corpus_id", "") or "")
        lines.append(f"- rag.corpus_id: `{corpus_id}`")
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
    if disk_blob is not None:
        lines.append("")
        lines.append("### Disk engine snapshot (best-effort, independent-lens JSON)")
        lines.extend(disk_snapshot_lines(lid, disk_blob))
    lines.append("")
    if corpus_id == "premium_multilens_rag_disk_bundle_v1":
        lines.append(
            "_RAG hits above: offline keyword bundle over tracked fixtures / optional `--rag-bundle`; "
            "not live corpus or embedding search._"
        )
    else:
        lines.append(
            "_RAG rows above: schema-example stubs unless `--mode best-effort` with a valid `--rag-bundle`._"
        )
    lines.append("")
    return "\n".join(lines)


def render_synthesis_md(
    coordinator: dict[str, Any],
    lens_ids: list[str],
    disk_blobs: dict[str, dict[str, Any] | None] | None,
) -> str:
    lines: list[str] = [
        "## Coordinator synthesis (v0 structural join)",
        "",
        f"- coordinator_mode_label: `{coordinator.get('coordinator_mode_label', '')}`",
        f"- lens_order: {', '.join(lens_ids)}",
        "",
    ]
    if disk_blobs:
        rows: list[str] = []
        for lid in lens_ids:
            b = disk_blobs.get(lid)
            if not isinstance(b, dict):
                rows.append(f"| `{lid}` | (no disk) | (no disk) |")
                continue
            sc = b.get("scores") if isinstance(b.get("scores"), dict) else {}
            d = sc.get("direction_score")
            c = sc.get("confidence")
            rows.append(f"| `{lid}` | {d} | {c} |")
        if any("no disk" not in r for r in rows):
            lines.append("### Numeric alignment (disk `scores`, B-track)")
            lines.append("")
            lines.append("| lens | direction_score | confidence |")
            lines.append("| --- | ---: | ---: |")
            lines.extend(rows)
            lines.append("")
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
    *,
    mode: Mode,
) -> str:
    tw = report.get("track_wall", [])
    tw_s = ", ".join(str(x) for x in tw) if isinstance(tw, list) else str(tw)
    ns = report.get("non_scope_ack", {})
    lines: list[str] = [
        "<!-- premium_btrack_multilens_report_v0 -->",
        "",
        f"# Premium B-track multi-lens report ({'v0.5 best-effort disk' if mode == 'best-effort' else 'v0 stub'})",
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
    if mode == "best-effort":
        lines.append(
            "_End of report. v0.5: independent-lens JSON on disk merged into MD; "
            "RAG/API workers and async queue still TBD._"
        )
    else:
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


def _insert_best_effort_caveat(
    *,
    mode: Mode,
    coord: dict[str, Any],
    lenses: list[dict[str, Any]],
    disk_blobs: dict[str, dict[str, Any] | None],
    rag_bundle_rel: str | None = None,
) -> None:
    if mode != "best-effort":
        return
    trace_parts: list[str] = []
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", ""))
        if (disk_blobs or {}).get(lid) is None:
            trace_parts.append(f"{lid}=MISSING")
            continue
        paths = lens.get("engine_artifact_paths")
        if isinstance(paths, list) and paths:
            trace_parts.append(f"{lid}={' '.join(str(p) for p in paths)}")
        else:
            trace_parts.append(f"{lid}=LOADED_NO_PATH")
    line = "Fact-Lock trace (best-effort disk ingest): " + " | ".join(trace_parts)
    if len(line) > 1950:
        line = line[:1947] + "..."
    caveats = coord.get("caveats")
    if not isinstance(caveats, list):
        caveats = []
        coord["caveats"] = caveats
    caveats.insert(0, line)
    if rag_bundle_rel:
        rag_line = (
            f"RAG (offline keyword bundle): `{rag_bundle_rel}` — "
            "not neural/API RAG; ranked by token overlap with disk lens blob text."
        )
        if len(rag_line) > 1950:
            rag_line = rag_line[:1947] + "..."
        caveats.insert(1, rag_line)


def _finalize_pipeline_outputs(
    pipeline: list[Any],
    *,
    mode: Mode,
    root: Path,
    slice_paths: dict[str, Path],
    synthesis_path: Path,
    main_json_path: Path,
    main_md_path: Path,
) -> None:
    """Point pipeline steps at real on-disk outputs; step 1 script_ref gets mode tag in best-effort."""
    if not isinstance(pipeline, list):
        return

    owner_outputs: dict[str, list[str]] = {}
    for lid, pth in slice_paths.items():
        owner_outputs[lid] = [_posix_under_root(pth, root)]
    owner_outputs["coordinator"] = [_posix_under_root(synthesis_path, root)]

    for step in pipeline:
        if not isinstance(step, dict):
            continue
        own = step.get("owner")
        if own in owner_outputs:
            step["outputs"] = list(owner_outputs[str(own)])
        if mode == "best-effort" and step.get("step") == 1 and own == "orchestrator":
            prev = str(step.get("script_ref", "")).strip()
            tag = " [actual_mode=best-effort]"
            merged = (prev + tag).strip()
            if len(merged) > 1024:
                merged = merged[:1021] + "..."
            step["script_ref"] = merged

        outs = step.get("outputs")
        if not isinstance(outs, list):
            continue
        new_outs: list[str] = []
        for o in outs:
            if isinstance(o, str) and o.endswith("premium_btrack_multilens_report_v1.json"):
                new_outs.append(_posix_under_root(main_json_path, root))
            elif isinstance(o, str) and o.endswith("premium_btrack_multilens_report_v1.md"):
                new_outs.append(_posix_under_root(main_md_path, root))
            else:
                new_outs.append(str(o))
        step["outputs"] = new_outs


def build_report(
    *,
    root: Path,
    out_dir: Path,
    example_path: Path,
    validate_schema: bool,
    mode: Mode = "stub",
    artifact_overrides: dict[str, Path] | None = None,
    rag_bundle_path: Path | None = None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    main_md_path = out_dir / "premium_btrack_multilens_report_v1.md"
    main_json_path = out_dir / "premium_btrack_multilens_report_v1.json"

    example = _load_example(example_path)
    lenses = stub_lens_workers(example)
    coord = stub_coordinator_block(example)

    overrides = artifact_overrides or {}
    disk_blobs = attach_disk_engine_paths(root=root, lenses=lenses, mode=mode, overrides=overrides)

    rag_bundle_rel = enrich_lenses_rag_from_disk_bundle(
        mode=mode,
        root=root,
        lenses=lenses,
        disk_blobs=disk_blobs,
        bundle_path=rag_bundle_path,
    )
    _insert_best_effort_caveat(
        mode=mode,
        coord=coord,
        lenses=lenses,
        disk_blobs=disk_blobs,
        rag_bundle_rel=rag_bundle_rel,
    )

    lens_ids = [str(x.get("lens_id", "")) for x in lenses if isinstance(x, dict)]

    slice_paths: dict[str, Path] = {}
    slice_contents: dict[str, str] = {}
    for lens in lenses:
        if not isinstance(lens, dict):
            continue
        lid = str(lens.get("lens_id", "unknown"))
        blob = disk_blobs.get(lid) if disk_blobs else None
        body = render_lens_slice_md(lens, blob)
        slice_contents[lid] = body
        p = out_dir / f"lens_{lid}_premium_slice_v0.md"
        p.write_text(body, encoding="utf-8")
        slice_paths[lid] = p
        if lens.get("sections") and isinstance(lens["sections"], list) and lens["sections"]:
            sec0 = lens["sections"][0]
            if isinstance(sec0, dict):
                sec0["markdown_path"] = _posix_under_root(p, root)

    synthesis_path = out_dir / "premium_multilens_synthesis_v0.md"
    synthesis_text = render_synthesis_md(coord, lens_ids, disk_blobs if mode == "best-effort" else None)
    synthesis_path.write_text(synthesis_text, encoding="utf-8")
    coord["synthesis_markdown_path"] = _posix_under_root(synthesis_path, root)

    report = copy.deepcopy(example)
    report["generated_at_utc"] = _utc_z()
    report.pop("async_job", None)
    report["lenses"] = lenses
    report["coordinator"] = coord

    package_md = render_package_md(report, slice_contents, synthesis_text, mode=mode)
    main_md_path.write_text(package_md, encoding="utf-8")
    md_hash = _sha256_bytes(main_md_path.read_bytes())

    report["package_artifacts"] = {
        "report_json_path": _posix_under_root(main_json_path, root),
        "report_markdown_path": _posix_under_root(main_md_path, root),
        "manifest_sha256": md_hash,
    }

    pl = report.get("pipeline")
    if isinstance(pl, list):
        _finalize_pipeline_outputs(
            pl,
            mode=mode,
            root=root,
            slice_paths=slice_paths,
            synthesis_path=synthesis_path,
            main_json_path=main_json_path,
            main_md_path=main_md_path,
        )

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
    ap.add_argument(
        "--mode",
        choices=("stub", "best-effort"),
        default="stub",
        help="stub=example only; best-effort=attach independent-lens JSON from disk (defaults under docs/final/artifacts/).",
    )
    ap.add_argument("--myeongni-json", type=Path, default=None, help="Override myeongni independent-lens JSON path")
    ap.add_argument("--sasang-json", type=Path, default=None, help="Override sasang independent-lens JSON path")
    ap.add_argument("--logos-json", type=Path, default=None, help="Override logos independent-lens JSON path")
    ap.add_argument(
        "--rag-bundle",
        type=Path,
        default=None,
        help="Offline keyword RAG corpus bundle JSON (default: tests/fixtures/premium_multilens_rag_corpus_bundle_v1.json if present).",
    )
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

    overrides: dict[str, Path] = {}
    for key, arg in (
        ("myeongni", args.myeongni_json),
        ("sasang", args.sasang_json),
        ("logos", args.logos_json),
    ):
        if arg is None:
            continue
        p = Path(arg)
        if not p.is_absolute():
            p = (root / p).resolve()
        overrides[key] = p

    mode: Mode = "best-effort" if args.mode == "best-effort" else "stub"

    rag_bundle: Path | None = None
    if args.rag_bundle is not None:
        rb = Path(args.rag_bundle)
        if not rb.is_absolute():
            rb = (root / rb).resolve()
        rag_bundle = rb if rb.is_file() else None
        if args.rag_bundle is not None and rag_bundle is None:
            print(f"WARN: --rag-bundle not found, skipping offline RAG: {rb}", file=sys.stderr)
    else:
        cand = root / "tests" / "fixtures" / "premium_multilens_rag_corpus_bundle_v1.json"
        if cand.is_file():
            rag_bundle = cand

    return build_report(
        root=root,
        out_dir=out_dir,
        example_path=example_path,
        validate_schema=not args.no_validate,
        mode=mode,
        artifact_overrides=overrides or None,
        rag_bundle_path=rag_bundle,
    )


if __name__ == "__main__":
    raise SystemExit(main())
