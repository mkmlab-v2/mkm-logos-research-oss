param(
    [string]$OutPath = "reports/hostinger_exit_monitor_probe_latest.json",
    [int]$TimeoutSec = 20,
    [string[]]$Domains = @("no1kmedi.com", "mkmlife.com", "jema-ai.com", "jema12.com", "jemaai.cloud"),
    [string[]]$HttpsGateDomains = @()
)

$results = @()
foreach ($domain in $Domains) {
    $row = [ordered]@{
        timestamp_utc   = (Get-Date).ToUniversalTime().ToString("o")
        domain          = $domain
        http_status     = "ERR"
        server_header   = ""
        cf_ray_present  = $false
        hsts_present    = $false
        ns              = @()
        a_records       = @()
        mx              = @()
        txt             = @()
        ok              = $false
    }

    try {
        $resp = Invoke-WebRequest -Uri ("https://" + $domain) -Method Head -MaximumRedirection 5 -TimeoutSec $TimeoutSec
        $row.http_status = [int]$resp.StatusCode
        $row.server_header = (($resp.Headers["Server"] | ForEach-Object { $_.ToString() }) -join " ").Trim()
        $row.cf_ray_present = [bool]$resp.Headers["CF-RAY"]
        $row.hsts_present = [bool]$resp.Headers["Strict-Transport-Security"]
    }
    catch {
        $row.http_status = "ERR"
    }

    $row.ns = @(Resolve-DnsName -Name $domain -Type NS -ErrorAction SilentlyContinue | ForEach-Object {
            $nh = $_.PSObject.Properties['NameHost']
            if ($null -ne $nh -and $null -ne $nh.Value) { [string]$nh.Value.Trim() }
        } | Where-Object { $_ } | Select-Object -Unique)

    $row.a_records = @(Resolve-DnsName -Name $domain -Type A -ErrorAction SilentlyContinue | ForEach-Object {
            $ip = $_.PSObject.Properties['IPAddress']
            if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
        } | Where-Object { $_ } | Select-Object -Unique)

    $row.mx = @(Resolve-DnsName -Name $domain -Type MX -ErrorAction SilentlyContinue | ForEach-Object {
            $pref = $_.PSObject.Properties['Preference']
            $ex = $_.PSObject.Properties['NameExchange']
            $p = if ($null -ne $pref -and $null -ne $pref.Value) { [string]$pref.Value } else { "" }
            $e = if ($null -ne $ex -and $null -ne $ex.Value) { [string]$ex.Value.Trim() } else { "" }
            if ($e) { [pscustomobject]@{ pref = [int]($p); line = "$p $e" } }
        } | Where-Object { $_ } | Sort-Object -Property pref | ForEach-Object { $_.line } | Select-Object -Unique)

    $row.txt = @(Resolve-DnsName -Name $domain -Type TXT -ErrorAction SilentlyContinue | ForEach-Object {
            $st = $_.PSObject.Properties['Strings']
            if ($null -ne $st -and $null -ne $st.Value) { (@($st.Value) -join "") }
        } | Where-Object { $_ } | Select-Object -Unique)

    $statusOk = ($row.http_status -is [int]) -and ($row.http_status -ge 200) -and ($row.http_status -lt 400)
    $row.ok = $statusOk
    $results += [pscustomobject]$row
}

$summary = [pscustomobject]@{
    generated_at_utc    = (Get-Date).ToUniversalTime().ToString("o")
    domains_total       = $results.Count
    domains_ok          = (@($results | Where-Object { $_.ok }).Count)
    domains_err         = (@($results | Where-Object { -not $_.ok }).Count)
    https_gate_domains  = @($HttpsGateDomains)
    https_gate_failures = $(if ($HttpsGateDomains.Count -gt 0) {
            (@($results | Where-Object {
                        $gd = $_.domain.ToString()
                        ($HttpsGateDomains | ForEach-Object { $_.ToString() }) -contains $gd -and -not $_.ok
                    })).Count
        }
        else { $null })
    results             = $results
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $OutPath -Encoding UTF8
Write-Output "WROTE $OutPath"

$exitFail = $false
if ($HttpsGateDomains.Count -gt 0) {
    $exitFail = (@($results | Where-Object {
                $gd = $_.domain.ToString()
                ($HttpsGateDomains | ForEach-Object { $_.ToString() }) -contains $gd -and -not $_.ok
            })).Count -gt 0
}
else {
    $exitFail = $summary.domains_err -gt 0
}
if ($exitFail) { exit 1 }
exit 0
