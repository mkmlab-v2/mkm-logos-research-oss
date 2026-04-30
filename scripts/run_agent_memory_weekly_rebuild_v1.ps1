<#
.SYNOPSIS
  Weekly rebuild for agent memory TTL/hot/compact.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$TtlDays = 7,
    [int]$MinReproScore = 1
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\rebuild_agent_memory_weekly_v1.py"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Weekly memory rebuild runner not found: $runner"
}

& py $runner `
    --memory-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_deltas_v1.jsonl") `
    --memory-jsonl-a (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_deltas_track_a_v1.jsonl") `
    --memory-jsonl-b (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_deltas_track_b_v1.jsonl") `
    --combined-mirror-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_deltas_v1.jsonl") `
    --hot-jsonl (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_hot_v1.jsonl") `
    --summary-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_weekly_rebuild_summary_latest.json") `
    --compact-json (Join-Path $WorkspaceRoot "docs\final\artifacts\agent_memory_compact_20_latest.json") `
    --ttl-days $TtlDays `
    --compact-limit 20 `
    --min-repro-score $MinReproScore
if ($LASTEXITCODE -ne 0) { throw "Agent memory weekly rebuild failed ($LASTEXITCODE)" }

Write-Host "DONE: agent memory weekly rebuild"
