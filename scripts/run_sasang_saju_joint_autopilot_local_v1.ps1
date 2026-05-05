#Requires -Version 5.1
<#
.SYNOPSIS
  Rebuild strict high-signal catalog filter, joint review queue, and auto Sasang enrichment (no Europe PMC calls).

.NOTES
  Run Europe PMC fetch separately: fetch_europepmc_sasang_saju_literature_catalog_v1.py
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
$py = "py"

& $py scripts/filter_sasang_saju_literature_catalog_v1.py `
  --in data/myeongni/sasang_saju_literature_catalog_strict_v1.jsonl `
  --out data/myeongni/sasang_saju_literature_catalog_strict_high_signal_v1.jsonl `
  --min-tier medium `
  --summary data/myeongni/sasang_saju_literature_filter_from_strict_v1.json

& $py scripts/build_sasang_saju_joint_review_queue_from_catalog_v1.py --max-rows 500

& $py scripts/auto_enrich_sasang_from_literature_stub_v1.py

& $py scripts/resolve_literature_sasang_majority_v1.py --majority-ratio 0.51 --majority-margin 1 --majority-min-hits 1

& $py scripts/export_sasang_literature_supervised_jsonl_v1.py

& $py scripts/ingest_curated_saju_joint_v1.py --input-jsonl data/myeongni/curated_saju_joint_v1.jsonl --target-jsonl data/myeongni/sasang_saju_joint_benchmark_v1.jsonl

& $py scripts/promote_joint_curated_csv_v1.py --csv data/myeongni/auto_joint_machine_curator_seed_v1.csv --target-jsonl data/myeongni/sasang_saju_joint_benchmark_v1.jsonl

& $py scripts/promote_joint_curated_csv_v1.py --dry-run

& $py scripts/validate_sasang_saju_joint_benchmark_jsonl_v1.py

& $py scripts/run_sasang_saju_joint_benchmark_smoke_v1.py

Write-Host "OK sasang_saju_joint_autopilot_local_v1"
