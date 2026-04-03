#Requires -Version 5.1
<#
.SYNOPSIS
  E:/F: volume health, top-level sizes (FSO), duplicate-folder warnings (no deletes).

.EXAMPLE
  .\scripts\Invoke-ExternalDrivesGovernance.ps1
  .\scripts\Invoke-ExternalDrivesGovernance.ps1 -ConfigPath .\scripts\external_drives_governance_v1.json
#>
param(
    [string]$ConfigPath = "",
    [string]$OutputJson = "",
    [string]$WorkspaceRoot = "",

    # Default: fast (names + volume only). FSO per-folder sizes can take many minutes on TB trees.
    [switch]$FullFolderSizes
)

$ErrorActionPreference = 'Stop'
$repoRoot = if ($WorkspaceRoot) { $WorkspaceRoot } else { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'external_drives_governance_v1.json' }
if (-not $OutputJson) { $OutputJson = Join-Path $repoRoot 'reports\drive_governance_latest.json' }

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Error "Missing config: $ConfigPath"
    exit 2
}
$cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json

function Get-TopLevelFoldersQuick([string]$driveRoot) {
    if (-not (Test-Path -LiteralPath $driveRoot)) { return @() }
    $rows = @()
    Get-ChildItem -LiteralPath $driveRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $rows += [ordered]@{
            name = $_.Name
            path = $_.FullName
            gb   = $null
        }
    }
    return $rows
}

function Get-TopLevelFolderSizes([string]$driveRoot) {
    if (-not (Test-Path -LiteralPath $driveRoot)) { return @() }
    $fso = New-Object -ComObject Scripting.FileSystemObject
    try {
        $rootFolder = $fso.GetFolder($driveRoot)
    } catch {
        return @()
    }
    $rows = @()
    foreach ($sf in $rootFolder.SubFolders) {
        try {
            $rows += [ordered]@{
                name  = $sf.Name
                path  = $sf.Path
                bytes = [int64]$sf.Size
                gb    = [math]::Round([double]$sf.Size / 1GB, 2)
            }
        } catch { }
    }
    return $rows
}

function Test-NameMatch([string]$name, [object[]]$patterns) {
    foreach ($p in $patterns) {
        if ($name -eq $p) { return $true }
        if ($p.EndsWith('*') -and $name.StartsWith($p.TrimEnd('*'))) { return $true }
    }
    return $false
}

$letters = @('E', 'F')
$utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$warnings = [System.Collections.Generic.List[string]]::new()
$suggestions = [System.Collections.Generic.List[string]]::new()

$volRows = @()
$topMap = @{}

foreach ($L in $letters) {
    $root = "${L}:\"
    $vol = Get-Volume -DriveLetter $L -ErrorAction SilentlyContinue
    if (-not $vol) {
        $warnings.Add("Drive ${L}: not present or not accessible.")
        continue
    }
    $freeGb = [math]::Round($vol.SizeRemaining / 1GB, 2)
    $sizeGb = [math]::Round($vol.Size / 1GB, 2)
    $usedPct = if ($vol.Size -gt 0) { [math]::Round(100 * (1 - $vol.SizeRemaining / $vol.Size), 1) } else { 0 }
    $volRows += [ordered]@{
        letter           = $L
        label            = $vol.FileSystemLabel
        size_gb          = $sizeGb
        free_gb          = $freeGb
        used_percent     = $usedPct
        filesystem       = $vol.FileSystem
    }

    $key = "${L}:"
    if ($FullFolderSizes) {
        $topMap[$key] = Get-TopLevelFolderSizes $root
    } else {
        $topMap[$key] = Get-TopLevelFoldersQuick $root
    }

    $roleKey = $L
    if ($cfg.drives.$roleKey) {
        $minW = $cfg.drives.$roleKey.min_free_gb_warn
        $minC = $cfg.drives.$roleKey.min_free_gb_critical
        if ($null -ne $minC -and $freeGb -lt [double]$minC) {
            $warnings.Add("${L}: CRITICAL free space ${freeGb} GB (below critical $minC GB).")
        } elseif ($null -ne $minW -and $freeGb -lt [double]$minW) {
            $warnings.Add("${L}: WARN free space ${freeGb} GB (below warn $minW GB).")
        }
    }

    if ($L -eq 'F' -and $cfg.f_drive_redundant_patterns -and $FullFolderSizes) {
        foreach ($row in $topMap[$key]) {
            foreach ($pat in $cfg.f_drive_redundant_patterns) {
                if (Test-NameMatch $row.name @($pat)) {
                    if ($null -ne $row.gb -and $row.gb -gt 5) {
                        $warnings.Add("F: heavy/redundant pattern: $($row.name) (~$($row.gb) GB) - consider one archive or E: + backup policy.")
                    }
                }
            }
        }
    } elseif ($L -eq 'F' -and $cfg.f_drive_redundant_patterns -and -not $FullFolderSizes) {
        foreach ($row in $topMap[$key]) {
            foreach ($pat in $cfg.f_drive_redundant_patterns) {
                if (Test-NameMatch $row.name @($pat)) {
                    $warnings.Add("F: redundant pattern present: $($row.name) - verify size with -FullFolderSizes; avoid duplicate full workspace copies.")
                }
            }
        }
    }
}

# Duplicate names across E and F
$dupNames = $cfg.duplicate_watch.folder_names
$dupGb = [double]$cfg.duplicate_watch.warn_if_both_exist_gb
if ($dupNames -and $topMap['E:'] -and $topMap['F:'] -and $FullFolderSizes) {
    $eNames = @{}
    foreach ($r in $topMap['E:']) { $eNames[$r.name] = $r }
    foreach ($fr in $topMap['F:']) {
        if ($dupNames -contains $fr.name -and $eNames.ContainsKey($fr.name)) {
            $eg = $eNames[$fr.name].gb
            $fg = $fr.gb
            if ($null -ne $eg -and $null -ne $fg -and $eg -ge $dupGb -and $fg -ge $dupGb) {
                $warnings.Add("Duplicate large tree name on E: and F: '$($fr.name)' (~${eg} GB + ~${fg} GB). Canonical repo: $($cfg.canonical_workspace).")
            }
        }
    }
} elseif ($dupNames -and $topMap['E:'] -and $topMap['F:'] -and -not $FullFolderSizes) {
    $eSet = @{}
    foreach ($r in $topMap['E:']) { $eSet[$r.name] = $true }
    foreach ($fr in $topMap['F:']) {
        if ($dupNames -contains $fr.name -and $eSet.ContainsKey($fr.name)) {
            $warnings.Add("Same folder name on E: and F: '$($fr.name)' - possible duplicate; run -FullFolderSizes to quantify.")
        }
    }
}

if ($cfg.canonical_workspace) {
    $suggestions.Add("Repo SSOT: $($cfg.canonical_workspace). Use backup_workspace_mirror.ps1 to a single dated path on F:; avoid multiple full workspace copies.")
}
if ($cfg.backup_destination_hint) {
    $suggestions.Add($cfg.backup_destination_hint)
}

$payload = [ordered]@{
    generated_at_utc     = $utc
    config_path        = $ConfigPath
    canonical_workspace = $cfg.canonical_workspace
    volumes            = $volRows
    top_level_folders_gb = $topMap
    warnings           = $warnings
    suggestions        = $suggestions
}

$dir = Split-Path -Parent $OutputJson
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$jsonText = $payload | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $OutputJson -Value $jsonText -Encoding utf8

Write-Host "=== External drives governance ===" -ForegroundColor Cyan
if (-not $FullFolderSizes) { Write-Host "Mode: Quick (add -FullFolderSizes for per-folder GB; slow on large disks)" -ForegroundColor DarkGray }
Write-Host "Report: $OutputJson"
foreach ($v in $volRows) {
    Write-Host ("{0}: {1} | free {2} GB / {3} GB ({4}% used)" -f $v.letter, $v.label, $v.free_gb, $v.size_gb, $v.used_percent)
}
foreach ($w in $warnings) {
    Write-Host "WARN: $w" -ForegroundColor Yellow
}
foreach ($s in $suggestions) {
    Write-Host "TIP: $s" -ForegroundColor DarkGray
}
Write-Host "Done." -ForegroundColor Green
