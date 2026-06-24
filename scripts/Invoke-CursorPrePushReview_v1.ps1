#Requires -Version 5.1
<#
.SYNOPSIS
  Pre-push /review gate (Cursor 3.7+) — local ack + git sanity before push-internal.

.DESCRIPTION
  /review runs inside Cursor chat (Bugbot + security). This script records commander ack
  after review and runs Verify-GitWorkspaceSanity.ps1.

.PARAMETER Ack
  Record that /review (or /review-bugbot) was completed in Cursor for current HEAD.

.PARAMETER AutoLocal
  Run local Fact-Lock gates (git sanity + P0 paths) and auto-record ack when all exit 0.
  Substitute when /review chat is unavailable; ack_mode=auto_local (not Bugbot).

.EXAMPLE
  powershell -File scripts\Invoke-CursorPrePushReview_v1.ps1 -AutoLocal
#>
param(
    [switch]$Ack,
    [switch]$AutoLocal,
    [switch]$CheckOnly,
    [int]$RequireAckHours = 24,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $OutJson) {
    $OutJson = Join-Path $WorkspaceRoot "reports\cursor_pre_push_review_v1_latest.json"
}

$head = (git rev-parse HEAD 2>$null).Trim()
if (-not $head) { throw "Not a git repo or no commits." }

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
$nowUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Write-ReviewPrompt {
    Write-Host ""
    Write-Host "=== Cursor pre-push /review (3.7+) ===" -ForegroundColor Cyan
    Write-Host "1. In this chat (or a review chat), run:  /review" -ForegroundColor White
    Write-Host "   Or:  /review-bugbot   and/or   /review-security" -ForegroundColor DarkGray
    Write-Host "2. After review completes, record ack:" -ForegroundColor White
    Write-Host "   powershell -File scripts\Invoke-CursorPrePushReview_v1.ps1 -Ack" -ForegroundColor Green
    Write-Host "3. Then push:" -ForegroundColor White
    Write-Host "   powershell -File scripts\push-internal.ps1" -ForegroundColor Green
    Write-Host ""
    Write-Host "HEAD: $head  branch: $branch" -ForegroundColor DarkGray
}

# Git sanity (Fact-Lock adjacent)
$sanity = Join-Path $WorkspaceRoot "scripts\Verify-GitWorkspaceSanity.ps1"
$sanityExit = 0
if (Test-Path -LiteralPath $sanity) {
    & $sanity
    $sanityExit = $LASTEXITCODE
    if ($sanityExit -ne 0 -and -not $CheckOnly) {
        throw "Verify-GitWorkspaceSanity.ps1 exit $sanityExit"
    }
}

$payload = @{
    schema           = "cursor_pre_push_review_v1"
    generated_at_utc = $nowUtc
    head_sha         = $head
    branch           = $branch
    git_sanity_exit  = $sanityExit
    review_ack       = $false
    ack_at_utc       = $null
    ack_head_sha     = $null
    ack_mode         = $null
    local_gates      = @()
    cursor_commands  = @("/review", "/review-bugbot", "/review-security")
    note             = "Bugbot in chat; auto_local = P0+git sanity substitute only"
}

if ($AutoLocal) {
    $gates = [System.Collections.Generic.List[object]]::new()
    $gates.Add([ordered]@{ name = "git_sanity"; exit = $sanityExit })
    if ($sanityExit -ne 0) {
        $payload.local_gates = @($gates)
        $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
        throw "AutoLocal blocked: git sanity exit $sanityExit"
    }
    $p0 = Join-Path $WorkspaceRoot "scripts\verify_p0_constitution_gate_paths.ps1"
    if (Test-Path -LiteralPath $p0) {
        Write-Host "==> verify_p0_constitution_gate_paths (AutoLocal)" -ForegroundColor Cyan
        & $p0 -WorkspaceRoot $WorkspaceRoot
        $p0Exit = $LASTEXITCODE
        $gates.Add([ordered]@{ name = "p0_constitution_gate_paths"; exit = $p0Exit })
        if ($p0Exit -ne 0) {
            $payload.local_gates = @($gates)
            $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
            throw "AutoLocal blocked: P0 gate exit $p0Exit"
        }
    }
    $payload.local_gates = @($gates)
    $payload.review_ack = $true
    $payload.ack_at_utc = $nowUtc
    $payload.ack_head_sha = $head
    $payload.ack_mode = "auto_local"
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
    Write-Host "[OK] AutoLocal pre-push review ack for HEAD $head (P0 + git sanity)." -ForegroundColor Green
    Write-Host "Wrote: $OutJson" -ForegroundColor DarkGray
    exit 0
}

if (Test-Path -LiteralPath $OutJson) {
    try {
        $prev = Get-Content -LiteralPath $OutJson -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prev.review_ack -and $prev.ack_head_sha -eq $head) {
            $ackAt = [datetime]::Parse($prev.ack_at_utc).ToUniversalTime()
            $ageH = ((Get-Date).ToUniversalTime() - $ackAt).TotalHours
            if ($ageH -le $RequireAckHours) {
                $payload.review_ack = $true
                $payload.ack_at_utc = $prev.ack_at_utc
                $payload.ack_head_sha = $prev.ack_head_sha
            }
        }
    } catch {
        Write-Host "WARN: could not read prior ack: $_" -ForegroundColor Yellow
    }
}

if ($Ack) {
    $payload.review_ack = $true
    $payload.ack_at_utc = $nowUtc
    $payload.ack_head_sha = $head
    $payload.ack_mode = "cursor_chat"
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
    Write-Host "[OK] Recorded /review ack for HEAD $head" -ForegroundColor Green
    Write-Host "Wrote: $OutJson" -ForegroundColor DarkGray
    exit 0
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8

if ($payload.review_ack) {
    Write-Host "[OK] Pre-push review ack valid for current HEAD (within ${RequireAckHours}h)." -ForegroundColor Green
    exit 0
}

Write-ReviewPrompt
if ($CheckOnly) { exit 2 }
exit 2
