param(
    [string[]]$Domains = @("no1kmedi.com", "mkmlife.com", "jema-ai.com", "jema12.com"),
    [int]$TimeoutSec = 20,
    [string]$OutPath = "reports/hostinger_exit_monitor_probe_latest.json"
)

$results = @()
foreach ($domain in $Domains) {
    $row = [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        domain = $domain
        http_status = "ERR"
        server_header = ""
        cf_ray_present = $false
        hsts_present = $false
        ns = @()
        a_records = @()
        mx = @()
        txt = @()
        ok = $false
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

    $row.ns = @(Resolve-DnsName -Name $domain -Type NS -ErrorAction SilentlyContinue | ForEach-Object { $_.NameHost } | Select-Object -Unique)
    $row.a_records = @(Resolve-DnsName -Name $domain -Type A -ErrorAction SilentlyContinue | ForEach-Object { $_.IPAddress } | Select-Object -Unique)
    $row.mx = @(Resolve-DnsName -Name $domain -Type MX -ErrorAction SilentlyContinue | Sort-Object Preference | ForEach-Object { "$($_.Preference) $($_.NameExchange)" } | Select-Object -Unique)
    $row.txt = @(Resolve-DnsName -Name $domain -Type TXT -ErrorAction SilentlyContinue | ForEach-Object { $_.Strings -join "" } | Select-Object -Unique)

    $statusOk = ($row.http_status -is [int]) -and ($row.http_status -ge 200) -and ($row.http_status -lt 400)
    $row.ok = $statusOk
    $results += [pscustomobject]$row
}

$summary = [pscustomobject]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    domains_total = $results.Count
    domains_ok = (@($results | Where-Object { $_.ok }).Count)
    domains_err = (@($results | Where-Object { -not $_.ok }).Count)
    results = $results
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $OutPath -Encoding UTF8
Write-Output "WROTE $OutPath"
