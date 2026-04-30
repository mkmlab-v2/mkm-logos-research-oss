param(
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_environment_snapshot_latest.json"
)

$ErrorActionPreference = "Stop"

function Test-DriveLetter([string]$Letter) {
    $root = "{0}:\" -f $Letter.TrimEnd(':')
    return (Test-Path -LiteralPath $root)
}

function Resolve-GVaultProbePath {
    if (-not (Test-DriveLetter "G")) {
        return $null
    }
    $candidates = @()
    # Discover path without relying on localized folder names.
    try {
        $gRootDirs = Get-ChildItem -LiteralPath "G:\" -Directory -ErrorAction Stop
        foreach ($dir in $gRootDirs) {
            $probe = Join-Path (Join-Path $dir.FullName "MKM_DATA_VAULT") "vault"
            if (Test-Path -LiteralPath $probe) {
                return $probe
            }
            $candidates += $probe
        }
    } catch {
        # Ignore discovery errors and rely on static fallback.
    }
    $candidates += "G:\공유 드라이브\MKM_DATA_VAULT\vault"
    foreach ($path in ($candidates | Select-Object -Unique)) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return $path
        }
    }
    return ($candidates | Select-Object -First 1)
}

$tasksToProbe = @(
    "\Bitcoin-Ops-Fusion-Cycle-Auto",
    "\Bitcoin-Verify-All-Green-SelfHeal-30min",
    "\Bitcoin-Fused-QuantPixel-SOP-Live-Daily"
)

$taskSnapshots = @()
foreach ($tn in $tasksToProbe) {
    $exists = $true
    schtasks /Query /TN $tn > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        $exists = $false
    }
    $entry = [ordered]@{
        task_name = $tn
        exists    = $exists
    }
    if ($exists) {
        $raw = schtasks /Query /TN $tn /V /FO LIST 2>$null
        if ($LASTEXITCODE -eq 0 -and $raw) {
            $logonLine = ($raw | Select-String "^Logon Mode:\s+" | Select-Object -First 1)
            $statusLine = ($raw | Select-String "^Status:\s+" | Select-Object -First 1)
            $nextLine = ($raw | Select-String "^Next Run Time:\s+" | Select-Object -First 1)
            if ($logonLine) { $entry["logon_mode"] = ($logonLine.ToString() -replace "^Logon Mode:\s+", "").Trim() }
            if ($statusLine) { $entry["status"] = ($statusLine.ToString() -replace "^Status:\s+", "").Trim() }
            if ($nextLine) { $entry["next_run_time"] = ($nextLine.ToString() -replace "^Next Run Time:\s+", "").Trim() }
        }
    }
    $taskSnapshots += $entry
}

$gPathProbe = Resolve-GVaultProbePath
$gProbeOk = $false
if ($gPathProbe) {
    # Retry a few times to avoid transient mapped-drive readiness races.
    for ($i = 0; $i -lt 3; $i++) {
        if (Test-Path -LiteralPath $gPathProbe) {
            $gProbeOk = $true
            break
        }
        Start-Sleep -Milliseconds 300
    }
}
$payload = [ordered]@{
    schema         = "ops_environment_snapshot_v1"
    ts_utc         = [DateTimeOffset]::UtcNow.ToString("o")
    user_name      = [Environment]::UserName
    user_domain    = [Environment]::UserDomainName
    workspace_ok   = (Test-Path -LiteralPath "C:\workspace")
    g_drive_root   = (Test-DriveLetter "G")
    g_vault_probe  = $gProbeOk
    g_vault_path   = $gPathProbe
    tasks          = $taskSnapshots
    notes          = "Unattended tasks may lose G: if mapped per-user; verify with pilot before broad Run-whether-logged-on."
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Host ("[env-snapshot] WROTE: {0}" -f $OutputPath)
exit 0
