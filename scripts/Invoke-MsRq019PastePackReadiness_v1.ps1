#Requires -Version 5.1
<#
.SYNOPSIS
  MS RQ-019 paste pack + Oracle appendix readiness (parallel gate).
  Writes reports/ms_rq019_paste_pack_readiness_latest.json
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pasteDir = Join-Path $root "reports\ms_rq019_paste_ready"
$required = @(
    "k1_problem_paste.txt",
    "k2_method_paste.txt",
    "k3_differentiation_paste.txt",
    "disclaimer_footer_paste.txt",
    "k3_visual_reasoning_path_appendix_paste.txt"
)
$optional = @("k2_two_track_architecture_paste.txt", "finops_l1_official_status_paste.txt")
$gifV6 = Join-Path $pasteDir "ms_rq019_oracle_v6_visual_path_10s.gif"
$gifV5 = Join-Path $pasteDir "ms_rq019_oracle_v5_visual_path_10s.gif"
$gif = if (Test-Path -LiteralPath $gifV6) { $gifV6 } else { $gifV5 }
$errors = @()
$files = @()

foreach ($name in ($required + $optional)) {
    $p = Join-Path $pasteDir $name
    $ok = Test-Path -LiteralPath $p
    $len = if ($ok) { (Get-Content -LiteralPath $p -Raw).Length } else { 0 }
    $files += @{ name = $name; path = $p; exists = $ok; chars = $len; required = ($required -contains $name) }
    if (-not $ok -and ($required -contains $name)) { $errors += "missing:$name" }
    if ($ok -and $len -lt 40 -and ($required -contains $name)) { $errors += "too_short:$name" }
}

$gifOk = Test-Path -LiteralPath $gif
$gifBytes = if ($gifOk) { (Get-Item -LiteralPath $gif).Length } else { 0 }

$wireCode = & curl.exe -sSI -o NUL -w "%{http_code}" --max-time 25 "https://jemaai.cloud/public_showroom_mkm_inter_agent_wire_v3.html" 2>$null
$v6Code = & curl.exe -sSI -o NUL -w "%{http_code}" --max-time 25 "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1" 2>$null
$v5Code = & curl.exe -sSI -o NUL -w "%{http_code}" --max-time 25 "https://jemaai.cloud/public_showroom_logos_oracle_v5.html" 2>$null

$doc = @{
    schema = "ms_rq019_paste_pack_readiness_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    paste_dir = $pasteDir
    files = $files
    gif = @{ path = $gif; exists = $gifOk; bytes = $gifBytes; v6_path = $gifV6; v5_path = $gifV5 }
    urls = @{
        wire_v3 = @{ url = "https://jemaai.cloud/public_showroom_mkm_inter_agent_wire_v3.html"; http = $wireCode }
        oracle_v6_product = @{ url = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"; http = $v6Code }
        oracle_v5 = @{ url = "https://jemaai.cloud/public_showroom_logos_oracle_v5.html"; http = $v5Code }
    }
    ok = ($errors.Count -eq 0) -and $gifOk -and ($wireCode -eq "200") -and ($v6Code -eq "200")
    errors = $errors
    commander_next = @("Paste MS 1-7 from paste_ready", "Attach GIF to K3 appendix", "O-P5: op5_jema12_nginx_one_liner.txt or CF studio redirect script")
}

$out = Join-Path $root "reports\ms_rq019_paste_pack_readiness_latest.json"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding UTF8

Write-Host "== MS paste pack readiness ==" -ForegroundColor Cyan
Write-Host "ok=$($doc.ok) gif=$gifOk wire=$wireCode v6=$v6Code v5=$v5Code"
if (-not $doc.ok) { foreach ($e in $errors) { Write-Host "  $e" -ForegroundColor Red } }
Write-Host "Wrote $out"
exit $(if ($doc.ok) { 0 } else { 1 })
