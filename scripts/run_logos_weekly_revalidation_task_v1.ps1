$ErrorActionPreference = "Stop"

$script = "c:\workspace\scripts\run_logos_falsification_benchmark_v1.py"
$output = "c:\workspace\docs\final\artifacts\logos_weekly_revalidation_latest.json"

py $script --execute --include-real-oos --output-json $output
