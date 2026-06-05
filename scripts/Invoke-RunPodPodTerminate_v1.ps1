#Requires -Version 5.1
<#
.SYNOPSIS
  Terminate a RunPod pod via GraphQL (stop billing). Requires RUNPOD_API_KEY in .env or env.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-RunPodPodTerminate_v1.ps1
  powershell ... -PodId txir98r3pwaqbr -DryRun
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PodId = "",
    [string]$ApiKey = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RunPodApiKey {
    param([string]$Override)
    if ($Override) { return $Override.Trim() }
    $fromEnv = [Environment]::GetEnvironmentVariable("RUNPOD_API_KEY")
    if ($fromEnv) { return $fromEnv.Trim() }
    $envPath = Join-Path $RepoRoot ".env"
    if (Test-Path -LiteralPath $envPath) {
        $line = Select-String -Path $envPath -Pattern '^\s*RUNPOD_API_KEY=(.+)$' | Select-Object -First 1
        if ($line) {
            $v = $line.Matches[0].Groups[1].Value.Trim().Trim('"').Trim("'")
            if ($v) { return $v }
        }
    }
    return ""
}

function Get-PodIdFromHandoff {
    param([string]$Root)
    $candidates = @(
        (Join-Path $Root "reports\runpod_nemotron_full_handoff_v1_latest.json"),
        (Join-Path $Root "reports\runpod_nemotron_smoke_handoff_v1_latest.json")
    )
    foreach ($p in $candidates) {
        if (-not (Test-Path -LiteralPath $p)) { continue }
        $j = Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
        if ($j.pod.id) { return [string]$j.pod.id }
    }
    return ""
}

$key = Get-RunPodApiKey -Override $ApiKey
if (-not $PodId) { $PodId = Get-PodIdFromHandoff -Root $RepoRoot }
if (-not $PodId) { throw "PodId missing (pass -PodId or set handoff pod.id)" }
if (-not $key) {
    Write-Host "[FAIL] RUNPOD_API_KEY not set (.env or User env). Console: https://www.runpod.io/console/pods -> Terminate pod $PodId" -ForegroundColor Red
    exit 2
}

$body = @{
    query     = "mutation (`$input: PodTerminateInput!) { podTerminate(input: `$input) }"
    variables = @{ input = @{ podId = $PodId } }
} | ConvertTo-Json -Depth 5 -Compress

$uri = "https://api.runpod.io/graphql?api_key=$key"
Write-Host "RunPod podTerminate podId=$PodId dryRun=$DryRun"
if ($DryRun) { exit 0 }

$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body $body
$errProp = $response.PSObject.Properties['errors']
if ($null -ne $errProp -and $errProp.Value) {
    $msg = @($errProp.Value | ForEach-Object { $_.message }) -join "; "
    if ($msg -match 'not found to terminate') {
        Write-Host "[OK] pod already terminated ($PodId)" -ForegroundColor Green
        exit 0
    }
    throw "RunPod API error: $msg"
}
Write-Host "[OK] podTerminate requested for $PodId" -ForegroundColor Green
exit 0
