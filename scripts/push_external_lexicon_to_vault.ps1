param(
    [string]$SourceRoot = "C:\workspace\vault\external_lexicon",
    [string]$VaultTargetRoot = ""
)

$ErrorActionPreference = "Stop"

function Resolve-MkmVaultRoot {
    $vaultBase = Get-ChildItem -Path "G:\" -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "vault" -and $_.FullName -match "MKM_DATA_VAULT" } |
        Select-Object -First 1
    if (-not $vaultBase) {
        throw "Could not locate MKM_DATA_VAULT\\vault under G:\\"
    }
    return $vaultBase.FullName
}

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Source root not found: $SourceRoot"
}

if ([string]::IsNullOrWhiteSpace($VaultTargetRoot)) {
    $VaultTargetRoot = Join-Path (Resolve-MkmVaultRoot) "external_lexicon"
}

$manifestPath = Join-Path $SourceRoot "MANIFEST.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Warning "MANIFEST.json missing under $SourceRoot; stage manifest + license before treating lexicon as SSOT."
}

if (-not (Test-Path -LiteralPath $VaultTargetRoot)) {
    New-Item -ItemType Directory -Path $VaultTargetRoot -Force | Out-Null
}

Copy-Item -Path (Join-Path $SourceRoot "*") -Destination $VaultTargetRoot -Recurse -Force

$fileCount = (Get-ChildItem -LiteralPath $VaultTargetRoot -File -Recurse -ErrorAction SilentlyContinue).Count

$summary = [ordered]@{
    executed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source_root     = $SourceRoot
    target_root     = $VaultTargetRoot
    files_under_target_recursive = $fileCount
    manifest_present_at_source   = (Test-Path -LiteralPath $manifestPath)
}

$summaryPath = Join-Path $VaultTargetRoot "_push_summary_lexicon_latest.json"
($summary | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Lexicon push complete. target_file_count(recursive)=$fileCount"
Write-Host "Target: $VaultTargetRoot"
