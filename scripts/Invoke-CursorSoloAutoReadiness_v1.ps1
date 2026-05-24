#Requires -Version 5.1
<#
.SYNOPSIS
  1인 개발 + Cursor Auto(무제한) 기준 로컬 IDE 준비도 점검 (유료 Cloud/Composer Fast 제외).

.DESCRIPTION
  순서: P0 경로 -> 비밀 하이브리드(DPAPI 위생) -> (선택) NotebookLM MCP prereq.
  통과 후 Settings 수동 체크리스트(스킬 핀·worktree·MCP 정리)를 stdout에 출력한다.

  SSOT: .cursor/environment/README.md 「1인 · Auto 무제한」

.PARAMETER SkipMcpProbe
  NotebookLM MCP prereq 프로브 생략.

.PARAMETER OutJson
  요약 JSON 경로 (기본 reports/cursor_solo_auto_readiness_latest.json).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorSoloAutoReadiness_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipMcpProbe,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $WorkspaceRoot) {
    $WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
        $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
    } else {
        (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    }
}

if (-not $OutJson) {
    $OutJson = Join-Path $WorkspaceRoot 'reports\cursor_solo_auto_readiness_latest.json'
}

$ps = 'powershell.exe'
$common = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File')
$steps = [ordered]@{}
$failed = $false

function Invoke-Step {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$ExtraArgs = @()
    )
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Missing script: $ScriptPath"
    }
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $ps @common $ScriptPath @ExtraArgs
    $code = $LASTEXITCODE
    $steps[$Name] = @{ exit_code = $code; script = $ScriptPath }
    if ($code -ne 0) { $script:failed = $true }
    return $code
}

Push-Location -LiteralPath $WorkspaceRoot
try {
    Invoke-Step -Name 'p0_constitution_gate_paths' -ScriptPath (Join-Path $PSScriptRoot 'verify_p0_constitution_gate_paths.ps1') | Out-Null
    Invoke-Step -Name 'secrets_hybrid_readiness' -ScriptPath (Join-Path $PSScriptRoot 'Invoke-MkmSecretsHybridReadiness_v1.ps1') | Out-Null

    if (-not $SkipMcpProbe) {
        $mcpOut = Join-Path $WorkspaceRoot 'reports\cursor_solo_auto_mcp_prereq_latest.json'
        Invoke-Step -Name 'notebooklm_mcp_prereq' -ScriptPath (Join-Path $PSScriptRoot 'Invoke-McpHygieneProbe.ps1') -ExtraArgs @(
            '-WorkspaceRoot', $WorkspaceRoot,
            '-OutJson', $mcpOut
        ) | Out-Null
    }

    $pub = Join-Path $PSScriptRoot 'Show-RemotePublicationMode.ps1'
    if (Test-Path -LiteralPath $pub) {
        Write-Host '==> remote_publication_mode' -ForegroundColor Cyan
        & $ps @common $pub
        $steps['remote_publication_mode'] = @{ exit_code = $LASTEXITCODE; script = $pub }
    }

    $summary = [ordered]@{
        schema          = 'cursor_solo_auto_readiness_v1'
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        workspace_root  = $WorkspaceRoot
        billing_mode    = 'cursor_auto_unlimited_local_first'
        steps           = $steps
        ok              = -not $failed
        manual_settings = @(
            'Model: Auto (default). Skip Composer 2.5 Fast / per-token premium unless needed.'
            'Pin skills (Settings): mkm-dispatch-vip-pipeline, Fact-Lock persona triggers; avoid live-trade pins.'
            'Agents Window: use /worktree or worktrees for b-track experiments; keep main clean.'
            'Plans: Build in Parallel only when file paths do not overlap (compression vs prophecy chats).'
            'MCP: disable servers unused in this chat (NotebookLM only when ingesting).'
            'Skip unless working: Cloud Agent env, Teams @Cursor, Bugbot (gitea/internal is SSOT).'
        )
        pointers = @(
            '.cursor/environment/README.md'
            'projects/bitcoin-trading/ops/v2/CURSOR_CHANGELOG_INTEGRATION_PLAN_2026-03-24.md'
            'docs/final/CURRENT_OPS_SNAPSHOT.md'
        )
    }

    $outDir = Split-Path -Parent $OutJson
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    ($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $OutJson -Encoding utf8

    Write-Host ''
    Write-Host '--- Cursor solo / Auto (manual in Settings) ---' -ForegroundColor Yellow
    foreach ($line in $summary.manual_settings) {
        Write-Host "  • $line"
    }
    Write-Host ''
    Write-Host "JSON: $OutJson" -ForegroundColor DarkGray

    if ($failed) {
        Write-Host 'Invoke-CursorSoloAutoReadiness_v1: FAILED (see step exit codes)' -ForegroundColor Red
        exit 1
    }
    Write-Host 'Invoke-CursorSoloAutoReadiness_v1: OK (exit 0)' -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
