# 10-minute open-bench onboard smoke — visitor reproduce + contributor validate (SSOT wrapper).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$PipInstall,
    [switch]$SkipEvidenceChain,
    [switch]$SkipCompressionValidate,
    [switch]$SkipProphecyValidate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "=== Open-bench onboard smoke (~10 min visitor path) ===" -ForegroundColor Cyan
Write-Host "SEND_GATE HOLD | no mirror push | no customer n50 default path" -ForegroundColor Yellow
Write-Host "SSOT: CONTRIBUTING_OPEN_BENCH.md + run_compression_open_bench_onboard_smoke_v1.py" -ForegroundColor DarkGray

$ArgsList = @("scripts/run_compression_open_bench_onboard_smoke_v1.py")
if ($PipInstall) { $ArgsList += "--pip-install" }
if ($SkipEvidenceChain) { $ArgsList += "--skip-evidence-chain" }
if ($SkipCompressionValidate) { $ArgsList += "--skip-compression-validate" }
if ($SkipProphecyValidate) { $ArgsList += "--skip-prophecy-validate" }
if ($DryRun) { $ArgsList += "--dry-run" }

& py @ArgsList
exit $LASTEXITCODE
