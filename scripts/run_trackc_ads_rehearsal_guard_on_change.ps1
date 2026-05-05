param(
    [string]$WorkDir = "C:/workspace",
    [string]$StateFile = "C:/workspace/reports/trackc_ads_guard_state.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Get-FileFingerprint([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $null
    }
    $item = Get-Item $Path
    return [pscustomobject]@{
        path = $Path
        length = [int64]$item.Length
        last_write_utc = $item.LastWriteTimeUtc.ToString("o")
    }
}

function Load-State([string]$Path) {
    if (-not (Test-Path $Path)) {
        return @{}
    }
    try {
        return (Get-Content -Raw -Encoding UTF8 $Path | ConvertFrom-Json -AsHashtable)
    } catch {
        return @{}
    }
}

function Save-State([string]$Path, $State) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    ($State | ConvertTo-Json -Depth 6) | Set-Content -Path $Path -Encoding UTF8
}

function Fingerprint-Changed($Old, $New) {
    if ($null -eq $Old -and $null -eq $New) { return $false }
    if ($null -eq $Old -or $null -eq $New) { return $true }
    if ($Old.length -ne $New.length) { return $true }
    if ($Old.last_write_utc -ne $New.last_write_utc) { return $true }
    return $false
}

$resolvedWorkDir = (Resolve-Path $WorkDir).Path
$watchTargets = @(
    (Join-Path $resolvedWorkDir "campaign-brief.md"),
    (Join-Path $resolvedWorkDir "generation-manifest.json"),
    (Join-Path $resolvedWorkDir "ad-assets")
)

$current = @{}
foreach ($target in $watchTargets) {
    if ($target.EndsWith("ad-assets")) {
        if (Test-Path $target) {
            $pngs = Get-ChildItem -Path $target -Recurse -File -Filter *.png -ErrorAction SilentlyContinue
            $latest = $pngs | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
            $current[$target] = [pscustomobject]@{
                file_count = @($pngs).Count
                latest_write_utc = if ($latest) { $latest.LastWriteTimeUtc.ToString("o") } else { $null }
            }
        } else {
            $current[$target] = $null
        }
    } else {
        $current[$target] = Get-FileFingerprint -Path $target
    }
}

$state = Load-State -Path $StateFile
$previous = if ($state.ContainsKey("fingerprints")) { $state["fingerprints"] } else { @{} }

$changed = $false
$changeReasons = @()

foreach ($key in $current.Keys) {
    $oldVal = if ($previous.ContainsKey($key)) { $previous[$key] } else { $null }
    $newVal = $current[$key]
    if ($key.EndsWith("ad-assets")) {
        $oldCount = if ($oldVal -and $oldVal.ContainsKey("file_count")) { [int]$oldVal["file_count"] } else { -1 }
        $oldLatest = if ($oldVal -and $oldVal.ContainsKey("latest_write_utc")) { [string]$oldVal["latest_write_utc"] } else { "" }
        $newCount = if ($newVal) { [int]$newVal.file_count } else { -1 }
        $newLatest = if ($newVal) { [string]$newVal.latest_write_utc } else { "" }
        if ($oldCount -ne $newCount -or $oldLatest -ne $newLatest) {
            $changed = $true
            $changeReasons += "changed: ad-assets"
        }
    } else {
        if (Fingerprint-Changed -Old $oldVal -New $newVal) {
            $changed = $true
            $changeReasons += "changed: $key"
        }
    }
}

if ($Force) {
    $changed = $true
    $changeReasons += "forced run"
}

if ($changed) {
    Write-Host "Track C guard: changes detected -> running validation" -ForegroundColor Green
    if ($changeReasons.Count -gt 0) {
        $changeReasons | Select-Object -Unique | ForEach-Object { Write-Host " - $_" }
    }
    powershell -NoProfile -ExecutionPolicy Bypass -File "C:/workspace/scripts/run_trackc_ads_rehearsal_guard.ps1" -WorkDir $resolvedWorkDir
    $exitCode = $LASTEXITCODE
} else {
    Write-Host "Track C guard: no relevant changes, skipping validation." -ForegroundColor Yellow
    $exitCode = 0
}

$newState = @{
    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    work_dir = $resolvedWorkDir
    fingerprints = $current
}
Save-State -Path $StateFile -State $newState

exit $exitCode
