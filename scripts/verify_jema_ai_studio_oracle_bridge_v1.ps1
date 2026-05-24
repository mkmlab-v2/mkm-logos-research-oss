#Requires -Version 5.1
<#
.SYNOPSIS
  Verify jema-ai.com /studio redirects to Oracle v5 (O-P5 bridge after CF rule).
#>
$ErrorActionPreference = "Stop"
$target = "public_showroom_logos_oracle_v5.html"
$urls = @("https://jema-ai.com/studio", "https://jema-ai.com/studio/")

function Get-Chain($Url) {
    $chain = @()
    $u = $Url
    for ($i = 0; $i -lt 8; $i++) {
        $hdr = & curl.exe -sSI --max-time 25 $u 2>$null
        if ($LASTEXITCODE -ne 0) { return $chain }
        $code = (($hdr | Select-String '^HTTP/' | Select-Object -Last 1) -replace 'HTTP/\S+\s+','').Trim()
        $loc = ($hdr | Select-String -Pattern '^location:' -CaseSensitive:$false | Select-Object -Last 1)
        $locVal = if ($loc) { ($loc -replace '(?i)^location:\s*','').Trim() } else { $null }
        $chain += @{ url = $u; status = $code; location = $locVal }
        if ($code -match '^(301|302|303|307|308)$' -and $locVal) {
            if ($locVal -match '^https?://') { $u = $locVal } else {
                $uri = [Uri]$u
                $u = ($uri.GetLeftPart([UriPartial]::Authority).TrimEnd('/') + '/' + $locVal.TrimStart('/'))
            }
            continue
        }
        break
    }
    return $chain
}

$ok = $false
foreach ($url in $urls) {
    $chain = Get-Chain $url
    $hit = ($chain | ForEach-Object { $_.location } | Where-Object { $_ -and $_ -like "*$target*" }) -ne $null
    if ($hit) { $ok = $true }
    Write-Host "== $url hit_v5=$hit ==" -ForegroundColor Cyan
    foreach ($s in $chain) { Write-Host "  $($s.status) $($s.url) -> $($s.location)" }
}

if (-not $ok) { Write-Host "EXIT 1" -ForegroundColor Red; exit 1 }
Write-Host "EXIT 0" -ForegroundColor Green
exit 0
