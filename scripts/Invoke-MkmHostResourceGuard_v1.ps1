#Requires -Version 5.1
<#
.SYNOPSIS
  Host resource guard — memory pressure, C: backup sprawl, Ollama idle unload.

.DESCRIPTION
  Writes reports/mkm_host_resource_guard_v1_latest.json.
  With -Apply: unloads Ollama models when RAM/committed exceed thresholds.
  Does not delete backups on C: (warn only).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmHostResourceGuard_v1.ps1 -Apply
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Apply,
    [double]$WarnCommittedPct = 80,
    [double]$WarnRamUsedPct = 80,
    [double]$WarnCBackupGB = 5,
    [double]$WarnFDriveFreeGB = 40,
    [switch]$SkipOllamaUnload
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$actions = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()
$degraded = $false

function Add-Warn($msg) {
    $script:warnings.Add($msg) | Out-Null
    $script:degraded = $true
}

$os = Get-CimInstance Win32_OperatingSystem
$ramUsedPct = [math]::Round(
    100 * ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize,
    1
)
$freeRamGb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$committedPct = $null
try {
    $committedPct = [math]::Round(
        (Get-Counter '\Memory\% Committed Bytes In Use' -ErrorAction Stop).CounterSamples.CookedValue,
        1
    )
} catch {
    $committedPct = $null
}

$pressure = ($ramUsedPct -ge $WarnRamUsedPct) -or (
    $null -ne $committedPct -and $committedPct -ge $WarnCommittedPct
)

# C: MKM_BACKUP sprawl (should live on F:\BACKUP)
$cBackupRoot = Join-Path $WorkspaceRoot "storage\MKM_BACKUP"
$cBackupGb = 0.0
if (Test-Path -LiteralPath $cBackupRoot) {
    $sum = (Get-ChildItem -LiteralPath $cBackupRoot -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    if ($null -ne $sum) { $cBackupGb = [math]::Round($sum / 1GB, 2) }
}
if ($cBackupGb -ge $WarnCBackupGB) {
    Add-Warn ("c_mkm_backup {0}GB >= warn {1}GB — move to F:\BACKUP" -f $cBackupGb, $WarnCBackupGB)
}

$fFreeGb = $null
$psF = Get-PSDrive -Name F -ErrorAction SilentlyContinue
if ($psF) {
    $fFreeGb = [math]::Round($psF.Free / 1GB, 1)
    if ($fFreeGb -lt $WarnFDriveFreeGB) {
        Add-Warn ("f_drive_free {0}GB < warn {1}GB" -f $fFreeGb, $WarnFDriveFreeGB)
    }
}

# Hygiene SSOT (cursor vscdb + memory thresholds at 85%)
$hygieneScript = Join-Path $WorkspaceRoot "scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
$hygieneExit = 0
if (Test-Path -LiteralPath $hygieneScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $hygieneScript -WorkspaceRoot $WorkspaceRoot
    $hygieneExit = $LASTEXITCODE
    if ($null -eq $hygieneExit) { $hygieneExit = 0 }
    if ($hygieneExit -ne 0) { $degraded = $true }
}

# Ollama idle unload under pressure
$ollamaModels = @()
$ollamaUnload = @()
if (-not $SkipOllamaUnload) {
    $ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaExe) {
        $psOut = & ollama ps 2>&1
        $psExit = $LASTEXITCODE
        if ($null -eq $psExit) { $psExit = 0 }
        if ($psExit -eq 0 -and $psOut) {
            $lines = @($psOut | Where-Object { $_ -is [string] })
            foreach ($line in $lines) {
                if ($line -match '^(NAME|\s*$|-)') { continue }
                $name = ($line -split '\s+', 2)[0]
                if ($name -and $name -ne 'NAME') { $ollamaModels += $name }
            }
        }
        if ($Apply -and $pressure -and $ollamaModels.Count -gt 0) {
            foreach ($model in $ollamaModels) {
                Write-Host "[ollama_unload] $model (pressure ram=$ramUsedPct% committed=$committedPct%)" -ForegroundColor Yellow
                & ollama stop $model 2>&1 | Out-Null
                $ollamaUnload += $model
                $actions.Add("ollama_stop:$model") | Out-Null
            }
        } elseif ($ollamaModels.Count -gt 0 -and $pressure) {
            Add-Warn ("ollama_loaded={0} under memory pressure — run with -Apply or ollama stop" -f ($ollamaModels -join ','))
        }
    }
}

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$payload = [ordered]@{
    schema           = "mkm_host_resource_guard_v1"
    generated_at_utc = $utc
    apply            = [bool]$Apply
    memory           = [ordered]@{
        ram_used_pct    = $ramUsedPct
        free_ram_gb     = $freeRamGb
        committed_pct   = $committedPct
        pressure        = [bool]$pressure
    }
    storage          = [ordered]@{
        c_mkm_backup_gb = $cBackupGb
        f_free_gb       = $fFreeGb
    }
    ollama           = [ordered]@{
        loaded_models = @($ollamaModels)
        unloaded      = @($ollamaUnload)
    }
    hygiene_exit     = $hygieneExit
    warnings         = @($warnings)
    actions          = @($actions)
    degraded         = [bool]$degraded
    verify_command   = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmHostResourceGuard_v1.ps1"
    apply_command    = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmHostResourceGuard_v1.ps1 -Apply"
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$outPath = Join-Path $reportDir "mkm_host_resource_guard_v1_latest.json"
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath"
Write-Host ("HOST_RESOURCE_GUARD degraded={0} warnings={1} actions={2}" -f $degraded, $warnings.Count, $actions.Count)

if ($degraded) { exit 1 }
exit 0
