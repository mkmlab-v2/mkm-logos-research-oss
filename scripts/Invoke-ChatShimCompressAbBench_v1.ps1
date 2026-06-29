# Chat shim A/B bench — raw vs compress (B-track; offline, no upstream billing)
param(
    [string]$InputJsonl = "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl",
    [int]$MaxCases = 0,
    [int]$MinRawTokens = 12,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:COMPRESSION_HARDENING_CONFIG_PATH = "data/btrack/compression_coding_proxy_hardening_v1.json"

$args = @(
    "scripts/sandbox/run_chat_shim_compress_ab_bench_v1.py",
    "--input", $InputJsonl,
    "--min-raw-tokens", $MinRawTokens
)
if ($MaxCases -gt 0) { $args += @("--max-cases", $MaxCases) }
if ($DryRun) { $args += "--dry-run" }

py @args
exit $LASTEXITCODE
