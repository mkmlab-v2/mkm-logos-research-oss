<#
.SYNOPSIS
  C:/workspace + drive free-space summary (no deletes).

.OUTPUTS
  reports/system_disk_hygiene_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutputJson = "",
    [switch]$WithWorkspaceFileSumFallback
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
if (-not $OutputJson) {
    $OutputJson = Join-Path $root "reports\system_disk_hygiene_latest.json"
}

function Get-DriveRow($letter) {
    $d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$letter'" -ErrorAction SilentlyContinue
    if (-not $d) { return $null }
    [ordered]@{
        drive    = $letter
        free_gb  = [math]::Round($d.FreeSpace / 1GB, 2)
        total_gb = [math]::Round($d.Size / 1GB, 2)
        pct_free = [math]::Round(100 * $d.FreeSpace / $d.Size, 1)
    }
}

function Get-TopDirGb($path, $limit = 12) {
    if (-not (Test-Path -LiteralPath $path)) { return @() }
    Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.PSIsContainer } |
        ForEach-Object {
            $files = Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue
            $sum = 0
            if ($files) {
                $m = $files | Measure-Object -Property Length -Sum
                if ($m.Sum) { $sum = [int64]$m.Sum }
            }
            [PSCustomObject]@{ name = $_.Name; gb = [math]::Round($sum / 1GB, 2) }
        } |
        Sort-Object gb -Descending |
        Select-Object -First $limit
}

$junctions = @(
    @{ path = Join-Path $root ".cache\huggingface"; label = "hf_cache" },
    @{ path = "$env:USERPROFILE\.ollama"; label = "ollama" },
    @{ path = Join-Path $root "storage\hf_cache\nemotron_wsl"; label = "nemotron_hf" },
    @{ path = Join-Path $root "data\nvidia"; label = "nvidia_data" }
)
$junctionRows = foreach ($j in $junctions) {
    if (-not (Test-Path -LiteralPath $j.path)) {
        [ordered]@{ label = $j.label; path = $j.path; ok = $false; link_type = $null; target = $null }
        continue
    }
    $item = Get-Item -LiteralPath $j.path -Force
    [ordered]@{
        label     = $j.label
        path      = $j.path
        ok        = $true
        link_type = $item.LinkType
        target    = if ($item.LinkType) { $item.Target -join ';' } else { $null }
    }
}

$report = [ordered]@{
    schema             = "system_disk_hygiene_v1"
    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    drives             = @(
        (Get-DriveRow 'C:'),
        (Get-DriveRow 'E:'),
        (Get-DriveRow 'F:'),
        (Get-DriveRow 'G:')
    ) | Where-Object { $_ }
    workspace_top_gb   = @(Get-TopDirGb $root)
    junctions          = $junctionRows
    hiberfil_exists    = Test-Path -LiteralPath "C:\hiberfil.sys"
    research_only      = $true
}

$dir = Split-Path -Parent $OutputJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputJson -Encoding UTF8
Write-Host "OK: $OutputJson"
exit 0
