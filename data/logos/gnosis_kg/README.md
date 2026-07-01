# Gnosis KG (user-provided, not shipped in OSS export)

Place local Gnosis exports here for morphology ingest:

- `hebrew-words.json`
- `greek-words.json`

## Ingest (local only)

```powershell
py scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py --gnosis-dir data/logos/gnosis_kg --ack-license-cc-by-sa-4
```

License: CC-BY-SA 4.0 — verify upstream `SOURCES.md`. Responsibility is on the user running ingest.

## Fixture smoke (no download required)

```powershell
py scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py --use-fixture-sample --no-merge
py scripts/run_logos_oss_premarket_smoke_v1.py
```

`research_only` · `send_gate: HOLD` for grants/contracts · Track A trading remains LOCKED.
