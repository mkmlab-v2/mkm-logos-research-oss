# GCP Free Trial (010B19-239742-DAF438) Vertex burn + JSONL assetization.
# Requires ADC as jema12@mkmlife.com (not giryun288) for gen-lang-client IAM.
param(
    [string]$Project = 'gen-lang-client-0846393371',
    [string]$Model = 'gemini-2.5-pro',
    [int]$Calls = 150,
    [int]$SleepMs = 150,
    [int]$MaxOutputTokens = 8192,
    [string]$PromptProfile = 'asset_rag',
    [string]$WaveId = 'wave2',
    [string]$OutJsonl = 'reports/gcp_free_trial_vertex_burn_assets_v1.jsonl',
    [switch]$DryRun,
    [switch]$NoJsonl
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$argsList = @(
    'scripts/run_gcp_free_trial_vertex_credit_burn_v1.py',
    '--project', $Project,
    '--model', $Model,
    '--calls', "$Calls",
    '--sleep-ms', "$SleepMs",
    '--max-output-tokens', "$MaxOutputTokens",
    '--prompt-profile', $PromptProfile,
    '--wave-id', $WaveId,
    '--out-jsonl', $OutJsonl
)
if ($DryRun) { $argsList += '--dry-run' }
if ($NoJsonl) { $argsList += '--no-jsonl' }

Write-Host "Free Trial Vertex burn: project=$Project wave=$WaveId profile=$PromptProfile calls=$Calls"
& py @argsList
exit $LASTEXITCODE
