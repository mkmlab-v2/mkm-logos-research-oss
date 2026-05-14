#!/usr/bin/env python3
"""
Create an Agent Search (Discovery Engine) data store and kick off a GCS document import.

Replaces fragile Cloud Console wizard clicks with API calls. One-time setup on the machine:

  pip install "google-cloud-discoveryengine>=0.11.0" "google-cloud-storage>=2.14.0"
  gcloud auth application-default login
  gcloud config set project YOUR_PROJECT_ID

Enable API (once per project):

  gcloud services enable discoveryengine.googleapis.com --project=YOUR_PROJECT_ID

IAM: account used by ADC needs roles such as Discovery Engine Admin (or Editor) on the project,
and Storage Object Viewer on the GCS bucket/prefix.

Docs (official samples):
  https://cloud.google.com/generative-ai-app-builder/docs/create-data-store-es
  https://cloud.google.com/generative-ai-app-builder/docs/samples/genappbuilder-import-documents-gcs

Search engine (binds one data store for Discovery Search UI / API):

  py scripts/bootstrap_agent_search_datastore_gcs_v1.py --project ... --engine-only

  Or after import: add --create-search-engine to also call EngineServiceClient.create_engine.
  Use google.cloud.discoveryengine_v1 (not the umbrella import) for EngineServiceClient to avoid
  v1/v1beta type mismatches.

After import + engine (ADC + APIs enabled): smoke query
  ``py scripts/query_agent_search_engine_v1.py --project … --engine-id …``;
explicit RAG + Vertex Gemini (or ``--skip-gemini``)
  ``py scripts/run_vertex_gemini_agent_search_context_v1.py``;
Windows wrapper ``scripts/Run-VertexGeminiAgentSearchContextSmoke_v1.ps1``
  (optional ``-ImportDocumentsFirst`` runs this script with ``--skip-create`` first when new PDFs were uploaded to GCS only).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional


def _default_data_store_id(project: str) -> str:
    """Stable-ish default from project id (Discovery Engine id rules: [a-z0-9-]+)."""
    s = project.lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    # Keep short; must start with letter for some UIs — prefix with literal.
    tail = s[:32].strip("-") or "project"
    return f"b2g-rag-{tail}"


def _default_engine_id(project: str) -> str:
    s = project.lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    tail = s[:32].strip("-") or "project"
    return f"b2g-search-{tail}"


def _pick_gcs_uri_from_bucket(project: str, bucket: str, *, max_scan: int = 2000) -> Optional[str]:
    """First PDF under bucket → gs://bucket/dir/*.pdf ; dir '' → gs://bucket/*.pdf"""
    try:
        from google.cloud import storage
    except ImportError:
        print(
            "For --bucket / --auto-pick-prefix install:\n"
            '  py -m pip install "google-cloud-storage>=2.14.0"\n',
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    client = storage.Client(project=project)
    b = client.bucket(bucket)
    first_pdf: Optional[str] = None
    for blob in client.list_blobs(b, max_results=max_scan):
        name = blob.name
        if name.lower().endswith(".pdf"):
            first_pdf = name
            break
    if not first_pdf:
        print(
            f"No .pdf found in gs://{bucket}/ (scanned up to {max_scan} objects). "
            "Upload PDFs or pass --gcs-uri explicitly.",
            file=sys.stderr,
        )
        return None
    dirpart = os.path.dirname(first_pdf).replace("\\", "/")
    if dirpart:
        prefix = dirpart.rstrip("/") + "/"
        return f"gs://{bucket}/{prefix}*.pdf"
    return f"gs://{bucket}/*.pdf"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True, help="GCP project id, e.g. mkm-lab-agi-2025")
    p.add_argument(
        "--location",
        default="global",
        help='Discovery Engine location (default: "global")',
    )
    p.add_argument(
        "--data-store-id",
        default="",
        help="Data store id (default: derived from --project, e.g. b2g-rag-mkm-lab-agi-2025)",
    )
    p.add_argument(
        "--display-name",
        default="",
        help="Human-readable name (default: same as data store id)",
    )
    p.add_argument(
        "--gcs-uri",
        default="",
        help="GCS prefix or glob for unstructured docs (e.g. gs://b/pdfs/*.pdf). "
        "Omit with --bucket (see --auto-pick-prefix / --gcs-prefix).",
    )
    p.add_argument(
        "--bucket",
        default="",
        help="GCS bucket name only. With --auto-pick-prefix, URI is inferred from first PDF. "
        "Otherwise combined with --gcs-prefix (default prefix: agent-search-docs/).",
    )
    p.add_argument(
        "--gcs-prefix",
        default="agent-search-docs/",
        help='When --bucket is set and --auto-pick-prefix is off: import glob '
        'gs://<bucket>/<gcs-prefix>*.pdf (default: agent-search-docs/)',
    )
    p.add_argument(
        "--auto-pick-prefix",
        action="store_true",
        help="With --bucket: scan bucket for the first .pdf and use its directory + *.pdf",
    )
    p.add_argument(
        "--skip-create",
        action="store_true",
        help="Only run import (data store must already exist)",
    )
    p.add_argument(
        "--skip-import",
        action="store_true",
        help="Only create the data store (no GCS import)",
    )
    p.add_argument(
        "--reconciliation-mode",
        choices=("INCREMENTAL", "FULL"),
        default="INCREMENTAL",
        help="Import reconciliation mode (default: INCREMENTAL)",
    )
    p.add_argument(
        "--create-search-engine",
        action="store_true",
        help="After import, create a Discovery Search engine linked to this data store (v1 API).",
    )
    p.add_argument(
        "--engine-only",
        action="store_true",
        help="Only create the search engine (no data store / no GCS import). Implies --skip-create --skip-import.",
    )
    p.add_argument(
        "--engine-id",
        default="",
        help="Search engine id (default: derived from --project, e.g. b2g-search-mkm-lab-agi-2025)",
    )
    p.add_argument(
        "--search-engine-display-name",
        default="",
        help="Engine display name (default: B2G search + project id)",
    )
    ns = p.parse_args()
    if ns.engine_only:
        ns.skip_create = True
        ns.skip_import = True
        ns.create_search_engine = True
    if ns.engine_only or ns.create_search_engine:
        if not ns.data_store_id:
            ns.data_store_id = _default_data_store_id(ns.project)
        if not ns.engine_id:
            ns.engine_id = _default_engine_id(ns.project)
        if not ns.search_engine_display_name:
            ns.search_engine_display_name = f"B2G search ({ns.project})"
    if not ns.engine_only:
        if not ns.gcs_uri and not ns.bucket:
            p.error("Provide --gcs-uri, or --bucket (with optional --auto-pick-prefix / --gcs-prefix).")
        if ns.gcs_uri and ns.bucket:
            p.error("Use either --gcs-uri or --bucket, not both.")
        if ns.gcs_uri and ns.auto_pick_prefix:
            p.error("--auto-pick-prefix requires --bucket (omit --gcs-uri).")
        if ns.auto_pick_prefix and not ns.bucket:
            p.error("--auto-pick-prefix requires --bucket.")
        if not ns.data_store_id:
            ns.data_store_id = _default_data_store_id(ns.project)
        if not ns.gcs_uri:
            assert ns.bucket
            if ns.auto_pick_prefix:
                picked = _pick_gcs_uri_from_bucket(ns.project, ns.bucket)
                if not picked:
                    p.error(
                        "No PDF under bucket; upload at least one .pdf or pass --gcs-uri explicitly."
                    )
                ns.gcs_uri = picked
            else:
                pre = ns.gcs_prefix.strip("/")
                if pre:
                    ns.gcs_uri = f"gs://{ns.bucket}/{pre}/*.pdf"
                else:
                    ns.gcs_uri = f"gs://{ns.bucket}/*.pdf"
        print(f"Resolved --data-store-id={ns.data_store_id!r} --gcs-uri={ns.gcs_uri!r}")
    else:
        print(
            f"Engine-only: --data-store-id={ns.data_store_id!r} --engine-id={ns.engine_id!r} "
            f"--search-engine-display-name={ns.search_engine_display_name!r}"
        )
    return ns


def _run_create_search_engine(
    project: str,
    location: str,
    data_store_id: str,
    engine_id: str,
    display_name: str,
) -> None:
    from google.api_core import exceptions as gexc
    from google.api_core.client_options import ClientOptions
    from google.cloud.discoveryengine_v1 import EngineServiceClient
    from google.cloud.discoveryengine_v1.types import CreateEngineRequest, Engine, common

    opts = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = EngineServiceClient(client_options=opts)
    parent = client.collection_path(
        project=project, location=location, collection="default_collection"
    )
    eng = Engine(
        display_name=display_name,
        solution_type=common.SolutionType.SOLUTION_TYPE_SEARCH,
        industry_vertical=common.IndustryVertical.GENERIC,
        data_store_ids=[data_store_id],
        search_engine_config=Engine.SearchEngineConfig(),
    )
    req = CreateEngineRequest(parent=parent, engine_id=engine_id, engine=eng)
    print(f"Creating search engine {engine_id!r} bound to data store {data_store_id!r} …")
    try:
        op = client.create_engine(request=req)
        op.result(timeout=900)
        print("CreateEngine: done.")
    except gexc.AlreadyExists:
        print("CreateEngine: already exists — skip.")


def main() -> int:
    args = _parse_args()
    try:
        from google.api_core import exceptions as gexc
        from google.api_core.client_options import ClientOptions
        from google.cloud import discoveryengine
    except ImportError:
        print(
            "Missing dependency. Run:\n"
            '  py -m pip install "google-cloud-discoveryengine>=0.11.0"\n',
            file=sys.stderr,
        )
        return 2

    if args.engine_only:
        _run_create_search_engine(
            args.project,
            args.location,
            args.data_store_id,
            args.engine_id,
            args.search_engine_display_name,
        )
        return 0

    display_name = args.display_name or args.data_store_id
    client_options = (
        ClientOptions(api_endpoint=f"{args.location}-discoveryengine.googleapis.com")
        if args.location != "global"
        else None
    )

    if not args.skip_create:
        ds_client = discoveryengine.DataStoreServiceClient(client_options=client_options)
        parent = ds_client.collection_path(
            project=args.project,
            location=args.location,
            collection="default_collection",
        )
        data_store = discoveryengine.DataStore(
            display_name=display_name,
            industry_vertical=discoveryengine.IndustryVertical.GENERIC,
            solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
            content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
        )
        req = discoveryengine.CreateDataStoreRequest(
            parent=parent,
            data_store_id=args.data_store_id,
            data_store=data_store,
        )
        print(f"Creating data store {args.data_store_id!r} in {args.project}/{args.location} …")
        try:
            op = ds_client.create_data_store(request=req)
            op.result()
            print("CreateDataStore: done.")
        except gexc.AlreadyExists:
            print("CreateDataStore: already exists — continuing.")

    if args.skip_import:
        if args.create_search_engine:
            _run_create_search_engine(
                args.project,
                args.location,
                args.data_store_id,
                args.engine_id or _default_engine_id(args.project),
                args.search_engine_display_name
                or args.display_name
                or f"B2G search ({args.project})",
            )
        return 0

    doc_client = discoveryengine.DocumentServiceClient(client_options=client_options)
    branch = doc_client.branch_path(
        project=args.project,
        location=args.location,
        data_store=args.data_store_id,
        branch="default_branch",
    )
    mode = getattr(
        discoveryengine.ImportDocumentsRequest.ReconciliationMode,
        args.reconciliation_mode,
    )
    import_req = discoveryengine.ImportDocumentsRequest(
        parent=branch,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[args.gcs_uri],
            data_schema="content",
        ),
        reconciliation_mode=mode,
    )
    print(f"ImportDocuments from {args.gcs_uri!r} …")
    op = doc_client.import_documents(request=import_req)
    op.result()
    print("ImportDocuments: operation finished.")

    if args.create_search_engine:
        _run_create_search_engine(
            args.project,
            args.location,
            args.data_store_id,
            args.engine_id or _default_engine_id(args.project),
            args.search_engine_display_name
            or args.display_name
            or f"B2G search ({args.project})",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
