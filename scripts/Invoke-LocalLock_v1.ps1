[CmdletBinding()]
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [ValidateSet('register', 'identity', 'add', 'who', 'open', 'inject', 'copy', 'run', 'ask', 'menu', 'help')]
    [string]$SubCommand = 'help',

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$Key,

    [Parameter(Mandatory = $false)]
    [ValidateSet('add', 'list')]
    [string]$IdentityAction = 'add',

    [Parameter(Mandatory = $false)]
    [switch]$AutofillEmail,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Passthrough = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$SecretScriptPath = Join-Path $ScriptDir 'Invoke-EncryptedSecretStore.ps1'

function Get-MkmAppDataDir {
    $dir = Join-Path $env:APPDATA 'MKM'
    if (-not (Test-Path -LiteralPath $dir)) {
        [void](New-Item -ItemType Directory -Path $dir -Force)
    }
    return $dir
}

function Get-IdentityStorePath {
    return (Join-Path (Get-MkmAppDataDir) 'dev_identities_v1.json')
}

function Get-JsonPropertyValue($Object, [string]$Name) {
    if ($null -eq $Object) {
        return $null
    }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        return $null
    }
    return $prop.Value
}

function Read-IdentityAutofillFromJson($Value) {
    if ($null -eq $Value) {
        return $null
    }
    $modeRaw = Get-JsonPropertyValue -Object $Value -Name 'mode'
    $mode = if ($modeRaw) { [string]$modeRaw } else { 'email_only' }
    $row = @{ mode = $mode }
    $emailSelector = Get-JsonPropertyValue -Object $Value -Name 'email_selector'
    if ($emailSelector) { $row.email_selector = [string]$emailSelector }
    $passwordSelector = Get-JsonPropertyValue -Object $Value -Name 'password_selector'
    if ($passwordSelector) { $row.password_selector = [string]$passwordSelector }
    $submitSelector = Get-JsonPropertyValue -Object $Value -Name 'submit_selector'
    if ($submitSelector) { $row.submit_selector = [string]$submitSelector }
    return $row
}

function Read-IdentityEntryFromJson($Value) {
    $entry = @{
        account_class = [string]$Value.account_class
        email         = [string]$Value.email
        login_url     = [string]$Value.login_url
        env_var_name  = [string]$Value.env_var_name
    }
    if ($null -ne $Value.browser_tier) {
        $entry.browser_tier = [int]$Value.browser_tier
    }
    if ($null -ne $Value.aliases) {
        $aliases = @()
        foreach ($item in @($Value.aliases)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
                $aliases += [string]$item
            }
        }
        if ($aliases.Count -gt 0) {
            $entry.aliases = $aliases
        }
    }
    $autofill = Read-IdentityAutofillFromJson -Value $Value.autofill
    if ($null -ne $autofill) {
        $entry.autofill = $autofill
    }
    return $entry
}

function Write-IdentityEntryOrdered($Row) {
    $ordered = [ordered]@{
        account_class = $Row.account_class
        email         = $Row.email
        login_url     = $Row.login_url
        env_var_name  = $Row.env_var_name
    }
    if ($Row.ContainsKey('browser_tier') -and $null -ne $Row.browser_tier) {
        $ordered.browser_tier = [int]$Row.browser_tier
    }
    if ($Row.ContainsKey('aliases') -and $Row.aliases -and $Row.aliases.Count -gt 0) {
        $ordered.aliases = @($Row.aliases)
    }
    if ($Row.ContainsKey('autofill') -and $Row.autofill) {
        $autofill = [ordered]@{ mode = $Row.autofill.mode }
        if ($Row.autofill.email_selector) { $autofill.email_selector = $Row.autofill.email_selector }
        if ($Row.autofill.password_selector) { $autofill.password_selector = $Row.autofill.password_selector }
        if ($Row.autofill.submit_selector) { $autofill.submit_selector = $Row.autofill.submit_selector }
        $ordered.autofill = $autofill
    }
    return $ordered
}

function Get-IdentityBrowserTier($Meta) {
    if ($Meta.ContainsKey('browser_tier') -and $null -ne $Meta.browser_tier) {
        return [int]$Meta.browser_tier
    }
    return 3
}

function Get-IdentityAutofillMode($Meta) {
    if ($Meta.ContainsKey('autofill') -and $Meta.autofill -and $Meta.autofill.mode) {
        return [string]$Meta.autofill.mode
    }
    return 'email_only'
}

function Start-LocalLockBrowserAutofill {
    param(
        [string]$IdentityKey,
        [hashtable]$Meta
    )
    $browserScript = Join-Path $ScriptDir 'local_lock_browser_open_v1.py'
    if (-not (Test-Path -LiteralPath $browserScript)) {
        throw "Browser helper missing: $browserScript"
    }
    $payload = [ordered]@{
        key          = $IdentityKey
        login_url    = $Meta.login_url
        email        = $Meta.email
        browser_tier = Get-IdentityBrowserTier -Meta $Meta
        autofill     = $Meta.autofill
    }
    if (-not $payload.autofill) {
        $payload.autofill = [ordered]@{ mode = 'email_only' }
    }
    $tmp = Join-Path $env:TEMP ("local_lock_open_{0}.json" -f ([guid]::NewGuid().ToString()))
    ($payload | ConvertTo-Json -Compress -Depth 6) | Set-Content -LiteralPath $tmp -Encoding UTF8
    $py = (Get-Command py -ErrorAction SilentlyContinue)
    if (-not $py) {
        throw 'Python launcher `py` not found on PATH.'
    }
    Start-Process -FilePath $py.Source -ArgumentList @(
        '-3',
        $browserScript,
        '--meta-file',
        $tmp
    ) -WindowStyle Normal | Out-Null
    Write-Host "[Vault-Browser] Spawned Playwright helper (identity plane only). Meta temp: $tmp" -ForegroundColor Cyan
}

function Read-IdentityStore {
    $path = Get-IdentityStorePath
    if (-not (Test-Path -LiteralPath $path)) {
        return @{}
    }
    $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @{}
    }
    $obj = $raw | ConvertFrom-Json
    $table = @{}
    foreach ($prop in $obj.PSObject.Properties) {
        $table[$prop.Name] = Read-IdentityEntryFromJson -Value $prop.Value
    }
    return $table
}

function Write-IdentityStore([hashtable]$Data) {
    $path = Get-IdentityStorePath
    $ordered = [ordered]@{}
    foreach ($name in ($Data.Keys | Sort-Object)) {
        $ordered[$name] = Write-IdentityEntryOrdered -Row $Data[$name]
    }
    ($ordered | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $path -Encoding UTF8
}

function Resolve-IdentityEntry {
    param(
        [hashtable]$Store,
        [string]$LookupKey
    )
    foreach ($name in $Store.Keys) {
        if ($name -ieq $LookupKey) {
            return @{ Name = $name; Meta = $Store[$name] }
        }
    }
    return $null
}

function Read-SecurePlainPrompt([string]$Prompt) {
    $secure = Read-Host -AsSecureString $Prompt
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Protect-DpapiPlain([string]$Plain) {
    $secure = ConvertTo-SecureString -String $Plain -AsPlainText -Force
    return (ConvertFrom-SecureString -SecureString $secure)
}

function Write-SecretStoreTable([hashtable]$Store) {
    $path = Join-Path (Get-MkmAppDataDir) 'secret_store_v1.json'
    $ordered = [ordered]@{}
    foreach ($name in ($Store.Keys | Sort-Object)) {
        $row = $Store[$name]
        $ordered[$name] = [ordered]@{
            encrypted   = $row.encrypted
            updated_utc = $row.updated_utc
        }
    }
    ($ordered | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $path -Encoding UTF8
}

function Read-SecretStoreTable {
    $path = Join-Path (Get-MkmAppDataDir) 'secret_store_v1.json'
    if (-not (Test-Path -LiteralPath $path)) {
        return @{}
    }
    $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @{}
    }
    $obj = $raw | ConvertFrom-Json
    $table = @{}
    foreach ($prop in $obj.PSObject.Properties) {
        $table[$prop.Name] = @{
            encrypted   = [string]$prop.Value.encrypted
            updated_utc = [string]$prop.Value.updated_utc
        }
    }
    return $table
}

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

function Get-DpapiSecretPlain([string]$SecretKey) {
    $store = Read-SecretStoreTable
    if (-not $store.ContainsKey($SecretKey)) {
        return $null
    }
    $cipher = [string]$store[$SecretKey].encrypted
    if ([string]::IsNullOrWhiteSpace($cipher)) {
        return $null
    }
    try {
        return Unprotect-DpapiCipher -Cipher $cipher
    }
    catch {
        return $null
    }
}

function Set-DpapiSecretPlain([string]$SecretKey, [string]$Plain) {
    $store = Read-SecretStoreTable
    $cipher = Protect-DpapiPlain -Plain $Plain
    $store[$SecretKey] = @{
        encrypted   = $cipher
        updated_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    Write-SecretStoreTable -Store $store
}

function Format-ProcessArgumentString {
    param([string[]]$Parts)
    if ($null -eq $Parts -or $Parts.Count -eq 0) {
        return ''
    }
    $quoted = foreach ($part in $Parts) {
        if ($part -match '[\s"]') {
            '"' + ($part -replace '"', '\"') + '"'
        }
        else {
            $part
        }
    }
    return ($quoted -join ' ')
}

function Start-LocalLockChildWithSecret {
    param(
        [string]$FilePath,
        [string[]]$ArgumentParts,
        [string]$EnvName,
        [string]$SecretValue
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = Format-ProcessArgumentString -Parts $ArgumentParts
    $psi.UseShellExecute = $false

    foreach ($entry in [System.Environment]::GetEnvironmentVariables('Process').GetEnumerator()) {
        $name = [string]$entry.Key
        $psi.EnvironmentVariables[$name] = [string]$entry.Value
    }
    $psi.EnvironmentVariables[$EnvName] = $SecretValue

    $proc = [System.Diagnostics.Process]::Start($psi)
    if ($null -eq $proc) {
        throw "Failed to start child process: $FilePath"
    }
    $proc.WaitForExit()
    return $proc.ExitCode
}

function Get-RunCommandPartsFromArgs {
    param([object[]]$RawArgs)
    $list = @($RawArgs | ForEach-Object { [string]$_ })
    $sepIdx = [Array]::IndexOf($list, '::')
    if ($sepIdx -lt 0) {
        $sepIdx = [Array]::IndexOf($list, '--')
    }
    if ($sepIdx -lt 0) {
        throw "run requires '::' before child command. Example: run mykey :: py -c ""print(1)"""
    }
    if ($sepIdx -ge ($list.Count - 1)) {
        throw "No command specified after '::'."
    }
    return ,$list[($sepIdx + 1)..($list.Count - 1)]
}

function Resolve-ExecutablePath {
    param([string]$CommandToken)
    if ([string]::IsNullOrWhiteSpace($CommandToken)) {
        throw 'Empty command token.'
    }
    if ($CommandToken -match '[\\/]') {
        return $CommandToken
    }
    $cmd = Get-Command $CommandToken -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $CommandToken
}

function Invoke-LocalLockIdentityAddKey {
    param([string]$IdentityKey)

    if ([string]::IsNullOrWhiteSpace($IdentityKey)) {
        throw 'Key is required for identity add.'
    }

    $email = Read-Host 'Enter login email/account'
    $url = Read-Host 'Enter login URL (optional)'
    $envVar = Read-Host "Enter target environment variable name [default: $($IdentityKey.ToUpper())]"
    if ([string]::IsNullOrWhiteSpace($envVar)) {
        $envVar = $IdentityKey.ToUpper()
    }
    $class = Read-Host 'Enter account_class (personal|company|dummy|development) [default: development]'
    if ([string]::IsNullOrWhiteSpace($class)) {
        $class = 'development'
    }

    $store = Read-IdentityStore
    $store[$IdentityKey] = @{
        account_class = $class
        email         = $email
        login_url     = $url
        env_var_name  = $envVar.ToUpper()
    }
    Write-IdentityStore -Data $store
    Write-Host "[Identity] Registered metadata for '$IdentityKey'." -ForegroundColor Green
}

function Invoke-LocalLockRegisterKey {
    param([string]$IdentityKey)

    if ([string]::IsNullOrWhiteSpace($IdentityKey)) {
        throw 'Key is required for register.'
    }
    $plain = Read-SecurePlainPrompt "Enter secret value for '$IdentityKey' (input hidden)"
    if ([string]::IsNullOrWhiteSpace($plain)) {
        throw 'Empty secret rejected.'
    }
    Set-DpapiSecretPlain -SecretKey $IdentityKey -Plain $plain
    Write-Host "[Secret] Registered key '$IdentityKey' in DPAPI store (value redacted)." -ForegroundColor Green
}

function Invoke-LocalLockOpenKey {
    param(
        [string]$IdentityKey,
        [switch]$UseAutofillEmail
    )

    $store = Read-IdentityStore
    if ($store.Count -eq 0) {
        throw "Identity registry missing or empty. Run: lock add $IdentityKey"
    }
    $resolved = Resolve-IdentityEntry -Store $store -LookupKey $IdentityKey
    if (-not $resolved) {
        throw "Key '$IdentityKey' not found in identity registry."
    }
    $idName = $resolved.Name
    $meta = $resolved.Meta
    if ([string]::IsNullOrWhiteSpace($meta.login_url)) {
        throw "login_url missing for '$idName'."
    }
    $tier = Get-IdentityBrowserTier -Meta $meta
    $mode = Get-IdentityAutofillMode -Meta $meta
    if (-not [string]::IsNullOrWhiteSpace($meta.email)) {
        Set-Clipboard -Value $meta.email
    }
    if ($UseAutofillEmail -and $tier -eq 3 -and $mode -ne 'none') {
        try {
            Start-LocalLockBrowserAutofill -IdentityKey $idName -Meta $meta
            Write-Host '[Identity] AutofillEmail tier-3 helper spawned. Enter password manually.' -ForegroundColor Cyan
            return
        }
        catch {
            Write-Warning "AutofillEmail helper failed; falling back to default browser. $($_.Exception.Message)"
        }
    }
    Start-Process $meta.login_url
    if ($UseAutofillEmail) {
        Write-Host '[Identity] Tier-2/default fallback: login page opened; email on clipboard when set.' -ForegroundColor Cyan
    }
    else {
        Write-Host '[Identity] Opened login page. Email copied to clipboard when set.' -ForegroundColor Cyan
    }
}

function Invoke-LocalLockInjectKey {
    param([string]$IdentityKey)

    $store = Read-IdentityStore
    $resolved = Resolve-IdentityEntry -Store $store -LookupKey $IdentityKey
    if (-not $resolved) {
        throw "Key '$IdentityKey' not found in identity registry."
    }
    $idName = $resolved.Name
    $meta = $resolved.Meta
    $secret = Get-DpapiSecretPlain -SecretKey $idName
    if ($null -eq $secret) {
        throw "No DPAPI secret for key '$idName'. Run: lock register $idName"
    }
    $envName = if (-not [string]::IsNullOrWhiteSpace($meta.env_var_name)) {
        $meta.env_var_name
    }
    else {
        $idName.ToUpper()
    }
    Set-Item -Path "env:$envName" -Value $secret
    Write-Host "[Secret] Injected into `$env:$envName (value redacted)." -ForegroundColor Green
}

function Invoke-LocalLockCopyKey {
    param([string]$IdentityKey)

    $store = Read-IdentityStore
    $resolved = Resolve-IdentityEntry -Store $store -LookupKey $IdentityKey
    if (-not $resolved) {
        throw "Key '$IdentityKey' not found in identity registry."
    }
    $idName = $resolved.Name
    $secret = Get-DpapiSecretPlain -SecretKey $idName
    if ($null -eq $secret) {
        throw "No DPAPI secret for key '$idName'. Run: lock register $idName"
    }
    Set-Clipboard -Value $secret
    Write-Host '[Secret] Copied to clipboard (opt-in). Clear clipboard after use.' -ForegroundColor Yellow
}

function Select-LocalLockIdentityKeyFromMenu {
    param([string]$Prompt = 'Select account number')

    $store = Read-IdentityStore
    $names = @($store.Keys | Sort-Object)
    if ($names.Count -eq 0) {
        Write-Host '[LocalLock] No identities registered. Use menu option 4 (add).' -ForegroundColor Yellow
        return $null
    }
    for ($i = 0; $i -lt $names.Count; $i++) {
        $row = $store[$names[$i]]
        $email = if ($row.email) { $row.email } else { '-' }
        Write-Host ("[{0}] {1}  ({2})" -f ($i + 1), $names[$i], $email)
    }
    $pick = Read-Host $Prompt
    if ([string]::IsNullOrWhiteSpace($pick)) {
        return $null
    }
    if ($pick -match '^\d+$') {
        $idx = [int]$pick - 1
        if ($idx -ge 0 -and $idx -lt $names.Count) {
            return $names[$idx]
        }
    }
    $resolved = Resolve-IdentityEntry -Store $store -LookupKey $pick
    if ($resolved) {
        return $resolved.Name
    }
    Write-Host "[LocalLock] Invalid selection: $pick" -ForegroundColor Yellow
    return $null
}

function Show-LocalLockInteractiveMenu {
    while ($true) {
        Write-Host ''
        Write-Host 'MKM Commander Vault - interactive menu' -ForegroundColor Cyan
        Write-Host '--------------------------------------'
        Write-Host '1) Find account (natural-language ask -> resolved_key)'
        Write-Host '2) Inject secret into current shell env'
        Write-Host '3) Web login (open URL + email autofill when tier 3)'
        Write-Host '4) Register new account (metadata + secret, terminal only)'
        Write-Host '5) Copy secret to clipboard'
        Write-Host '6) Exit'
        Write-Host '--------------------------------------'
        $choice = Read-Host 'Select (1-6)'
        switch ($choice) {
            '1' {
                $query = Read-Host 'Describe the service or alias'
                if (-not [string]::IsNullOrWhiteSpace($query)) {
                    [void](Invoke-LocalLockAskQuery -Query $query -NoExit)
                }
            }
            '2' {
                $key = Select-LocalLockIdentityKeyFromMenu -Prompt 'Account number for inject'
                if ($key) { Invoke-LocalLockInjectKey -IdentityKey $key }
            }
            '3' {
                $key = Select-LocalLockIdentityKeyFromMenu -Prompt 'Account number for web login'
                if ($key) { Invoke-LocalLockOpenKey -IdentityKey $key -UseAutofillEmail }
            }
            '4' {
                $newKey = Read-Host 'New identity key (e.g. vercel_prod)'
                if (-not [string]::IsNullOrWhiteSpace($newKey)) {
                    Invoke-LocalLockIdentityAddKey -IdentityKey $newKey
                    $registerNow = Read-Host "Register secret now for '$newKey'? [Y/n]"
                    if ([string]::IsNullOrWhiteSpace($registerNow) -or $registerNow -match '^[Yy]') {
                        Invoke-LocalLockRegisterKey -IdentityKey $newKey
                    }
                }
            }
            '5' {
                $key = Select-LocalLockIdentityKeyFromMenu -Prompt 'Account number for clipboard copy'
                if ($key) { Invoke-LocalLockCopyKey -IdentityKey $key }
            }
            '6' {
                return
            }
            default {
                Write-Host '[LocalLock] Invalid menu choice.' -ForegroundColor Yellow
            }
        }
    }
}

function Invoke-LocalLockAskQuery {
    param(
        [string]$Query,
        [switch]$NoExit
    )
    $askScript = Join-Path $ScriptDir 'local_lock_ask_v1.py'
    if (-not (Test-Path -LiteralPath $askScript)) {
        throw "Ask helper missing: $askScript"
    }
    $py = Get-Command py -ErrorAction Stop
    & $py.Source '-3' $askScript '--query' $Query
    $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    if ($NoExit) {
        return $code
    }
    exit $code
}

function Show-LocalLockHelp {
    Write-Host @"
Invoke-LocalLock P2.5 — Local credential facade (MKM B-track · research_only)

Shell shortcut (one-time):
  powershell -File scripts\Register-LocalLockShellAlias_v1.ps1 -IncludeKoreanAlias -ReloadProfile
  lock ...                 # or: 비번관리  (opens menu)

  menu                     Interactive numbered menu (password prompts stay in terminal)
  add <key>                Shorthand for identity add <key>
  register <key>           Interactive DPAPI secret registration (no argv secrets)
  identity add <key>       Interactive identity metadata (email, login_url, env_var_name)
  identity list            List identity keys (no secrets)
  who <key>                Print identity metadata only
  ask <query...>           Fuzzy intent -> resolved_key JSON (metadata only; optional Ollama)
  open <key>               Copy email to clipboard; open login_url in default browser
  open <key> -AutofillEmail
                           Tier 3: Playwright Chrome profile (email autofill; human password)
  inject <key>             Inject secret into current session env (stdout redacted)
  copy <key>               Copy secret to clipboard (explicit opt-in)
  run <key> :: <cmd...>    Child-process env inject only (op-run pattern)

Quick examples (after alias install):
  lock menu
  lock add vercel_prod
  lock register vercel_prod
  lock ask "orange test database"
  lock open supabase_dev -AutofillEmail

SSOT: docs/final/schemas/dev_identities_v1.schema.json
Alias: scripts/Register-LocalLockShellAlias_v1.ps1
Guard: .cursor/rules/local-lock-security-guard-v1.mdc
"@ -ForegroundColor Cyan
}

if ($SubCommand -eq 'help') {
    Show-LocalLockHelp
    exit 0
}

if ($SubCommand -eq 'identity') {
    if ($Key -eq 'list') {
        $IdentityAction = 'list'
        $Key = $null
    }
    elseif ($Key -eq 'add') {
        $IdentityAction = 'add'
        $Key = $null
    }
    elseif (-not [string]::IsNullOrWhiteSpace($Key)) {
        $IdentityAction = 'add'
    }
}

switch ($SubCommand) {
    'menu' {
        Show-LocalLockInteractiveMenu
        exit 0
    }

    'add' {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw 'Key is required for add.'
        }
        Invoke-LocalLockIdentityAddKey -IdentityKey $Key
        exit 0
    }

    'register' {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for register."
        }
        Invoke-LocalLockRegisterKey -IdentityKey $Key
        exit 0
    }

    'identity' {
        if ($IdentityAction -eq 'list') {
            $store = Read-IdentityStore
            $rows = @()
            foreach ($name in ($store.Keys | Sort-Object)) {
                $row = $store[$name]
                $item = [ordered]@{
                    key           = $name
                    account_class = $row.account_class
                    email         = $row.email
                    env_var_name  = $row.env_var_name
                    login_url     = $row.login_url
                    browser_tier  = Get-IdentityBrowserTier -Meta $row
                }
                if ($row.ContainsKey('aliases') -and $row.aliases) {
                    $item.aliases = @($row.aliases)
                }
                if ($row.ContainsKey('autofill') -and $row.autofill) {
                    $item.autofill_mode = $row.autofill.mode
                }
                $rows += $item
            }
            [PSCustomObject]@{
                schema          = 'dev_identities_list_v1'
                count           = $rows.Count
                identities      = $rows
                research_only   = $true
                send_gate       = 'HOLD'
            } | ConvertTo-Json -Depth 6
            exit 0
        }

        if ($IdentityAction -ne 'add') {
            throw "Unsupported identity action: $IdentityAction"
        }
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for identity add."
        }
        Invoke-LocalLockIdentityAddKey -IdentityKey $Key
        exit 0
    }

    'ask' {
        $queryParts = @()
        if (-not [string]::IsNullOrWhiteSpace($Key)) {
            $queryParts += $Key
        }
        if ($Passthrough.Count -gt 0) {
            $queryParts += $Passthrough
        }
        $query = ($queryParts -join ' ').Trim()
        if ([string]::IsNullOrWhiteSpace($query)) {
            throw 'ask requires a natural-language query.'
        }
        Invoke-LocalLockAskQuery -Query $query
    }

    default {
        if ([string]::IsNullOrWhiteSpace($Key)) {
            throw "Key is required for subcommand '$SubCommand'."
        }
        $store = Read-IdentityStore
        if ($store.Count -eq 0) {
            throw "Identity registry missing or empty. Run: Invoke-LocalLock identity add $Key"
        }
        $resolved = Resolve-IdentityEntry -Store $store -LookupKey $Key
        if (-not $resolved) {
            Write-Warning "Key '$Key' not found in identity registry."
            exit 1
        }
        $idName = $resolved.Name
        $meta = $resolved.Meta

        switch ($SubCommand) {
            'who' {
                $who = [ordered]@{
                    key           = $idName
                    account_class = $meta.account_class
                    email         = $meta.email
                    env_var_name  = $meta.env_var_name
                    login_url     = $meta.login_url
                    browser_tier  = Get-IdentityBrowserTier -Meta $meta
                }
                if ($meta.ContainsKey('aliases') -and $meta.aliases) {
                    $who.aliases = @($meta.aliases)
                }
                if ($meta.ContainsKey('autofill') -and $meta.autofill) {
                    $who.autofill = $meta.autofill
                }
                [PSCustomObject]$who | ConvertTo-Json -Depth 6
                exit 0
            }

            'open' {
                Invoke-LocalLockOpenKey -IdentityKey $idName -UseAutofillEmail:$AutofillEmail
                exit 0
            }

            'inject' {
                Invoke-LocalLockInjectKey -IdentityKey $idName
                exit 0
            }

            'copy' {
                Invoke-LocalLockCopyKey -IdentityKey $idName
                exit 0
            }

            'run' {
                $commandParts = Get-RunCommandPartsFromArgs -RawArgs $Passthrough
                $secret = Get-DpapiSecretPlain -SecretKey $idName
                if ($null -eq $secret) {
                    throw "No DPAPI secret for key '$idName'. Run: Invoke-LocalLock register $idName"
                }
                $envName = if (-not [string]::IsNullOrWhiteSpace($meta.env_var_name)) {
                    $meta.env_var_name
                }
                else {
                    $idName.ToUpper()
                }
                $exeToken = $commandParts[0]
                $argParts = @()
                if ($commandParts.Count -gt 1) {
                    $argParts = $commandParts[1..($commandParts.Count - 1)]
                }
                $exePath = Resolve-ExecutablePath -CommandToken $exeToken
                $exitCode = Start-LocalLockChildWithSecret `
                    -FilePath $exePath `
                    -ArgumentParts $argParts `
                    -EnvName $envName `
                    -SecretValue $secret
                Write-Host "[Secret] Child run finished for `$env:$envName (value redacted). exit=$exitCode" -ForegroundColor Green
                exit $exitCode
            }
        }
    }
}

throw "Unhandled subcommand: $SubCommand"
