param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Benchmark,
    [switch]$SkipBenchmark,
    [switch]$Fast
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\enterprisemind-common.ps1"

$root = Get-EnterpriseMindRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

$summary = [ordered]@{
    "backend tests" = "skipped"
    "ruff" = "skipped"
    "mypy" = "skipped"
    "frontend tests" = "skipped"
    "frontend build" = "skipped"
    "benchmark" = "skipped"
}

function Set-Summary {
    param(
        [string]$Name,
        [string]$Value
    )
    $summary[$Name] = $Value
}

function Run-CheckedStep {
    param(
        [string]$Name,
        [string]$SummaryName,
        [scriptblock]$Command
    )
    Write-Step $Name
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE."
        }
        Set-Summary $SummaryName "passed"
        Write-Ok $Name
    } catch {
        Set-Summary $SummaryName "failed"
        Write-Fail $Name
        Write-Fail $_.Exception.Message
        Show-TestSummary
        exit 1
    }
}

function Show-TestSummary {
    Write-Host ""
    Write-Host "Test summary:"
    foreach ($key in $summary.Keys) {
        Write-Host ("  {0}: {1}" -f $key, $summary[$key])
    }
}

if ($BackendOnly -and $FrontendOnly) {
    throw "Cannot use -BackendOnly and -FrontendOnly together."
}

Write-Host "EnterpriseMind one-click test"
Write-Host "Project root: $root"
if ($Fast) {
    Write-Warn "Fast mode: skip ruff, mypy, frontend build and benchmark."
}

if (-not $FrontendOnly) {
    Push-Location $backend
    try {
        Run-CheckedStep "Backend pytest" "backend tests" {
            & conda run -n em python -m pytest -p no:cacheprovider --basetemp .pytest-tmp-all tests -q
        }

        if (-not $Fast) {
            Run-CheckedStep "Ruff" "ruff" {
                & conda run -n em python -m ruff check app tests scripts
            }

            Run-CheckedStep "Mypy" "mypy" {
                & conda run -n em python -m mypy app
            }
        }

        if ($Benchmark -and (-not $SkipBenchmark) -and (-not $Fast)) {
            Run-CheckedStep "Benchmark baseline" "benchmark" {
                & conda run -n em python scripts\evaluation\run_agent_benchmark.py --profile baseline --output evaluation\reports\baseline.json
            }
            Run-CheckedStep "Benchmark enhanced" "benchmark" {
                & conda run -n em python scripts\evaluation\run_agent_benchmark.py --profile enhanced --output evaluation\reports\enhanced.json
            }
            Run-CheckedStep "Benchmark compare" "benchmark" {
                & conda run -n em python scripts\evaluation\compare_benchmark.py evaluation\reports\baseline.json evaluation\reports\enhanced.json --output evaluation\reports\compare.json
            }
            Set-Summary "benchmark" "generated"
        } elseif ($Benchmark -and $Fast) {
            Set-Summary "benchmark" "skipped by fast mode"
        }
    } finally {
        Pop-Location
    }
}

if (-not $BackendOnly) {
    Push-Location $frontend
    try {
        Run-CheckedStep "Frontend tests" "frontend tests" {
            & npm test
        }

        if (-not $Fast) {
            Run-CheckedStep "Frontend build" "frontend build" {
                & npm run build
            }
        }
    } finally {
        Pop-Location
    }
}

if ($SkipBenchmark) {
    Set-Summary "benchmark" "skipped"
}

Show-TestSummary
Write-Ok "EnterpriseMind test script finished"
