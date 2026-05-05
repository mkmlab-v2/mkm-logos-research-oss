[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$storeScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path -LiteralPath $storeScript)) {
    throw "Required script not found: $storeScript"
}

function Get-StoreKeys {
    $output = powershell -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action list
    if ($LASTEXITCODE -ne 0) {
        return @()
    }
    if ($output -is [string]) {
        if ($output -eq "No keys in encrypted store.") { return @() }
        return @($output)
    }
    return @($output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

$requiredKeys = @(
    "PADDLE_EMAIL",
    "PADDLE_VENDOR_ID",
    "PADDLE_PAYONEER_EMAIL",
    "PADDLE_LEGAL_ENTITY_TYPE"
)

$optionalKeys = @(
    "PADDLE_API_KEY"
)

$webRuntimeKeys = @(
    "NEXT_PUBLIC_PADDLE_CLIENT_TOKEN",
    "NEXT_PUBLIC_PADDLE_PRICE_ID",
    "NEXT_PUBLIC_PADDLE_ENV"
)

$keys = Get-StoreKeys

$requiredStatus = @()
foreach ($k in $requiredKeys) {
    $requiredStatus += [ordered]@{
        key = $k
        present = ($keys -contains $k)
    }
}

$optionalStatus = @()
foreach ($k in $optionalKeys) {
    $optionalStatus += [ordered]@{
        key = $k
        present = ($keys -contains $k)
    }
}

$webRuntimeStatus = @()
foreach ($k in $webRuntimeKeys) {
    $webRuntimeStatus += [ordered]@{
        key = $k
        present = ($keys -contains $k)
    }
}

$webRuntimeMissing = @($webRuntimeStatus | Where-Object { -not $_.present } | ForEach-Object { $_.key })
$webRuntimeReady = ($webRuntimeMissing.Count -eq 0)

$requiredMissing = @($requiredStatus | Where-Object { -not $_.present } | ForEach-Object { $_.key })
$requiredReady = ($requiredMissing.Count -eq 0)

$report = [ordered]@{
    schema = "paddle_onboarding_readiness_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    secure_store = [ordered]@{
        script = "scripts/Invoke-EncryptedSecretStore.ps1"
        keys_present_count = @($keys).Count
    }
    required = $requiredStatus
    optional = $optionalStatus
    web_runtime = $webRuntimeStatus
    required_ready = $requiredReady
    web_runtime_ready = $webRuntimeReady
    required_missing_keys = $requiredMissing
    web_runtime_missing_keys = $webRuntimeMissing
    onboarding_blockers = @(
        "Payout settings legal representative fields must be entered by account owner",
        "Website verification failed requires Paddle review/resubmission"
    )
    next_commands = @(
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Initialize-PaddleSecureStore.ps1",
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Use-PaddleSecureSession.ps1"
    )
}

$artifactDir = Join-Path $PSScriptRoot "..\docs\final\artifacts"
$artifactDir = [System.IO.Path]::GetFullPath($artifactDir)
if (-not (Test-Path -LiteralPath $artifactDir)) {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
}

$jsonPath = Join-Path $artifactDir "paddle_onboarding_readiness_latest.json"
$mdPath = Join-Path $artifactDir "paddle_onboarding_readiness_latest.md"

$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$md = @()
$md += "# Paddle Onboarding Readiness"
$md += ""
$md += "- generated_at_utc: ``$($report.generated_at_utc)``"
$md += "- required_ready: ``$($report.required_ready)``"
$md += "- keys_present_count: ``$($report.secure_store.keys_present_count)``"
$md += ""
$md += "## Required Keys"
foreach ($row in $requiredStatus) {
    $md += "- $($row.key): ``$($row.present)``"
}
$md += ""
$md += "## Optional Keys"
foreach ($row in $optionalStatus) {
    $md += "- $($row.key): ``$($row.present)``"
}
$md += ""
$md += "## Web Runtime Keys (Paddle.js)"
foreach ($row in $webRuntimeStatus) {
    $md += "- $($row.key): ``$($row.present)``"
}
$md += ""
$md += "## Missing Web Runtime Keys"
if ($webRuntimeMissing.Count -eq 0) {
    $md += "- none"
}
else {
    foreach ($k in $webRuntimeMissing) {
        $md += "- $k"
    }
}
$md += ""
$md += "## Missing Required Keys"
if ($requiredMissing.Count -eq 0) {
    $md += "- none"
}
else {
    foreach ($k in $requiredMissing) {
        $md += "- $k"
    }
}
$md += ""
$md += "## Onboarding Blockers"
foreach ($b in $report.onboarding_blockers) {
    $md += "- $b"
}
$md += ""
$md += "## Next Commands"
foreach ($c in $report.next_commands) {
    $md += "- ``$c``"
}
$md += ""

$md -join "`r`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Output "Wrote: $jsonPath"
Write-Output "Wrote: $mdPath"
if ($requiredReady) {
    Write-Output "READY: required secure keys are present."
}
else {
    Write-Output "HOLD: missing required secure keys."
}

