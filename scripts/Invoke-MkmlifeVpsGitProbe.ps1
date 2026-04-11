<#
.SYNOPSIS
  mkmlife VPS에 SSH로 접속해 Git HEAD / origin/main만 조회한다 (배포 없음).

.DESCRIPTION
  Windows PowerShell에서 흔한 실수를 막는다:
  - VPS_HOST에 예시 문자열·플레이스홀더가 들어간 경우
  - VPS_SSH_KEY 비어 있음 → ssh가 `Identity file @` 같은 인자로 깨지는 경우
  - 큰따옴표 안에 원격 `&&`를 넣어 호스트명이 깨지는 경우

  원격 명령은 항상 단일 인자(작은따옴표 문자열)로 전달한다.

.PARAMETER VpsHostname
  VPS 호스트(IP 또는 DNS). 미지정 시 환경변수 VPS_HOST. (이름을 Host로 두면 PowerShell 자동 변수 $Host와 충돌한다.)

.PARAMETER SshUser
  SSH 사용자. 미지정 시 환경변수 VPS_USER (필수).

.PARAMETER IdentityPath
  개인키 경로. 미지정 시 VPS_SSH_KEY, 없으면 F:\workspace\.ssh\hostinger_mkmlife (SSOT 기본).

.PARAMETER RemoteRepoPath
  원격에서 cd할 경로 (기본 /var/www/mkmlife_runtime/mkm-life).

.EXAMPLE
  $env:VPS_HOST = '203.0.113.10'; $env:VPS_USER = 'root'
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
    $bad = @(
        "실제_호스트", "여기에_진짜", "your.vps.host", "your-vps-host",
        "example.com", "example.org", "placeholder", "changeme", "tbd",
        "xxx", "localhost", "127.0.0.1", "<", ">"
    )
    foreach ($b in $bad) {
        if ($t -match [regex]::Escape($b)) { return $true }
    }
    if ($t -like "*예시*" -or $t -like "*실제*도메인*" -or $t -like "*진짜*") { return $true }
    return $false
}

$vpsHost = if ($PSBoundParameters.ContainsKey("VpsHostname") -and -not [string]::IsNullOrWhiteSpace($VpsHostname)) { $VpsHostname } else { $env:VPS_HOST }
$vpsUser = if ($PSBoundParameters.ContainsKey("SshUser") -and -not [string]::IsNullOrWhiteSpace($SshUser)) { $SshUser } else { $env:VPS_USER }

$key = $IdentityPath
if ([string]::IsNullOrWhiteSpace($key)) {
    $key = $env:VPS_SSH_KEY
}
if ([string]::IsNullOrWhiteSpace($key)) {
    $key = "F:\workspace\.ssh\hostinger_mkmlife"
}

if (Test-PlaceholderHost $vpsHost) {
    throw @"
VPS_HOST is missing or looks like a placeholder ('$vpsHost').
Set a real public IP or SSH hostname (Hostinger dashboard / your ~/.ssh/config / deploy script), e.g.:
  `$env:VPS_HOST = '203.0.113.10'
See docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md §2.2
"@
}

if ([string]::IsNullOrWhiteSpace($vpsUser)) {
    throw "VPS_USER is not set. Example: `$env:VPS_USER = 'root'"
}

if (-not (Test-Path -LiteralPath $key)) {
    throw "SSH key file not found: $key`nSet VPS_SSH_KEY to your key path or place the default key (SSOT: F:\workspace\.ssh\hostinger_mkmlife)."
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
$remote = "cd $RemoteRepoPath && git rev-parse HEAD && git fetch origin -q && git rev-parse origin/main"

Write-Host "=== Mkmlife VPS Git probe ===" -ForegroundColor Cyan
Write-Host "Target: $target"
Write-Host "Identity: $key"
Write-Host "Remote: $remote"
Write-Host ""

& $ssh.Source -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new $target $remote
exit $LASTEXITCODE
