#Requires -Version 5.1
param(
    [string]$DownloadsDir = "$env:USERPROFILE\Downloads",
    [string]$OutDir = "reports/kstartup_startup_package_ai_attachments"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dest = Join-Path $root $OutDir
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$portalUrl = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?pbancClssCd=PBC010&schM=view&pbancSn=177670"

$files = Get-ChildItem -LiteralPath $DownloadsDir -File | Where-Object {
    $n = $_.Name
    ($n -like "*창업패키지*AI*") -or ($n -like "*창업도약*") -or ($n -like "*초기창업패키지*AI*")
}

$copied = @()
foreach ($f in $files) {
    $target = Join-Path $dest $f.Name
    Copy-Item -LiteralPath $f.FullName -Destination $target -Force
    $track = "common"
    if ($f.Name -match "도약") { $track = "doyak" }
    elseif ($f.Name -match "초기") { $track = "chogi" }
    $copied += [ordered]@{
        name  = $f.Name
        rel   = ($OutDir.Replace("\", "/") + "/" + $f.Name)
        bytes = $f.Length
        track = $track
    }
}

$doyakPlan = $copied | Where-Object { $_.track -eq "doyak" -and $_.name -match "별첨\s*1" -and $_.name -match "\.docx$" } | Select-Object -First 1
$notice = $copied | Where-Object { $_.name -match "공고문" } | Select-Object -First 1

$manifest = [ordered]@{
    schema             = "kstartup_startup_package_ai_attachments_manifest_v1"
    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    portal_detail_url  = $portalUrl
    pbanc_sn           = "177670"
    track_recommended  = "doyak"
    files              = @($copied)
    paths              = [ordered]@{
        doyak_plan_docx = if ($doyakPlan) { $doyakPlan.rel } else { $null }
        notice_pdf      = if ($notice) { $notice.rel } else { $null }
    }
}

$manifestPath = Join-Path $dest "manifest_latest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "Copied $($copied.Count) files -> $dest"
Write-Host "Manifest: $manifestPath"
