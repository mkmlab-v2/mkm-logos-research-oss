<#
.SYNOPSIS
  mkmlife VPS에 SSH로 접속해 Git HEAD / origin/main만 조회한다 (배포 없음).

.DESCRIPTION
  Windows PowerShell에서 흔한 실수를 막는다:
  - VPS_HOST에 예시 문자열·플레이스홀더가 들어간 경우
  - VPS_SSH_KEY / MKM_VPS_SSH_KEY_PATH 비어 있음 → ssh가 `Identity file @` 같은 인자로 깨지는 경우
  - 큰따옴표 안에 원격 `&&`를 넣어 호스트명이 깨지는 경우

  원격 명령은 항상 단일 인자(작은따옴표 문자열)로 전달한다.

.PARAMETER VpsHostname
  VPS 호스트(IP 또는 DNS). 미지정 시 VPS_HOST, 없으면 MKM_VPS_HOST (Invoke-VpsOpsSmoke_v1.ps1 과 동일 규약).

.PARAMETER SshUser
  SSH 사용자. 미지정 시 VPS_USER, 없으면 MKM_VPS_USER (필수).

.PARAMETER IdentityPath
  개인키 경로. 미지정 시 VPS_SSH_KEY, MKM_VPS_SSH_KEY_PATH, SSH_KEY_PATH 순, 없으면 SSOT 기본 경로 후보(존재하는 첫 파일).

.PARAMETER RemoteRepoPath
  원격에서 cd할 경로 (기본 /var/www/mkmlife_runtime/mkm-life).

.EXAMPLE
  $env:VPS_HOST = '203.0.113.10'; $env:VPS_USER = 'root'
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmlifeVpsGitProbe.ps1

.EXAMPLE
  $env:MKM_VPS_HOST = '203.0.113.10'; $env:MKM_VPS_USER = 'ubuntu'; $env:MKM_VPS_SSH_KEY_PATH = 'C:\Users\YOU\.ssh\id_ed25519_mkm'
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmlifeVpsGitProbe.ps1
#>
param(
    [string]$VpsHostname,
    [string]$SshUser,
    [string]$IdentityPath,
    [string]$RemoteRepoPath = "/var/www/mkmlife_runtime/mkm-life"
)

$ErrorActionPreference = "Stop"

function Test-PlaceholderHost([string]$h) {
    if ([string]::IsNullOrWhiteSpace($h)) { return $true }
    $t = $h.Trim()
    # ASCII-only in source file so Windows PowerShell 5.x parses without UTF-8 BOM.
    $bad = @(
        "your.vps.host", "your-vps-host", "example.com", "example.org",
        "placeholder", "changeme", "tbd", "xxx", "localhost", "127.0.0.1",
        "<", ">", "real_ip_or_ssh_hostname", "fill_here", "replace_me"
    )
    foreach ($b in $bad) {
        if ($t -match [regex]::Escape($b)) { return $true }
    }
    # Korean doc placeholders via codepoints (no Hangul literals in .ps1).
    $fragments = @(
        ([char]0xC2E4) + ([char]0xC81C) + '_' + ([char]0xD638) + ([char]0xC2A4) + ([char]0xD2B8),
        ([char]0xC5EC) + ([char]0xAE30) + ([char]0xC5D0) + '_' + ([char]0xC9C4) + ([char]0xC9DC),
        ([char]0xC608) + ([char]0xC2DC)
    )
    foreach ($frag in $fragments) {
        if ($t.Contains($frag)) { return $true }
    }
    return $false
}

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$vpsHost = if ($PSBoundParameters.ContainsKey("VpsHostname") -and -not [string]::IsNullOrWhiteSpace($VpsHostname)) {
    $VpsHostname
}
else {
    $h = $env:VPS_HOST
    if ([string]::IsNullOrWhiteSpace($h)) { $h = $env:MKM_VPS_HOST }
    $h
}

$vpsUser = if ($PSBoundParameters.ContainsKey("SshUser") -and -not [string]::IsNullOrWhiteSpace($SshUser)) {
    $SshUser
}
else {
    $u = $env:VPS_USER
    if ([string]::IsNullOrWhiteSpace($u)) { $u = $env:MKM_VPS_USER }
    $u
}

$key = $IdentityPath
if ([string]::IsNullOrWhiteSpace($key)) {
    foreach ($p in @($env:VPS_SSH_KEY, $env:MKM_VPS_SSH_KEY_PATH, $env:SSH_KEY_PATH)) {
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        $cand = $p.Trim()
        if (Test-Path -LiteralPath $cand) {
            $key = $cand
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($key)) {
    # Prefer user profile (typical Hostinger deploy key), then repo .ssh, then legacy F: path.
    foreach ($c in @(
            (Join-Path $env:USERPROFILE '.ssh\hostinger_mkmlife'),
            (Join-Path $workspaceRoot '.ssh\hostinger_mkmlife'),
            "F:\workspace\.ssh\hostinger_mkmlife"
        )) {
        if (Test-Path -LiteralPath $c) {
            $key = $c
            break
        }
    }
}

if (Test-PlaceholderHost $vpsHost) {
    throw @"
VPS host is missing or looks like a placeholder ('$vpsHost').
Set a real public IP or SSH hostname (Hostinger dashboard / your ~/.ssh/config / deploy script), e.g.:
  `$env:VPS_HOST = '203.0.113.10'   or   `$env:MKM_VPS_HOST = '203.0.113.10'
See docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md (section 2.2)
"@
}

if ([string]::IsNullOrWhiteSpace($vpsUser)) {
    throw "SSH user is not set. Set `$env:VPS_USER or `$env:MKM_VPS_USER (e.g. 'root' or 'ubuntu')."
}

if (-not (Test-Path -LiteralPath $key)) {
    throw "SSH key file not found: $key`nSet VPS_SSH_KEY, MKM_VPS_SSH_KEY_PATH, or SSH_KEY_PATH; or place hostinger_mkmlife under workspace .ssh or USERPROFILE\.ssh\ (see Invoke-VpsOpsSmoke_v1.ps1)."
}

$ssh = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $ssh) { $ssh = Get-Command ssh -ErrorAction SilentlyContinue }
if (-not $ssh) {
    throw "ssh not found. Install OpenSSH client or use Git for Windows ssh."
}

if ($RemoteRepoPath -notmatch '^/[-a-zA-Z0-9_/]+$') {
    throw "RemoteRepoPath must be a simple absolute path (letters, digits, underscore, slash only)."
}

$target = "${vpsUser}@${vpsHost}"
# One argv to ssh.exe: remote shell runs this as a single command string (no PS double-quote splatting).
$remote = 'cd ' + $RemoteRepoPath + ' && git rev-parse HEAD && git fetch origin -q && git rev-parse origin/main'

Write-Host "=== Mkmlife VPS Git probe ===" -ForegroundColor Cyan
Write-Host "Target: $target"
Write-Host "Identity: $key"
Write-Host "Remote: $remote"
Write-Host ""

& $ssh.Source -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new $target $remote
exit $LASTEXITCODE
