param()

$ErrorActionPreference = "Stop"

powershell -NoProfile -ExecutionPolicy Bypass -File "c:\workspace\scripts\run_smartfarm_daily_ingest_and_gate_v1.ps1" `
  -LiveFetch `
  -MappingCsv "c:\workspace\data\smartfarm_rda_extract_v1\out\station_zone_mapping_operational_v1.csv" `
  -Profile "aggressive" `
  -RecentHoursFromLatest 120

exit $LASTEXITCODE
