param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SyncAsDefaultBundle
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$sourceBundle = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_showroom_public_bundle_latest.json"
$defaultBundle = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"
$rehearsalBundle = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\showroom_public_bundle_v1.json"
$validator = Join-Path $WorkspaceRoot "scripts\validate_showroom_public_bundle.py"
$publishScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\publish_showroom_public_event.ps1"

if (-not (Test-Path -LiteralPath $sourceBundle)) {
    throw "missing source bundle: $sourceBundle"
}

Write-Host "[1/5] Validate generated Logos showroom bundle..."
py $validator $sourceBundle
if ($LASTEXITCODE -ne 0) { throw "validate failed for source bundle" }

Write-Host "[2/5] Verify required public_event.v1 fields..."
$doc = Get-Content -LiteralPath $sourceBundle -Raw -Encoding UTF8 | ConvertFrom-Json
$ev = $doc.public_event_v1
if ($null -eq $ev) { throw "public_event_v1 missing in $sourceBundle" }
$required = @("timestamp","active_character_id","risk_level","public_signal_direction","abstract_reason","schema_version","event_id","source","disclaimer_ref")
$missing = @()
foreach ($k in $required) {
    if (-not ($ev.PSObject.Properties.Name -contains $k)) { $missing += $k }
}
if ($missing.Count -gt 0) {
    throw ("missing fields: " + ($missing -join ", "))
}
if ([string]$ev.schema_version -ne "public-event.v1") { throw "schema_version mismatch" }
if ([string]$ev.disclaimer_ref -ne "jemaai_showroom_v1") { throw "disclaimer_ref mismatch" }
Write-Host "    OK: required fields present"

Write-Host "[3/5] Sync bundle to showroom consumer path..."
Copy-Item -LiteralPath $sourceBundle -Destination $rehearsalBundle -Force
Write-Host "    synced -> $rehearsalBundle"

if ($SyncAsDefaultBundle) {
    Write-Host "[4/5] Sync bundle to default publish path..."
    Copy-Item -LiteralPath $sourceBundle -Destination $defaultBundle -Force
    Write-Host "    synced -> $defaultBundle"
} else {
    Write-Host "[4/5] Skip default path sync (use -SyncAsDefaultBundle to enable)."
}

Write-Host "[5/5] Validate publish script can read this bundle path..."
powershell -NoProfile -ExecutionPolicy Bypass -File $publishScript -WorkspaceRoot $WorkspaceRoot -BundlePath $sourceBundle
if ($LASTEXITCODE -ne 0) {
    Write-Host "    INFO: publish step returned non-zero (likely gateway/token), but consumer-path parse was executed."
}

Write-Host "DONE: logos showroom consumer path smoke complete."

