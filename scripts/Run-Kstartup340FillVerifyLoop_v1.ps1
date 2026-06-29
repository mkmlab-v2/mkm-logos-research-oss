#Requires -Version 5.1
<#
.SYNOPSIS
  Startup package 340: paste lint, fill, verify, forbidden, body audit, Downloads copy.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-Kstartup340FillVerifyLoop_v1.ps1
#>
param(
    [int]$Version = 0,
    [int]$MaxAttempts = 2,
    [switch]$SkipIngest,
    [switch]$SkipPasteLint,
    [switch]$StrictPasteLint,
    [switch]$AttestG1,
    [switch]$SkipCopyDownloads
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$filledDir = Join-Path $root "reports\kstartup_startup_package_ai_filled"
$loopReport = Join-Path $root "reports\kstartup_startup_package_ai_fill_verify_loop_latest.json"

function Invoke-Step($name, [scriptblock]$block) {
    Write-Host "== $name ==" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$name failed exit=$LASTEXITCODE" }
}

function Get-NextVersion {
    if ($Version -gt 0) { return $Version }
    $max = 0
    if (Test-Path $filledDir) {
        Get-ChildItem -Path $filledDir -Filter "doyak_plan_filled_v*.docx" -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.BaseName -match "_v(\d+)$") {
                $n = [int]$Matches[1]
                if ($n -gt $max) { $max = $n }
            }
        }
    }
    return ($max + 1)
}

function Write-LoopReport($obj) {
    $obj | ConvertTo-Json -Depth 8 | Set-Content -Path $loopReport -Encoding UTF8
}

$ver = Get-NextVersion
$docxRel = "reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v$ver.docx"
$pdfRel = "reports/kstartup_startup_package_ai_filled/doyak_plan_filled_v$ver.pdf"
$docxAbs = Join-Path $root "reports\kstartup_startup_package_ai_filled\doyak_plan_filled_v$ver.docx"
$pdfAbs = Join-Path $root "reports\kstartup_startup_package_ai_filled\doyak_plan_filled_v$ver.pdf"

$steps = @()
$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

try {
    if (-not $SkipIngest) {
        Invoke-Step "ingest_attachments" { py scripts/ingest_kstartup_startup_package_ai_downloads_v1.py }
        $steps += @{ step = "ingest"; ok = $true }
    }

    Invoke-Step "build_paste" { py scripts/build_kstartup_startup_package_ai_paste_ready_v1.py }
    $steps += @{ step = "build_paste"; ok = $true }

    if (-not $SkipPasteLint) {
        Write-Host "== paste_lint ==" -ForegroundColor Cyan
        if ($StrictPasteLint) {
            py scripts/check_kstartup_startup_package_ai_paste_lint_v1.py --strict
        } else {
            py scripts/check_kstartup_startup_package_ai_paste_lint_v1.py
        }
        $lintRc = $LASTEXITCODE
        $steps += @{ step = "paste_lint"; ok = ($lintRc -eq 0); exit_code = $lintRc }
        if ($lintRc -ne 0) {
            throw "paste_lint failed exit=$lintRc"
        }
    }

    $attempt = 0
    $verifyOk = $false
    $lastVerify = $null
    while ($attempt -lt $MaxAttempts -and -not $verifyOk) {
        $attempt++
        Write-Host "== fill_doyak_docx (attempt $attempt / $MaxAttempts, v$ver) ==" -ForegroundColor Cyan
        py scripts/fill_kstartup_startup_package_ai_doyak_docx_v1.py --out-docx $docxRel --out-pdf $pdfRel
        if ($LASTEXITCODE -ne 0) { throw "fill failed exit=$LASTEXITCODE on attempt $attempt" }
        $steps += @{ step = "fill"; attempt = $attempt; version = $ver; ok = $true }

        Write-Host "== verify_filled_plan (attempt $attempt) ==" -ForegroundColor Cyan
        py scripts/verify_kstartup_startup_package_ai_filled_plan_v1.py --docx $docxRel --pdf $pdfRel
        $verifyRc = $LASTEXITCODE
        $verifyPath = Join-Path $root "reports\kstartup_startup_package_ai_filled_plan_verify_latest.json"
        if (Test-Path $verifyPath) {
            $lastVerify = Get-Content $verifyPath -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        $verifyOk = ($verifyRc -eq 0)
        $steps += @{ step = "verify"; attempt = $attempt; ok = $verifyOk; exit_code = $verifyRc }
        if (-not $verifyOk -and $attempt -lt $MaxAttempts) {
            Write-Host "WARN: verify failed - retrying fill" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }

    if (-not $verifyOk) {
        throw "verify failed after $MaxAttempts attempt(s)"
    }

    Invoke-Step "forbidden_scan" { py scripts/check_kstartup_startup_package_ai_forbidden_phrases_v1.py }
    $steps += @{ step = "forbidden"; ok = $true }

    Write-Host "== body_audit ==" -ForegroundColor Cyan
    py scripts/export_kstartup_startup_package_ai_docx_preview_v1.py --docx $docxRel
    $auditRc = $LASTEXITCODE
    $steps += @{ step = "body_audit"; ok = ($auditRc -eq 0); exit_code = $auditRc }
    if ($auditRc -ne 0) {
        throw "body_audit failed exit=$auditRc"
    }

    if ($AttestG1) {
        Invoke-Step "attest_g1" {
            py scripts/verify_kstartup_startup_package_ai_filled_plan_v1.py --docx $docxRel --pdf $pdfRel --attest-g1
        }
        $steps += @{ step = "attest_g1"; ok = $true }
    }

    $copied = @()
    if (-not $SkipCopyDownloads) {
        Invoke-Step "copy_downloads" { py scripts/copy_kstartup340_filled_to_downloads_v1.py --version $ver }
        $copied = @(
            (Join-Path $env:USERPROFILE "Downloads\kstartup340_plan_moksori_v$ver.docx"),
            (Join-Path $env:USERPROFILE "Downloads\kstartup340_plan_moksori_v$ver.pdf")
        )
        Write-Host "Copied to Downloads v$ver" -ForegroundColor Green
    }

    $summary = @{
        schema = "kstartup_startup_package_ai_fill_verify_loop_v1"
        started_at_utc = $started
        finished_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        version = $ver
        ok = $true
        outputs = @{
            docx = $docxRel
            pdf = $pdfRel
            verify = "reports/kstartup_startup_package_ai_filled_plan_verify_latest.json"
            paste_lint = "reports/kstartup_startup_package_ai_paste_lint_latest.json"
            body_audit = "reports/kstartup_startup_package_ai_filled_body_audit_latest.json"
            downloads = $copied
        }
        verify_summary = $lastVerify
        steps = $steps
    }
    Write-LoopReport $summary
    Write-Host ""
    Write-Host "340 fill-verify loop PASS v$ver" -ForegroundColor Green
    Write-Host "  docx: $docxRel" -ForegroundColor DarkGray
    Write-Host "  report: $loopReport" -ForegroundColor DarkGray
    exit 0
}
catch {
    $summary = @{
        schema = "kstartup_startup_package_ai_fill_verify_loop_v1"
        started_at_utc = $started
        finished_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        version = $ver
        ok = $false
        error = $_.Exception.Message
        steps = $steps
    }
    Write-LoopReport $summary
    Write-Host "340 fill-verify loop FAIL: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  report: $loopReport" -ForegroundColor DarkGray
    exit 1
}
