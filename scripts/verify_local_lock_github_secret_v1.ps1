Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Unprotect-DpapiCipher([string]$Cipher) {
    $secure = ConvertTo-SecureString -String $Cipher
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

$key = 'github_mkmlab_v2'
$storePath = Join-Path $env:APPDATA 'MKM\secret_store_v1.json'
$result = [ordered]@{
    schema     = 'local_lock_github_verify_v1'
    key        = $key
    research_only = $true
    send_gate  = 'HOLD'
}

if (-not (Test-Path -LiteralPath $storePath)) {
    $result.ok = $false
    $result.error = 'secret_store_missing'
    $result | ConvertTo-Json -Compress
    exit 1
}

$store = Get-Content -LiteralPath $storePath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $store.$key) {
    $result.ok = $false
    $result.error = 'key_not_in_store'
    $result | ConvertTo-Json -Compress
    exit 1
}

$plain = Unprotect-DpapiCipher -Cipher ([string]$store.$key.encrypted)
if ([string]::IsNullOrWhiteSpace($plain)) {
    $result.ok = $false
    $result.error = 'decrypt_failed'
    $result | ConvertTo-Json -Compress
    exit 1
}

$result.secret_length = $plain.Length
$result.looks_like_github_pat = [bool]($plain -match '^(ghp_|github_pat_|gho_|ghu_)')
$result.looks_like_password = -not $result.looks_like_github_pat

$headers = @{
    Authorization = "Bearer $plain"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'MKM-LocalLock-Verify'
    'X-GitHub-Api-Version' = '2022-11-28'
}

try {
    $user = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers -Method Get -TimeoutSec 20
    $result.ok = $true
    $result.github_login = [string]$user.login
    $result.github_id = [int]$user.id
    $result.message = 'GitHub API accepted stored secret (PAT/token).'
}
catch {
    $status = $null
    if ($_.Exception.Response) {
        $status = [int]$_.Exception.Response.StatusCode
    }
    $result.ok = $false
    $result.http_status = $status
    $result.message = if ($result.looks_like_password) {
        'Stored value does not look like a PAT and GitHub API rejected it — you may have entered account password instead of a PAT.'
    } else {
        'GitHub API rejected the stored PAT/token (wrong, expired, or missing scopes).'
    }
}

$result | ConvertTo-Json -Depth 4
exit $(if ($result.ok) { 0 } else { 1 })
